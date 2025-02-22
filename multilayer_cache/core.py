from multilayer_cache.util import to_async

from typing import Generic
from typing import TypeVar
from typing import Any
from typing import Callable
from typing import Annotated
from typing import Literal
from typing import Awaitable

import pydantic


# For nesting of layers L(0..N) to be possible (where L_0 is the most inner layer and L_N is the most outer layer)
#
#
# Represents value type a cache returns
#
# For T(0..N) must be such as there must exist a one-way transformation (morfism) T_0 -> T_N.
# Simply, there must be a way to reduce a **value** passing from *inner to outer* layer.
# For example, it works with bytes -> decoded bytes -> parsed json
# 
# It's a formalization, but since constructing of cache happens from the ground up, it would be understood in the process
#
T = TypeVar("T")

# Represent [K]ey used for retrieving from local cache or source
#
#
# For K(0..N) must be such as there must exist a one-way transformation (morfism) K_N -> K_0.
# Simply, there must be a way to reduce a **key** passing from *outer to inner* layer.
#
# There must be a transformation from type for most outer layer to most inner layer
# Practically it implies that the key must contain all required info for dependant cache layers
#
K = TypeVar("K")

# Represents unique (in "is" operation) [D]efault value that should be returned on not found key
D = TypeVar("D")


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


class CACHE_MISS: ...
class KEY_NOT_FOUND: ...

CACHE_MISS = CACHE_MISS()
KEY_NOT_FOUND = KEY_NOT_FOUND()


class CacheLayerInspectHit(BaseModel, Generic[K]):
    choice: Literal["hit"] = "hit"
    key: K

class CacheLayerInspectMiss(BaseModel, Generic[K]):
    choice: Literal["miss"] = "miss"
    key: K

class CacheLayerInspect(BaseModel, Generic[K]):
    identifier: str
    value: Annotated[CacheLayerInspectHit[K] | CacheLayerInspectMiss[K], pydantic.Field(discriminator="choice")]


def cache_layer(
    # A way to get a cache key
    get_cache_key: Callable[[], K],
    # A way to use the key from local cache to get a value
    get_cache_value: Callable[[K, D], T],
    # A way to update local cache with the key and value
    set_cache_value: Callable[[K, T], None],
    # A way to get value from the dependant source with the key
    on_cache_miss_source: Callable[[K, D], T],
    # A way to get a unique value the local cache and dependant source would return when the key not found
    get_default: Callable[[], D],
    # A way to get an identifier for a cache layer
    get_identifier: Callable[[], Any],
    # Handler of generated events, for example for testing and logging
    inspect: Callable[[CacheLayerInspect], None] = lambda _: None,
) -> T:
    cache_id = get_identifier()

    key = get_cache_key()

    cached = get_cache_value(key, CACHE_MISS)

    if cached is CACHE_MISS:
        inspect(CacheLayerInspect(
            identifier=cache_id,
            value=CacheLayerInspectMiss(
                key=key,
            )
        ))

        default = get_default()

        value = on_cache_miss_source(key, default)

        if value is default:
            return default

        set_cache_value(key, value)
        return value

    else:
        inspect(CacheLayerInspect(
            identifier=cache_id,
            value=CacheLayerInspectHit(
                key=key,
            )
        ))

        return cached
    

async def async_cache_layer(
    get_cache_key: Callable[[], Awaitable[K]],
    get_cache_value: Callable[[K, D], Awaitable[T]],
    set_cache_value: Callable[[K, T], Awaitable[None]],
    on_cache_miss_source: Callable[[K, D], Awaitable[T]],
    get_default: Callable[[], Awaitable[D]],
    get_identifier: Callable[[], Awaitable[Any]],
    inspect: Callable[[CacheLayerInspect], Awaitable[None]] = to_async(lambda _: None),
) -> T:
    cache_id = await get_identifier()

    key = await get_cache_key()

    cached = await get_cache_value(key, CACHE_MISS)

    if cached is CACHE_MISS:
        await inspect(CacheLayerInspect(
            identifier=cache_id,
            value=CacheLayerInspectMiss(
                key=key,
            )
        ))

        default = await get_default()

        value = await on_cache_miss_source(key, default)

        if value is default:
            return default

        await set_cache_value(key, value)
        return value

    else:
        await inspect(CacheLayerInspect(
            identifier=cache_id,
            value=CacheLayerInspectHit(
                key=key,
            )
        ))

        return cached


### class CacheName(...GenericArgs [T, C, S]) todo add cache key type
###
###     T type cache returns
###     C type local cache stores values in
###     S type on_cache_miss_source returns
###
###     on_cache_miss_source (key part -> S)
###
###     getter -> key
###     getter -> (S -> T)
###
###     serialize -> (T, C)
###     deserialize -> (C, T)
###
###     local_cache
###
###
###     def get(self, getter)
###         getter -> key
###
###         local_cache (key)
###             hit:
###                 deserialize
###             miss:
###                 on_cache_miss_source (key part)
###                 getter -> (S -> T)
###                 local_cache[key]=serialize
###                 serialize
###
###
###

