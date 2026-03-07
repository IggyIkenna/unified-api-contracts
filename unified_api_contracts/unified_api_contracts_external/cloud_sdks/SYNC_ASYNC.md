# GCP Cloud SDK: Sync vs Async per Client

| Client             | Package                 | Sync                                | Async                                                        |
| ------------------ | ----------------------- | ----------------------------------- | ------------------------------------------------------------ |
| **Compute Engine** | `google-cloud-compute`  | `InstancesClient`                   | `InstancesAsyncClient` (same package)                        |
| **Cloud Run**      | `google-cloud-run`      | `ServicesClient`, `RevisionsClient` | `ServicesAsyncClient`, `RevisionsAsyncClient`                |
| **GCS**            | `google-cloud-storage`  | `Client`                            | No native async; use `asyncio.to_thread(client.method, ...)` |
| **BigQuery**       | `google-cloud-bigquery` | `Client`                            | No native async; use `asyncio.to_thread(client.query, ...)`  |

## Usage

```python
# Compute: async
from google.cloud.compute_v1.services.instances import InstancesAsyncClient
client = InstancesAsyncClient()
op = await client.insert(request=request)

# GCS: wrap sync
import asyncio
from google.cloud import storage
client = storage.Client()
data = await asyncio.to_thread(client.bucket("b").blob("x").download_as_bytes)
```
