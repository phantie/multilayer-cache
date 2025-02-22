from multilayer_cache.util import to_async

from typing import Generic
from typing import TypeVar
from typing import Any
from typing import Callable
from typing import Annotated
from typing import Literal
from typing import Awaitable

import pydantic


# Represents value type a cache returns
T = TypeVar("T")
# Represent [K]ey used for fetching from inner cache or source
K = TypeVar("K")
# Represents unique [D]efault value that should be returned on not found key
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
    get_cache_key: Callable[[], K],
    get_cache_value: Callable[[K, D], T],
    set_cache_value: Callable[[K, T], None],
    on_cache_miss_source: Callable[[K, D], T],
    get_default: Callable[[], D],
    get_identifier: Callable[[], Any],
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
###     C type inner cache stores values in
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
###     inner_cache
###
###
###     def get(self, getter)
###         getter -> key
###
###         inner_cache (key)
###             hit:
###                 deserialize
###             miss:
###                 on_cache_miss_source (key part)
###                 getter -> (S -> T)
###                 inner_cache[key]=serialize
###                 serialize
###
###
###

