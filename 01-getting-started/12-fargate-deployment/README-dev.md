# Local Development with Docker

This directory contains everything you need to run the Restaurant Assistant API locally using Docker for faster development and testing.

## Quick Start

### Automatic Setup (Recommended)

If you use `awsume team` or similar tools:

1. **Authenticate with AWS:**

   ```bash
   awsume team  # or your preferred AWS credential method
   ```

2. **Run the setup script:**
   ```bash
   ./dev-setup.sh
   ```

The script will automatically extract AWS credentials from your CLI cache and create the `.env` file for you!

### Manual Setup

If automatic credential extraction doesn't work:

1. **Setup environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials and bucket name
   ```

2. **Run the setup script:**
   ```bash
   ./dev-setup.sh
   ```

### Start Development

3. **Start the development server:**
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```

The API will be available at `http://localhost:8000` with auto-reload enabled for code changes.

## Credential Management

### Automatic Credential Extraction

The `extract-aws-creds.py` script can automatically populate your `.env` file from AWS CLI cache:

```bash
# Basic usage (writes to .env)
python3 extract-aws-creds.py

# Specify bucket name
python3 extract-aws-creds.py --bucket my-agent-bucket

# Write to custom file
python3 extract-aws-creds.py --output custom.env

# Help
python3 extract-aws-creds.py --help
```

**Requirements:**

- Valid AWS credentials in `~/.aws/cli/cache/` (created by `awsume`, `aws sso login`, etc.)
- Non-expired session tokens
- Python 3.6+

### Manual Credential Setup

If automatic extraction fails, manually edit `.env`:

```bash
AGENT_BUCKET=your-agent-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_SESSION_TOKEN=your-session-token
AWS_DEFAULT_REGION=ap-southeast-2
KNOWLEDGE_BASE_ID=RTPQAOWJTZ
```

## Development Features

- **Auto-reload**: Code changes in `docker/app/` automatically restart the server
- **Volume mounting**: Your local code is mounted into the container
- **Debug logging**: Full debug logging enabled for troubleshooting
- **Fast iteration**: No need to rebuild the image for code changes

## Available Commands

| Command                                               | Description                    |
| ----------------------------------------------------- | ------------------------------ |
| `docker compose -f docker-compose.dev.yml up`         | Start the development server   |
| `docker compose -f docker-compose.dev.yml up -d`      | Start in background (detached) |
| `docker compose -f docker-compose.dev.yml down`       | Stop the server                |
| `docker compose -f docker-compose.dev.yml logs -f`    | View logs                      |
| `docker compose -f docker-compose.dev.yml up --build` | Rebuild and start              |

## Testing Endpoints

Once running, you can test the API:

- **Health check**: `GET http://localhost:8000/health`
- **API documentation**: `http://localhost:8000/docs`
- **Invoke agent**: `POST http://localhost:8000/invoke/{session_id}`
- **Streaming response**: `POST http://localhost:8000/invoke-streaming/{session_id}`

### Example curl commands:

```bash
# Health check
curl http://localhost:8000/health

# Test agent invocation
curl -X POST "http://localhost:8000/invoke/test-session" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, I need help with restaurant reservations"}'

# Test streaming
curl -X POST "http://localhost:8000/invoke-streaming/test-session" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Can you search for receipts from merchant ID 12345?"}'
```

## Environment Variables

Required environment variables (set in `.env`):

- `AGENT_BUCKET`: S3 bucket name for agent state storage
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_SESSION_TOKEN`: AWS session token (if using temporary credentials)
- `AWS_DEFAULT_REGION`: AWS region (default: ap-southeast-2)
- `KNOWLEDGE_BASE_ID`: Bedrock knowledge base id

## File Structure

```
├── docker-compose.dev.yml   # Docker Compose for local development
├── .env.example            # Environment variables template
├── dev-setup.sh            # Quick setup script
└── docker/
    ├── app/                # Your application code (mounted as volume)
    ├── Dockerfile          # Dockerfile (used for both dev and production)
    └── requirements.txt    # Python dependencies
```

## Development Workflow

1. Make changes to files in `docker/app/`
2. The server will automatically reload
3. Test your changes at `http://localhost:8000`
4. View logs with `docker-compose -f docker-compose.dev.yml logs -f`

## Troubleshooting

- **Container won't start**: Check your `.env` file has correct AWS credentials
- **Permission issues**: Ensure Docker has access to the project directory
- **Port conflicts**: If port 8000 is in use, modify the port mapping in `docker-compose.dev.yml`
- **AWS connection issues**: Verify your credentials have access to the S3 bucket and Bedrock service
