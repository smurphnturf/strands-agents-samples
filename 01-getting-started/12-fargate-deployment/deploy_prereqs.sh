# agent knowledge base
echo "deploying knowledge base ..."
python prereqs/knowledge_base.py --mode create

# agent dynamodb
echo "deploying DynamoDB ..."
python prereqs/dynamodb.py --mode create

# agent guardrail
echo "deploying Bedrock Guardrail ..."
python prereqs/guardrail.py --mode create


