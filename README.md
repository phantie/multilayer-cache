# Multilayer caching

"Multilayer" here means that one cache layer may depend on another, which, in turn, may depend on yet another. It is also capable of forming not only chains but also trees of dependent caches. Value retrievals update the local cache of all downstream layers.

## Our example

For example, suppose we have files stored in an S3 bucket that we want to cache locally, and also cache the parsed data structures derived from these files. This results in a 2-layer cache structure, with the bucket serving as the data source.

```
Bucket  
 ├── File Cache  
 │   ├── Parsed File Cache  
```

Say you want a parsed value, so you are concerned with the **Parsed File Cache**.

With both local caches empty, let's describe what happens during the first value retrieval.


Since **Parsed File Cache** would *not* find it in the local cache, it would then try to retrieve it from its dependant - **File Cache**.
**File Cache** would also *not* find a transformable value in its local cache, and to the dependant it goes - **Bucket**.


**Bucket** may or may *not* have a value.
If it doesn’t, no local cache updates occur, and the result of retrieval from **Parsed File Cache** is a value representing *Key not found*.
But if it does, **File Cache** transforms the value retrieved from **Bucket**, stores the value in its local cache, and **Parsed File Cache** does the same.

When values are found in local caches, they pop out immediately, and the caches do not contact their dependants.

It's a simple recursive algorithm.

### More elaborate cache structures

For the sake of brevity, we investigate this minimal example, but arbitrary nested tree cache structures are possible nonetheless:

```
Bucket  
 ├── File Cache  
 │   ├── Parsed File Cache  
 │   │   ├── Further Parsed File Cache  
 │   ├── Another Parsed File Cache  
```

## Implementation

### Common problems

Implementing such caching still may be a challenge. The implementation may suffer from:

- spagetti
(having a recursive nature, but with finite nesting. For your purposes, you might have started with one layer, but after adding a layer or two more, the code started looking like this from afar:)
```
@@@@ outer layer get
  @@@@ middle layer get
    @@@@ inner layer get
  @@@@
@@@@
```

- imposing too tight contracts and controlling the local cache.

- mixing in more logic than necessary (due to lack of formalization and restrictions).


### Approach

In implementation, the concern is to provide the most flexible way to construct caches. This is achieved by imposing only the essential constraints to the problem, which, at the same time, provide freedom by enforcing similarity across different layers.

### Python implementation

```python
# Represents value type a cache returns
T = TypeVar("T")
# Represent [K]ey used for retrieving from local cache or source
K = TypeVar("K")
# Represents unique (in "is" operation) [D]efault value that should be returned on not found key
D = TypeVar("D")


def cache_layer(
    # A way to get a cache key
    get_cache_key: Callable[[], K],
    # A way to use the key from local cache to get a value
    get_cache_value: Callable[[K, D], T | D],
    # A way to update local cache with the key and value
    set_cache_value: Callable[[K, T], None],
    # A way to get value from the dependant source with the key
    on_cache_miss_source: Callable[[K, D], T | D],
    # A way to get a unique value the local cache and dependant source would return when the key not found
    get_default: Callable[[], D],
    # A way to get an identifier for a cache layer
    get_identifier: Callable[[], Any],
    # Handler of generated events, for example for testing and logging
    inspect: Callable[[CacheLayerInspect], None] = lambda _: None,
) -> T | D:
    ...
```

### Constraints

For nesting of layers L(0..N) to be possible (where L_0 is the most inner layer and L_N is the most outer layer)

T(0..N) must be such that, there must exist a one-way transformation (morfism) T_0 -> T_N.
Simply, there must be a way to reduce a **value** passing from *inner to outer* layer.
For example, it works with bytes -> decoded bytes -> parsed json

K(0..N) must be such that, there must exist a one-way transformation (morfism) K_N -> K_0.
Simply, there must be a way to reduce a **key** passing from *outer to inner* layer.

### [multilayer_cache](https://github.com/phantie/multilayer-cache) is a library containing cache_layer among other things (asynchronous and type hinted cache layer, examples)

So let's implement the 2-layer example

