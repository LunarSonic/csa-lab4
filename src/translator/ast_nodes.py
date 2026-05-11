from __future__ import annotations

import re
from typing import Any

from src.translator.symbol import SymbolType


def camel_to_snake(name):
    snake = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", snake).lower()


class NodeVisitor:
    def visit(self, node):
        method = "visit_" + camel_to_snake(node.__class__.__name__)
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"No visit_{node.__class__.__name__} method")


class Ast:
    name: str
    address: int
    type_: SymbolType | None
    value: Any


class AstBlock(Ast):
    def __init__(self, children: list[Ast]) -> None:
        self.children = children


class AstDeclaration(Ast):
    def __init__(self, type_: SymbolType, name: str, value: Ast | None = None) -> None:
        self.name = name
        self.value = value
        self.type_ = type_


class AstAssign(Ast):
    def __init__(
        self, ref: AstVariableReference | AstArrayReference, expression: Ast, type_: SymbolType | None = None
    ) -> None:
        self.ref = ref
        self.expression = expression
        self.type_ = type_


class AstNumber(Ast):
    def __init__(self, value: int, type_: SymbolType = SymbolType.INT) -> None:
        self.value = value
        self.type_ = type_


class AstString(Ast):
    def __init__(self, value: str, address: int = -1, type_: SymbolType = SymbolType.STRING) -> None:
        self.value = value
        self.address = address
        self.type_ = type_


class AstArray(Ast):
    def __init__(self, size: int, address: int = -1) -> None:
        self.size = size
        self.address = address


class AstVariableReference(Ast):
    def __init__(self, name: str, type_: SymbolType | None = None) -> None:
        self.name = name
        self.type_ = type_


class AstArrayReference(Ast):
    def __init__(self, name: str, index: Ast, type_: SymbolType | None = None) -> None:
        self.name = name
        self.index = index
        self.type_ = type_


class AstBinaryOperation(Ast):
    def __init__(self, left: Ast, op: str, right: Ast, type_: SymbolType | None = None) -> None:
        self.left = left
        self.op = op
        self.right = right
        self.type_ = type_


class AstUnaryOperation(Ast):
    def __init__(self, op: str, expression: Ast, type_: SymbolType | None = None) -> None:
        self.op = op
        self.expression = expression
        self.type_ = type_


class AstIf(Ast):
    def __init__(self, condition: Ast, if_block: AstBlock, else_block: AstBlock | None = None) -> None:
        self.condition = condition
        self.if_block = if_block
        self.else_block = else_block


class AstWhile(Ast):
    def __init__(self, condition: Ast, body: AstBlock) -> None:
        self.condition = condition
        self.body = body


class AstPrint(Ast):
    def __init__(self, value: Ast | AstString, port: int = 2, type_: SymbolType = SymbolType.INT) -> None:
        self.value = value
        self.port = port
        self.type_ = type_


class AstRead(Ast):
    def __init__(
        self,
        variable: AstVariableReference | AstArrayReference,
        port: int = 0,
        type_: SymbolType = SymbolType.INT,
    ) -> None:
        self.variable = variable
        self.port = port
        self.type_ = type_
