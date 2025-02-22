from typing import TypeAlias
from typing import TypeVar

import pydantic


BlobId: TypeAlias = str
FileContents: TypeAlias = str

T = TypeVar("T")


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