```python
from multilayer_cache import cache_layer
from multilayer_cache import type_hinted_cache_layer
from multilayer_cache import KEY_NOT_FOUND
from multilayer_cache import CacheLayerInspect
from multilayer_cache import CacheLayerInspectHit
from multilayer_cache import CacheLayerInspectMiss

import json
from functools import partial
from typing import TypeAlias
from typing import TypeVar
from typing import Any
from typing import Optional

import pydantic

D = TypeVar("D")

########################################################################

### Define mock blob storage as a mapping from BlobId to FileContents.

BlobId: TypeAlias = str
FileContents: TypeAlias = str

class Bucket(pydantic.BaseModel):
    files: dict[BlobId, FileContents]

    def get(self, blob_id: BlobId, default: D) -> FileContents | D:
        return self.files.get(blob_id, default)

bucket = Bucket(
    files = {
        "a": json.dumps({"key": "a", "value": "a"}),
        "b": json.dumps({"key": "b", "value": "b"}),
    }
)

########################################################################

### Let's implement the first layer: an in-memory cache layer preserving raw files.

FilesInnerCache: TypeAlias = dict[BlobId, FileContents]

# It doesn't enforce local cache management.
# You may provide any and manage it as you like.
# An in-memory solution is the shortest to demonstrate.
files_inner_cache: FilesInnerCache = {}

# Let's match against the generated events.
events = []

def on_cache_miss_source(cache_key: BlobId, default: D) -> FileContents | D:
    blob_id = cache_key
    # It's important to enforce a contract that lets you know when a value was not found because
    # most of the time, a library would throw its own exception.
    return bucket.get(blob_id, default)

# Bake in common parameters
files_cache_layer_partial = partial(
    cache_layer,
    # get_cache_key=
    get_cache_value=lambda key, default: files_inner_cache.get(key, default),
    set_cache_value=lambda key, value: files_inner_cache.update({key: value}),
    on_cache_miss_source=on_cache_miss_source,
    # get_default=
    get_identifier=lambda: "raw_files",
    inspect=lambda event: events.append(event),
)

# Make a call with the key "a" (we know the bucket has it).
result = files_cache_layer_partial(
    get_cache_key=lambda: "a",
    # do not bake in default because outer layers provide their own
    get_default=lambda: KEY_NOT_FOUND,
)

# As expected, we received the unchanged value from the blob and cached it locally.
# The same call would return the already cached value.
assert result == '{"key": "a", "value": "a"}'


match events:
    # One miss event was generated because the key was missing from the cache.
    case [
        CacheLayerInspect(identifier='raw_files', value=CacheLayerInspectMiss(key='a')),
    ]:
        pass
    case _:
        raise ValueError

events.clear()


# Let's do the same call
result = files_cache_layer_partial(
    get_cache_key=lambda: "a",
    get_default=lambda: KEY_NOT_FOUND,
)

match events:
    # Now it's a hit
    case [
        CacheLayerInspect(identifier='raw_files', value=CacheLayerInspectHit(key='a')),
    ]:
        pass
    case _:
        raise ValueError

events.clear()


# Make a call with the key "c" (we know the bucket does not have it).
result = files_cache_layer_partial(
    get_cache_key=lambda: "c",
    get_default=lambda: KEY_NOT_FOUND,
)

# As expected, the value was not found, and nothing has changed.
assert result is KEY_NOT_FOUND


########################################################################

### Let's implement the second layer: an in-memory cache of parsed files.

# To demonstrate more complex key usage,
# we'll version a parser.
ParserVersion: TypeAlias = str

# To demonstrate transformations to and from the local cache,
# we'll serialize the model to a string and back.
ParsedFileCompressed: TypeAlias = str

# To demonstrate the transformation of a value retrieved from a dependant source,
# we'll parse it.
class ParsedFile(pydantic.BaseModel):
    key: Any
    value: Any


# It's common for parsers to change, so data parsed with one version may not be compatible with another.

# You are free to manage (invalidate) the local cache however you like in this regard.

# You may clean it when a parser with a newer version is used, 
# keep all the data,
# restrict it by size and keep the latest data,
# or use a database or network.

# It's still your choice and an exercise for the reader.
class JsonParser:
    def version(self) -> ParserVersion:
        return "0"

    def parse(self, value: FileContents) -> ParsedFile:
        return ParsedFile.model_validate_json(value)


parser = JsonParser()

ParsedFilesKey: TypeAlias = tuple[BlobId, ParserVersion]
ParsedFilesInnerCache: TypeAlias = dict[ParsedFilesKey, ParsedFileCompressed]

parsed_files_inner_cache: FilesInnerCache = {}

def on_cache_miss_source(cache_key: ParsedFilesKey, default: D) -> ParsedFile | D:
    # The inner layer requires only the blob_id.
    blob_id, _parser_version = cache_key

    # Use the raw files cache and provide a key and a default.
    value = files_cache_layer_partial(
        get_cache_key=lambda: blob_id,
        get_default=lambda: default,
    )

    # Pop out the default.
    if value is default:
        return default

    # Transform the found value to this cache return type.
    value = parser.parse(value)

    # This value will be passed to be stored in the local cache.
    return value


parsed_files_cache_layer_partial = partial(
    # The type_hinted_cache_layer allows you to type hint ahead of time,
    # making it better to work with lambdas.
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
    # Provide both the blob_id and the parser version.
    get_cache_key=lambda: ("a", parser.version()),
    get_default=lambda: KEY_NOT_FOUND,
)

# As a result, we've got a parsed file cached on all layers.
assert result == ParsedFile(key="a", value="a")


########################################################################

### The layers are implemented, but the composition is up to your imagination.

# For example, we could provide a more user-friendly interface.
def get_parsed_file(blob_id: BlobId, parser: JsonParser) -> Optional[ParsedFile]:
    value = parsed_files_cache_layer_partial(
        get_cache_key=lambda: (blob_id, parser.version()),
        get_default=lambda: KEY_NOT_FOUND,
    )

    return None if value is KEY_NOT_FOUND else value
```

### Async capabilities

The [multilayer_cache](https://github.com/phantie/multilayer-cache) library also has an asynchronous cache layer (async_cache_layer). The difference is that it takes as arguments asynchronous functions instead of synchronous. See [async_cached_files](https://github.com/phantie/multilayer-cache/blob/main/multilayer_cache/tests/test_async_cached_files.py) example.

Since retrieving values from the cache is a parallelizable operation when used with many keys, it would work nicely with asyncio.gather or asyncio.Semaphore.

## Conclusion

Caching **can** be fun. (somewhat)