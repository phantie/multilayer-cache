from multilayer_cache import cache_layer
from multilayer_cache import KEY_NOT_FOUND
from multilayer_cache.examples.parsed_files.defs import BlobId
from multilayer_cache.examples.parsed_files.parser import Parser

from typing import TypeAlias
import json
from functools import partial

import pydantic



InnerCache: TypeAlias = dict[BlobId, str]



def bakein_get_cache_value(inner_cache: InnerCache):
    return lambda key, default: json.loads(cached) if (cached := inner_cache.get(key, default)) is not default else default

def bakein_set_cache_value(inner_cache: InnerCache):
    return lambda key, value: inner_cache.update({key: json.dumps(value)})



cache_layer_partial = partial(
    cache_layer,
    # get_cache_key
    # get_cache_value
    # set_cache_value
    # on_cache_miss_source=on_cache_miss_source,
    get_default=lambda: KEY_NOT_FOUND,
    get_identifier=lambda: "parsed_cached_files",
    # inspect
)

