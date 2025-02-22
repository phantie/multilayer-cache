from typing import TypeAlias
from typing import TypeVar
from typing import Protocol
from typing import Generic
from typing import Any


import pydantic


BlobId: TypeAlias = str
ParserVersion: TypeAlias = str
FileContents: TypeAlias = str

T = TypeVar("T")


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


class Bucket(BaseModel):
    files: dict[BlobId, FileContents]

    def get(self, blob_id: BlobId, default) -> FileContents:
        return self.files.get(blob_id, default)


class Parser(Protocol, Generic[T]):
    def version(self) -> ParserVersion:
        ...
    
    def parse(self, value: Any) -> T:
        ...


class JsonParser(Parser):
    def version(self) -> str:
        return "0"

    def parse(self, value: Any) -> Any:
        import json
        return json.loads(value)

