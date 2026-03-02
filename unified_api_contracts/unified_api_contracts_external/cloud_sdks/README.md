# Cloud SDK Schemas and Protocols

Pydantic request/response schemas and Protocol definitions for AWS (boto3) and GCP cloud SDKs.

## AWS: boto3 vs aioboto3 (Sync vs Async)

### boto3 (Synchronous)

- **Client**: `boto3.client("ec2")`, `boto3.client("s3")`, etc.
- **Usage**: Blocking calls; suitable for scripts, batch jobs, sync code.
- **Example**:
  ```python
  import boto3
  ec2 = boto3.client("ec2")
  resp = ec2.describe_instances(InstanceIds=["i-12345"])
  ```

### aioboto3 (Asynchronous)

- **Client**: `aioboto3.Session().client("ec2")` used as async context manager.
- **Usage**: Non-blocking; suitable for async applications (FastAPI, asyncio).
- **Example**:
  ```python
  import aioboto3
  async with aioboto3.Session().client("ec2") as ec2:
      resp = await ec2.describe_instances(InstanceIds=["i-12345"])
  ```

### API Parity

- **Same API surface**: aioboto3 mirrors boto3 method signatures; request/response shapes are identical.
- **Schemas apply to both**: Pydantic schemas in `aws_schemas.py` validate responses from either client.
- **When to use**:
  - **boto3**: Sync scripts, CLI tools, batch pipelines, non-async services.
  - **aioboto3**: Async web services, event-driven handlers, high-concurrency I/O.

### Dependencies

- `boto3` — sync AWS SDK (common dependency).
- `aioboto3` — async wrapper; install only when needed: `uv pip install aioboto3`.
