from multilayer_cache.examples.parsed_files.defs import ParserVersion
from multilayer_cache.examples.parsed_files.defs import T

from typing import Protocol
from typing import Generic
from typing import Any



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

