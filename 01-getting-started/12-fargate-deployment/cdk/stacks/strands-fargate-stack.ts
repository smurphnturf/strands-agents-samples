import { Stack, StackProps, Duration, RemovalPolicy } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as ecrAssets from "aws-cdk-lib/aws-ecr-assets";
import * as path from "path";
import { agentModelId, projectName, s3BucketProps, ssmParamDynamoDb, ssmParamKnowledgeBaseId, ssmParamGuardrailId, ssmParamGuardrailVersion } from "../constant";
import { BlockPublicAccess, Bucket, BucketEncryption, ObjectOwnership } from "aws-cdk-lib/aws-s3";
import { setSecureTransport } from "../utility";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { NagSuppressions } from "cdk-nag";

export class StrandsFargateStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const knowledgeBaseId = ssm.StringParameter.fromStringParameterName(
      this,
      `${projectName}-knowledge-base-id`,
      `/${ssmParamKnowledgeBaseId}`,
    );

    const dynamoDBName = ssm.StringParameter.fromStringParameterName(
      this,
      `${projectName}-dynamo-db-name`,
      `/${ssmParamDynamoDb}`,
    );

    // Try to get guardrail parameters (optional - may not exist)
    let guardrailId: ssm.IStringParameter | undefined;
    let guardrailVersion: ssm.IStringParameter | undefined;
    
    try {
      guardrailId = ssm.StringParameter.fromStringParameterName(
        this,
        `${projectName}-guardrail-id`,
        `/${ssmParamGuardrailId}`,
      );
      
      guardrailVersion = ssm.StringParameter.fromStringParameterName(
        this,
        `${projectName}-guardrail-version`,
        `/${ssmParamGuardrailVersion}`,
      );
    } catch (error) {
      console.log("Guardrail parameters not found - deploying without guardrails");
    }

    // const albLogBucket = new Bucket(this, `${projectName}-alb-access-logs`, {
    //   objectOwnership: ObjectOwnership.OBJECT_WRITER,
    //   encryption: BucketEncryption.S3_MANAGED,
    //   blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
    //   versioned: true,
    //   enforceSSL: true,
    //   ...s3BucketProps,
    // });

    // setSecureTransport(albLogBucket);

    const accessLogBucket = new Bucket(this, `${projectName}-access-bucket-access-logs`, {
      objectOwnership: ObjectOwnership.OBJECT_WRITER,
      encryption: BucketEncryption.S3_MANAGED,
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      enforceSSL: true,
      ...s3BucketProps,
    });

    setSecureTransport(accessLogBucket);

    // Define the Flow Log Bucket first
    const flowLogBucket = new Bucket(this, `${projectName}-flow-log-bucket`, {
      objectOwnership: ObjectOwnership.OBJECT_WRITER,
      encryption: BucketEncryption.S3_MANAGED,
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      serverAccessLogsBucket: accessLogBucket,
      serverAccessLogsPrefix: `${projectName}-vpc-bucket-access-logs`,
      versioned: true,
      enforceSSL: true,
      ...s3BucketProps,
    });

    setSecureTransport(flowLogBucket);

    const agentBucket = new Bucket(this, `${projectName}-agent-bucket`, {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.S3_MANAGED,
      serverAccessLogsBucket: accessLogBucket,
      enforceSSL: true,
      versioned: true,
      serverAccessLogsPrefix: `${projectName}-agent-bucket-access-logs`,
      ...s3BucketProps,
    });

    setSecureTransport(agentBucket);

    // // Define the VPC
    // const vpc = new ec2.Vpc(this, `${projectName}-vpc`, {
    //   maxAzs: 2,
    //   natGateways: 1,
    // });
    // Import the VPC by ID (replace 'vpc-xxxxxxxx' with your VPC ID)
    const vpc = ec2.Vpc.fromLookup(this, `vpc-shared`, {
      vpcId: "vpc-057ac7d36bc099bf1", // team
    });

    // Create the VPC Flow Log without deliverLogsPermissionArn
    new ec2.CfnFlowLog(this, `${projectName}-vpc-flow-log`, {
      resourceId: vpc.vpcId,
      resourceType: "VPC",
      trafficType: "ALL",
      logDestinationType: "s3",
      logDestination: flowLogBucket.bucketArn,
    });

    // Create an ECS cluster
    const cluster = new ecs.Cluster(this, `${projectName}-cluster`, {
      vpc,
      containerInsights: true,
    });

    // Create a log group for the container
    const logGroup = new logs.LogGroup(this, `${projectName}-service-logs`, {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Create a task execution role
    const executionRole = new iam.Role(this, `${projectName}-task-execution-role`, {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      managedPolicies: [iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AmazonECSTaskExecutionRolePolicy")],
    });

    // Create a task role with permissions to invoke Bedrock APIs
    const taskRole = new iam.Role(this, `${projectName}-task-role`, {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    agentBucket.grantReadWrite(taskRole);

    // Add permissions for the task to invoke Bedrock APIs
    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        resources: ["*"],
      }),
    );

    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:Retrieve"],
        resources: [
          `arn:aws:bedrock:${process.env.CDK_DEFAULT_REGION}:${process.env.CDK_DEFAULT_ACCOUNT}:knowledge-base/${knowledgeBaseId.stringValue}`,
        ],
      }),
    );

    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "dynamodb:ListTables",
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:GetRecords",
          "dynamodb:DeleteItem",
          "dynamodb:DeleteTable",
          "dynamodb:UpdateItem",
          "dynamodb:UpdateTable",
        ],
        resources: [
          `arn:aws:dynamodb:${process.env.CDK_DEFAULT_REGION}:${process.env.CDK_DEFAULT_ACCOUNT}:table/${dynamoDBName.stringValue}`,
        ],
      }),
    );

    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ssm:GetParameter"],
        resources: [
          `arn:aws:ssm:${process.env.CDK_DEFAULT_REGION}:${process.env.CDK_DEFAULT_ACCOUNT}:parameter/${ssmParamDynamoDb}`,
        ],
      }),
    );

    // Add guardrail permissions if guardrail is configured
    if (guardrailId) {
      taskRole.addToPolicy(
        new iam.PolicyStatement({
          actions: ["bedrock:ApplyGuardrail"],
          resources: [
            `arn:aws:bedrock:${process.env.CDK_DEFAULT_REGION}:${process.env.CDK_DEFAULT_ACCOUNT}:guardrail/${guardrailId.stringValue}`,
          ],
        }),
      );
    }

    // Create a task definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, `${projectName}-task-definition`, {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole,
      taskRole,
      runtimePlatform: {
        cpuArchitecture: ecs.CpuArchitecture.ARM64,
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
      },
    });

    // This will use the Dockerfile in the docker directory
    const dockerAsset = new ecrAssets.DockerImageAsset(this, `${projectName}-image`, {
      directory: path.join(__dirname, "../../docker"),
      file: "./Dockerfile",
      platform: ecrAssets.Platform.LINUX_ARM64,
    });

    // Add container to the task definition
    taskDefinition.addContainer(`${projectName}-container`, {
      image: ecs.ContainerImage.fromDockerImageAsset(dockerAsset),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "agent-service",
        logGroup,
      }),
      environment: {
        // Add any environment variables needed by your application
        LOG_LEVEL: "INFO", // changing this value will result in new
        KNOWLEDGE_BASE_ID: knowledgeBaseId.stringValue,
        AGENT_BUCKET: agentBucket.bucketName,
        ...(guardrailId && guardrailVersion ? {
          GUARDRAIL_ID: guardrailId.stringValue,
          GUARDRAIL_VERSION: guardrailVersion.stringValue,
        } : {}),
      },
      portMappings: [
        {
          containerPort: 8000, // The port your application listens on
          protocol: ecs.Protocol.TCP,
        },
      ],
    });

    // Create a Fargate service
    const service = new ecs.FargateService(this, `${projectName}-service`, {
      cluster,
      taskDefinition,
      desiredCount: 2, // Run 2 instances for high availability
      assignPublicIp: false, // Use private subnets with NAT gateway
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      circuitBreaker: {
        rollback: true,
      },
      securityGroups: [
        new ec2.SecurityGroup(this, `${projectName}-service-sg`, {
          vpc,
          description: "Security group for Agent Fargate Service",
          allowAllOutbound: true,
        }),
      ],
      minHealthyPercent: 100,
      maxHealthyPercent: 200,
      healthCheckGracePeriod: Duration.seconds(60),
    });

    // Create an Application Load Balancer
    const lb = new elbv2.ApplicationLoadBalancer(this, `${projectName}-alb`, {
      vpc,
      internetFacing: true,
    });

    // lb.logAccessLogs(albLogBucket,'alb-access-logs/')

    // Create a listener
    const listener = lb.addListener(`${projectName}-listener`, {
      port: 80,
    });

    // Add target group to the listener
    listener.addTargets(`${projectName}-targets`, {
      port: 8000,
      targets: [service],
      healthCheck: {
        path: "/health",
        interval: Duration.seconds(300),
        timeout: Duration.seconds(5),
        healthyHttpCodes: "200",
      },
      deregistrationDelay: Duration.seconds(300),
    });

    // Output the load balancer DNS name
    this.exportValue(lb.loadBalancerDnsName, {
      name: `${projectName}-service-endpoint`,
      description: "The DNS name of the load balancer for the Agent Service",
    });

    // NagSuppressions.addResourceSuppressionsByPath(
    //   this,
    //   `/${projectName}FargateStack/${projectName}-flow-log-role/DefaultPolicy/Resource`,
    //   [
    //     {
    //       id: "AwsSolutions-IAM5",
    //       reason: "Wildcard resource required for S3 PutObject into VPC Flow Logs folder structure.",
    //     },
    //   ],
    // );

    NagSuppressions.addResourceSuppressionsByPath(
      this,
      `/${projectName}FargateStack/${projectName}-task-execution-role/Resource`,
      [
        {
          id: "AwsSolutions-IAM4",
          reason: "AmazonECSTaskExecutionRolePolicy is used intentionally.",
        },
      ],
    );

    NagSuppressions.addResourceSuppressionsByPath(
      this,
      `/${projectName}FargateStack/${projectName}-task-execution-role/DefaultPolicy/Resource`,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "AmazonECSTaskExecutionRolePolicy is used intentionally.",
        },
      ],
    );

    NagSuppressions.addResourceSuppressions(taskDefinition, [
      {
        id: "AwsSolutions-ECS2",
        reason: "Environment variables used are non-sensitive and needed for container behavior.",
      },
    ]);

    NagSuppressions.addResourceSuppressionsByPath(this, `/${projectName}FargateStack/${projectName}-alb/Resource`, [
      {
        id: "AwsSolutions-ELB2",
        reason: "ALB access logs cannot be enabled on region agnostic stacks. Use VPC flow logs",
      },
    ]);

    NagSuppressions.addResourceSuppressionsByPath(
      this,
      `/${projectName}FargateStack/${projectName}-alb/SecurityGroup/Resource`,
      [
        {
          id: "AwsSolutions-EC23",
          reason: "ALB allows inbound access to public.",
        },
      ],
    );

    NagSuppressions.addResourceSuppressionsByPath(
      this,
      `/${projectName}FargateStack/${projectName}-task-role/DefaultPolicy/Resource`,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "Allowing access to all bedrock models",
        },
      ],
    );
  }
}
