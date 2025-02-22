from multilayer_cache import cache_layer
from multilayer_cache import type_hinted_cache_layer
from multilayer_cache import KEY_NOT_FOUND

import json
from functools import partial
from typing import TypeAlias
from typing import Any

import pydantic


########################################################################

### Mock blob storage as mapping from BlobId to FileContents

BlobId: TypeAlias = str
FileContents: TypeAlias = str

class Bucket(pydantic.BaseModel):
    files: dict[BlobId, FileContents]

    def get(self, blob_id: BlobId, default) -> FileContents:
        return self.files.get(blob_id, default)

bucket = Bucket(
    files = {
        "a": json.dumps({"key": "a", "value": "a"}),
        "b": json.dumps({"key": "b", "value": "b"}),
    }
)

########################################################################

### Let's implement the first layer:
### In memory cache layer preserving raw files

FilesInnerCache: TypeAlias = dict[BlobId, FileContents]

# It doesn't enforce local cache managment
# You may provide any, and manage as you like
# In memory solution is the shortest to demonstrate
files_inner_cache: FilesInnerCache = {}

def on_cache_miss_source(cache_key: BlobId, default) -> FileContents:
    blob_id = cache_key
    # it's important to enforce contract letting you know when value was not found
    # because most of the time a library would throw their own exception
    return bucket.get(blob_id, default)

# bake in common params
files_cache_layer_partial = partial(
    cache_layer,
    # get_cache_key=
    get_cache_value=lambda key, default: files_inner_cache.get(key, default),
    set_cache_value=lambda key, value: files_inner_cache.update({key: value}),
    on_cache_miss_source=on_cache_miss_source,
    # get_default=
    get_identifier=lambda: "raw_files",
)

# make a call with the key "a" (as we know the bucket has it)
result = files_cache_layer_partial(
    get_cache_key=lambda: "a",
    # do not bake in default because outer layers provide their own
    get_default=lambda: KEY_NOT_FOUND,
)

# as expected, we received unchanged value from blob
# and cached it locally
# the same call would return already cached value
assert result == '{"key": "a", "value": "a"}'


# make a call with the key "c" (as we know the bucket does not have it)
result = files_cache_layer_partial(
    get_cache_key=lambda: "c",
    get_default=lambda: KEY_NOT_FOUND,
)

# as expected, value was not found and nothing has changed
assert result is KEY_NOT_FOUND



########################################################################

### Let's implement the second layer:
### In memory cache of parsed files

# to demonstrate more complex key usage
# we'll version a parser
ParserVersion: TypeAlias = str

# to demonstrate transformations to and out of local cache
# we'll serialize model to string and back
ParsedFileCompressed: TypeAlias = str

# to demonstrate transformation of value retrieved from dependant source
# we'll parse it
class ParsedFile(pydantic.BaseModel):
    key: Any
    value: Any


# it's common that parsers change
# so data parsed with one version may not be compatible with another
#
# you are free manage (invalidate) local cache however you like in this regard
#
# you may clean it when a parser with a newer version is used
# you may keep all the data
# you may restrict it by size and keep the latest data
#
# it's still your choice and an excercise to the reader)
class JsonParser:
    def version(self) -> ParserVersion:
        return "0"

    def parse(self, value: FileContents) -> ParsedFile:
        return ParsedFile.model_validate_json(value)


parser = JsonParser()

ParsedFilesKey: TypeAlias = tuple[BlobId, ParserVersion]
ParsedFilesInnerCache: TypeAlias = dict[ParsedFilesKey, ParsedFileCompressed]

parsed_files_inner_cache: FilesInnerCache = {}

def on_cache_miss_source(cache_key: ParsedFilesKey, default) -> ParsedFile:
    # inner layer requires only blob_id
    blob_id, _parser_version = cache_key

    # use the raw files cache and provide a key and default
    value = files_cache_layer_partial(
        get_cache_key=lambda: blob_id,
        get_default=lambda: default,
    )

    # pop out the default
    if value is default:
        return default

    # transform found value to this cache return type
    value = parser.parse(value)

    # this value will be passed to be stored in the local cache
    return value


parsed_files_cache_layer_partial = partial(
    # type_hinted_cache_layer allows to type hint ahead of type
    # making it better to work with lambdas
    type_hinted_cache_layer[ParsedFile, ParsedFilesKey, Any].new,
    # get_cache_key=
    on_cache_miss_source=on_cache_miss_source,
    get_cache_value = lambda key, default: (
        ParsedFile.model_validate(cached) 
        if (cached := parsed_files_inner_cache.get(key, default)) is not default 
        else default
    ),
    set_cache_value=lambda key, value: parsed_files_inner_cache.update({key: value.model_dump_json(by_alias=True)}),
    # get_default=
    get_identifier=lambda: "parsed_files",
)


result = parsed_files_cache_layer_partial(
    # provide blob_id as well as parser version
    get_cache_key=lambda: ("a", parser.version()),
    get_default=lambda: KEY_NOT_FOUND,
)

# as the result we've got a parsed file cached on all layers
assert result == ParsedFile(key="a", value="a")


