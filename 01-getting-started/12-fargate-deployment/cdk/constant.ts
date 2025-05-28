import { RemovalPolicy, StackProps } from "aws-cdk-lib";

const projectName = "StrandsAgent";

const ssmParamKnowledgeBaseId = "restaurant-assistant-kb-id";
const ssmParamDynamoDb = "restaurant-assistant-table-name";
const ssmParamGuardrailId = "restaurant-assistant-guardrail-id";
const ssmParamGuardrailVersion = "restaurant-assistant-guardrail-version";

const s3BucketProps = {
  autoDeleteObjects: true,
  removalPolicy: RemovalPolicy.DESTROY,
};

const agentModelId = "anthropic.claude-3-5-sonnet-20241022-v2:0";
export { projectName, s3BucketProps, ssmParamKnowledgeBaseId, ssmParamDynamoDb, ssmParamGuardrailId, ssmParamGuardrailVersion, agentModelId };
