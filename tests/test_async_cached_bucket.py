
from multilayer_cache.core import KEY_NOT_FOUND
from multilayer_cache.core import CacheLayerInspect
from multilayer_cache.core import CacheLayerInspectHit
from multilayer_cache.core import CacheLayerInspectMiss
from multilayer_cache.util import to_async
from multilayer_cache.examples.async_parsed_files.defs import BlobId
from multilayer_cache.examples.async_parsed_files.defs import FileContents
from multilayer_cache.examples.async_parsed_files.bucket import Bucket
from multilayer_cache.examples.async_parsed_files import cached_files

import json
from functools import partial
import logging

import pydantic
import pytest 


def get_test_bucket() -> Bucket:
    bucket = Bucket(
        files = {
            "a": json.dumps({"key": "a", "value": "a"}),
            "b": json.dumps({"key": "b", "value": "b"}),
        }
    )

    return bucket


@pytest.mark.asyncio
async def test_foo_async():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    inspect_queue: list[CacheLayerInspect] = []

    def inspect(value: CacheLayerInspect):
        print(repr(value))
        inspect_queue.append(value)

    log = lambda value: print(value)

    bucket = get_test_bucket()


    cached_files_from_bucket_inner_cache = {}

    cached_files_from_bucket_cache = partial(
        cached_files.cache_layer_partial,
        get_cache_value=cached_files.bakein_get_cache_value(cached_files_from_bucket_inner_cache),
        set_cache_value=cached_files.bakein_set_cache_value(cached_files_from_bucket_inner_cache),
        on_cache_miss_source=cached_files.bakein_on_cache_miss_source(bucket),
        inspect=to_async(inspect),
    )


    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    result = await cached_files_from_bucket_cache(
        get_cache_key=to_async(lambda: "a"),
        get_default=to_async(lambda: KEY_NOT_FOUND),
    )

    log(f"{result=!r}")

    assert result == '{"key": "a", "value": "a"}'

    match inspect_queue:
        case [
            CacheLayerInspect(identifier='cached_files', value=CacheLayerInspectMiss(key='a')),
        ]:
            pass
        case _:
            raise ValueError
        
    inspect_queue.clear()

    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
