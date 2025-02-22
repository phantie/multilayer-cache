from multilayer_cache.examples.parsed_cached_bucket.defs import BlobId
from multilayer_cache.examples.parsed_cached_bucket.defs import ParserVersion
from multilayer_cache.examples.parsed_cached_bucket.defs import FileContents
from multilayer_cache.examples.parsed_cached_bucket.defs import BaseModel


class Bucket(BaseModel):
    files: dict[BlobId, FileContents]

    def get(self, blob_id: BlobId, default) -> FileContents:
        return self.files.get(blob_id, default)

