from multilayer_cache.examples.async_cached_bucket.defs import BlobId
from multilayer_cache.examples.async_cached_bucket.defs import FileContents
from multilayer_cache.examples.async_cached_bucket.defs import BaseModel


class Bucket(BaseModel):
    files: dict[BlobId, FileContents]

    async def get(self, blob_id: BlobId, default) -> FileContents:
        return self.files.get(blob_id, default)

