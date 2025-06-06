from multilayer_cache import cache_layer
from multilayer_cache import KEY_NOT_FOUND
from multilayer_cache.examples.parsed_files.defs import BlobId
from multilayer_cache.examples.parsed_files.defs import FileContents
from multilayer_cache.examples.parsed_files.defs import BaseModel
from multilayer_cache.examples.parsed_files.defs import Bucket

from typing import TypeAlias
from functools import partial
import pydantic



InnerCache: TypeAlias = dict[BlobId, FileContents]


def bakein_on_cache_miss_source(bucket: Bucket):

    def on_cache_miss_source(cache_key: BlobId, default) -> FileContents:
        blob_id = cache_key
        return bucket.get(blob_id, default)
    
    return on_cache_miss_source

def bakein_get_cache_value(inner_cache: InnerCache):
    return lambda key, default: inner_cache.get(key, default)

def bakein_set_cache_value(inner_cache: InnerCache):
    return lambda key, value: inner_cache.update({key: value})


cache_layer_partial = partial(
    cache_layer,
    # get_cache_key
    # get_cache_value
    # set_cache_value
    # on_cache_miss_source
    get_default=lambda: KEY_NOT_FOUND,
    get_identifier=lambda: "cached_files",
    # inspect
)

