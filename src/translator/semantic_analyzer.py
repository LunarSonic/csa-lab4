from typing import Any

from src.translator.ast_nodes import (
    Ast,
    AstArray,
    AstArrayReference,
    AstAssign,
    AstBinaryOperation,
    AstBlock,
    AstDeclaration,
    AstIf,
    AstNumber,
    AstPrint,
    AstRead,
    AstString,
    AstUnaryOperation,
    AstVariableReference,
    AstWhile,
    NodeVisitor,
)
from src.translator.symbol import Symbol, SymbolTable, SymbolType
from src.util.exceptions import (
    ArrayInitializationError,
    AssignmentTypeError,
    IllegalDeclarationError,
    InvalidArrayIndexError,
    InvalidConditionError,
    NameAlreadyDeclaredError,
    NameNotDeclaredError,
    NotAnArrayError,
    TypeMismatchError,
)


class SemanticAnalyzer(NodeVisitor):
    def __init__(self) -> None:
        self.symbol_table = SymbolTable()
        self.data_address_counter = 0
        self.is_top_level = True
        self.string_literals: list[Any] = []

    def analyze(self, tree):
        if isinstance(tree, AstBlock):
            for stmt in tree.children:
                self.visit(stmt)
        else:
            self.visit(tree)
        return self.symbol_table, self.string_literals

    def visit_ast_block(self, node) -> None:
        old_top_level = self.is_top_level
        self.is_top_level = False
        for stmt in node.children:
            self.visit(stmt)
        self.is_top_level = old_top_level

    def visit_ast_declaration(self, node: AstDeclaration):
        if not self.is_top_level:
            raise IllegalDeclarationError(node.name)

        if self.symbol_table.lookup(node.name):
            raise NameAlreadyDeclaredError(node.name)

        address = self.data_address_counter

        if node.type_ == SymbolType.ARRAY:
            if not isinstance(node.value, AstArray):
                raise ArrayInitializationError(node.name)
            self.data_address_counter += node.value.size
        elif node.type_ == SymbolType.LONG:
            self.data_address_counter += 2
        else:
            self.data_address_counter += 1

        symbol = Symbol(node.name, node.type_, address)
        self.symbol_table.declare(symbol)

        if node.type_ != SymbolType.ARRAY and node.value:
            assert node.type_ is not None
            self.resolve_expression_type(node.value, node.type_)

    def visit_ast_assign(self, node: AstAssign):
        symbol = self.symbol_table.lookup(node.ref.name)
        if symbol is None:
            raise NameNotDeclaredError(node.ref.name)

        if isinstance(node.ref, AstArrayReference):
            if symbol.type_ != SymbolType.ARRAY:
                raise NotAnArrayError(node.ref.name)
            try:
                self.resolve_expression_type(node.ref.index, SymbolType.INT)
            except TypeMismatchError:
                raise InvalidArrayIndexError() from None
            self.resolve_expression_type(node.expression, SymbolType.INT)
        else:
            try:
                assert symbol.type_ is not None, f"Symbol {symbol.name} must have a type"
                self.resolve_expression_type(node.expression, symbol.type_)
            except TypeMismatchError:
                raise AssignmentTypeError(node.ref.name, actual=symbol.type_) from None

    def visit_ast_binary_operation(self, node: AstBinaryOperation) -> None:
        target_type = self.infer_type(node)
        self.resolve_expression_type(node, target_type)

    def visit_ast_unary_operation(self, node: AstUnaryOperation) -> None:
        target_type = self.infer_type(node)
        self.resolve_expression_type(node, target_type)

    def visit_ast_number(self, node: AstNumber) -> None:
        if node.type_ is None:
            node.type_ = SymbolType.INT

    def visit_ast_variable_reference(self, node: AstVariableReference):
        symbol = self.symbol_table.lookup(node.name)
        if symbol is None:
            raise NameNotDeclaredError(node.name)
        node.type_ = symbol.type_

    def visit_ast_array_reference(self, node: AstArrayReference):
        symbol = self.symbol_table.lookup(node.name)
        if symbol is None:
            raise NameNotDeclaredError(node.name)
        if symbol.type_ not in (SymbolType.ARRAY, SymbolType.LONG, SymbolType.STRING):
            raise NotAnArrayError(node.name)
        try:
            self.resolve_expression_type(node.index, SymbolType.INT)
        except TypeMismatchError:
            raise InvalidArrayIndexError() from None
        node.type_ = SymbolType.INT

    def visit_ast_string(self, node: AstString) -> None:
        node.type_ = SymbolType.STRING
        if node not in self.string_literals:
            self.string_literals.append(node)

    def visit_ast_if(self, node: AstIf):
        try:
            self.resolve_expression_type(node.condition, SymbolType.INT)
        except TypeMismatchError:
            raise InvalidConditionError() from None
        self.visit(node.if_block)
        if node.else_block:
            self.visit(node.else_block)

    def visit_ast_while(self, node: AstWhile):
        try:
            self.resolve_expression_type(node.condition, SymbolType.INT)
        except TypeMismatchError:
            raise InvalidConditionError() from None
        self.visit(node.body)

    def visit_ast_print(self, node: AstPrint) -> None:
        self.visit(node.value)
        symbol = None
        if hasattr(node.value, "name"):
            symbol = self.symbol_table.lookup(node.value.name)
        if isinstance(node.value, AstString) or (symbol and symbol.type_ == SymbolType.STRING):
            node.port = 3
            node.type_ = SymbolType.STRING
        else:
            node.port = 2
            node.type_ = SymbolType.INT

    def visit_ast_read(self, node: AstRead):
        symbol = self.symbol_table.lookup(node.variable.name)
        if symbol is None:
            raise NameNotDeclaredError(node.variable.name)
        if symbol.type_ == SymbolType.STRING:
            node.port = 1
        else:
            node.port = 0

        if not isinstance(node.variable, AstVariableReference):
            self.visit(node.variable)

    def resolve_expression_type(self, node: Ast, expected: SymbolType):
        if isinstance(node, AstNumber):
            node.type_ = expected
            return

        if isinstance(node, AstString):
            node.type_ = SymbolType.STRING
            if expected != SymbolType.STRING:
                raise TypeMismatchError(expected, SymbolType.STRING)
            return

        if isinstance(node, AstVariableReference):
            symbol = self.symbol_table.lookup(node.name)
            if not symbol:
                raise NameNotDeclaredError(node.name)
            if symbol.type_ == SymbolType.INT and expected == SymbolType.LONG:
                node.type_ = SymbolType.LONG
            else:
                if symbol.type_ != expected:
                    raise TypeMismatchError(expected, symbol.type_)
                node.type_ = symbol.type_
            return

        if isinstance(node, AstArrayReference):
            symbol = self.symbol_table.lookup(node.name)
            if symbol.type_ not in (SymbolType.ARRAY, SymbolType.LONG, SymbolType.STRING):
                raise NotAnArrayError(node.name)
            self.resolve_expression_type(node.index, SymbolType.INT)
            node.type_ = SymbolType.INT
            if expected == SymbolType.LONG:
                node.type_ = SymbolType.LONG
            return

        if isinstance(node, AstBinaryOperation):
            if node.op in ["&&", "||", "==", "!=", ">", "<", ">=", "<="]:
                left_type = self.infer_type(node.left)
                right_type = self.infer_type(node.right)
                operand_type = (
                    SymbolType.LONG
                    if (left_type == SymbolType.LONG or right_type == SymbolType.LONG)
                    else SymbolType.INT
                )
                self.resolve_expression_type(node.left, operand_type)
                self.resolve_expression_type(node.right, operand_type)
                node.type_ = SymbolType.INT
                if expected == SymbolType.LONG:
                    node.type_ = SymbolType.LONG
            else:
                self.resolve_expression_type(node.left, expected)
                self.resolve_expression_type(node.right, expected)
                node.type_ = expected
            return

        if isinstance(node, AstUnaryOperation):
            if node.op == "!":
                inner_type = self.infer_type(node.expression)
                self.resolve_expression_type(node.expression, inner_type)
                node.type_ = expected
            else:
                self.resolve_expression_type(node.expression, expected)
                node.type_ = expected
            return

    def infer_type(self, node: Ast):
        if isinstance(node, AstNumber):
            return node.type_ if node.type_ else SymbolType.INT
        if isinstance(node, AstVariableReference):
            sym = self.symbol_table.lookup(node.name)
            return sym.type_ if sym else SymbolType.INT
        if isinstance(node, AstBinaryOperation):
            if node.op in ["==", "!=", ">", "<", ">=", "<=", "&&", "||"]:
                return SymbolType.INT
            left_type = self.infer_type(node.left)
            right_type = self.infer_type(node.right)
            if left_type == SymbolType.LONG or right_type == SymbolType.LONG:
                return SymbolType.LONG
            return left_type
        if isinstance(node, AstUnaryOperation):
            return self.infer_type(node.expression)
        return SymbolType.INT
