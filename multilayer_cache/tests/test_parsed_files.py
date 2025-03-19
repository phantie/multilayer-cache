
from multilayer_cache import KEY_NOT_FOUND
from multilayer_cache import CacheLayerInspect
from multilayer_cache import CacheLayerInspectHit
from multilayer_cache import CacheLayerInspectMiss
from multilayer_cache.examples.parsed_files.defs import BlobId
from multilayer_cache.examples.parsed_files.defs import ParserVersion
from multilayer_cache.examples.parsed_files.defs import FileContents
from multilayer_cache.examples.parsed_files.defs import Bucket
from multilayer_cache.examples.parsed_files.defs import JsonParser
from multilayer_cache.examples.parsed_files import parsed_cached_files
from multilayer_cache.examples.parsed_files import cached_files

import json
from functools import partial
import logging

import pydantic



def get_test_bucket() -> Bucket:
    bucket = Bucket(
        files = {
            "a": json.dumps({"key": "a", "value": "a"}),
            "b": json.dumps({"key": "b", "value": "b"}),
        }
    )

    return bucket


def test_foo():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    inspect_queue: list[CacheLayerInspect] = []

    def inspect(value: CacheLayerInspect):
        print(repr(value))
        inspect_queue.append(value)

    log = lambda value: print(value)

    bucket = get_test_bucket()

    parser = JsonParser()

    cached_files_inner_cache = {}

    cached_files_cache = partial(
        cached_files.cache_layer_partial,
        get_cache_value=cached_files.bakein_get_cache_value(cached_files_inner_cache),
        set_cache_value=cached_files.bakein_set_cache_value(cached_files_inner_cache),
        on_cache_miss_source=cached_files.bakein_on_cache_miss_source(bucket),
        inspect=inspect,
    )

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    result = cached_files_cache(
        get_cache_key=lambda: "a",
        get_default=lambda: KEY_NOT_FOUND,
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


    def on_cache_miss_source(cache_key: tuple[BlobId, ParserVersion], default):
        blob_id, _ = cache_key
        value = cached_files_cache(
            get_cache_key=lambda: blob_id,
            get_default=lambda: default,
        )

        if value is default:
            return default

        value = {"key": parser.parse(value)["key"]}

        return value

    parsed_cached_files_inner_cache = {}

    parsed_cached_files_cache = partial(
        parsed_cached_files.cache_layer_partial,
        get_cache_value=parsed_cached_files.bakein_get_cache_value(parsed_cached_files_inner_cache),
        set_cache_value=parsed_cached_files.bakein_set_cache_value(parsed_cached_files_inner_cache),
        on_cache_miss_source=on_cache_miss_source,
        inspect=inspect,
    )

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    result = parsed_cached_files_cache(
        get_cache_key=lambda: ("a", parser.version()),
    )

    log(f"{result=!r}")

    assert result == {"key": "a"}

    match inspect_queue:
        case [
            CacheLayerInspect(identifier='parsed_cached_files', value=CacheLayerInspectMiss(key=('a', '0'))),
            CacheLayerInspect(identifier='cached_files', value=CacheLayerInspectHit(key='a')),
        ]:
            pass
        case _:
            raise ValueError
    
    inspect_queue.clear()

    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    result = parsed_cached_files_cache(
        get_cache_key=lambda: ("a", parser.version()),
    )

    assert result == {"key": "a"}

    log(f"{result=!r}")

    match inspect_queue:
        case [
            CacheLayerInspect(identifier='parsed_cached_files', value=CacheLayerInspectHit(key=('a', '0'))),
        ]:
            pass
        case _:
            raise ValueError
    
    inspect_queue.clear()

    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    result = parsed_cached_files_cache(
        get_cache_key=lambda: ("c", parser.version()),
    )

    assert result is KEY_NOT_FOUND

    log(f"{result=!r}")

    match inspect_queue:
        case [
            CacheLayerInspect(identifier='parsed_cached_files', value=CacheLayerInspectMiss(choice='miss', key=('c', '0'))),
            CacheLayerInspect(identifier='cached_files', value=CacheLayerInspectMiss(choice='miss', key='c')),
        ]:
            pass
        case _:
            raise ValueError

    inspect_queue.clear()

    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    # log(f"{bucket=!r}")
    # log(f"{cached_files_inner_cache=!r}")
    # log(f"{parsed_cached_files_inner_cache=!r}")

