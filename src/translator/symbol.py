from enum import Enum
from typing import Any


class SymbolType(str, Enum):
    INT = "int"
    LONG = "long"
    STRING = "string"
    ARRAY = "array"


class Symbol:
    def __init__(self, name, type_, address=-1) -> None:
        self.name = name
        self.type_ = type_
        self.address = address


class SymbolTable:
    def __init__(self) -> None:
        self.symbols: dict[str, Any] = {}

    def declare(self, symbol):
        if symbol.name in self.symbols:
            raise Exception(f"{symbol.name} has been already declared")
        self.symbols[symbol.name] = symbol

    def lookup(self, name):
        return self.symbols.get(name)

    def define_address(self, name, address) -> None:
        self.symbols[name].address = address
