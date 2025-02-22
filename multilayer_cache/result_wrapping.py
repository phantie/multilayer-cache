from multilayer_cache.util import to_async

from typing import Generic
from typing import TypeVar
from typing import Annotated
from typing import Literal

import pydantic


# Represents value type a cache returns
T = TypeVar("T")


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


class CacheResultFound(BaseModel, Generic[T]):
    choice: Literal["found"] = "found"
    value: T

class CacheResultNotFound(BaseModel):
    choice: Literal["not_found"] = "not_found"

class CacheResultError(BaseModel):
    choice: Literal["error"] = "error"
    error: Exception

class CacheResult(BaseModel, Generic[T]):
    value: Annotated[CacheResultFound[T] | CacheResultNotFound | CacheResultError, pydantic.Field(discriminator="choice")]

