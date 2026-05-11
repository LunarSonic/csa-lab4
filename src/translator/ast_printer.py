from src.translator.ast_nodes import (
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


class AstPrinter(NodeVisitor):
    def __init__(self) -> None:
        self.tab = 0

    def print(self, tree) -> None:
        self.visit(tree)

    def _print(self, text) -> None:
        print(" " * self.tab + text)

    def visit_ast_block(self, node: AstBlock) -> None:
        self._print("{")
        self.tab += 1
        for stmt in node.children:
            self.visit(stmt)
        self.tab -= 1
        self._print("}")

    def visit_ast_declaration(self, node: AstDeclaration) -> None:
        self._print(f"Declaration {node.type_}: {node.name}")
        if node.value:
            self.tab += 1
            self.visit(node.value)
            self.tab -= 1

    def visit_ast_assign(self, node: AstAssign) -> None:
        self._print("Assign")
        self.tab += 1
        self.visit(node.ref)
        self.visit(node.expression)
        self.tab -= 1

    def visit_ast_string(self, node: AstString) -> None:
        self._print(f'String: "{node.value}"')

    def visit_ast_number(self, node: AstNumber) -> None:
        self._print(f"Number {node.type_}: {node.value}")

    def visit_ast_array(self, node: AstArray) -> None:
        self._print(f"(size: {node.size})")

    def visit_ast_unary_operation(self, node: AstUnaryOperation) -> None:
        self._print(f"UnaryOp: {node.op}")
        self.tab += 1
        self.visit(node.expression)
        self.tab -= 1

    def visit_ast_print(self, node: AstPrint) -> None:
        self._print("print(")
        self.tab += 1
        self.visit(node.value)
        self.tab -= 1
        self._print(")")

    def visit_ast_read(self, node: AstRead) -> None:
        self._print("read(")
        self.tab += 1
        self.visit(node.variable)
        self.tab -= 1
        self._print(")")

    def visit_ast_variable_reference(self, node: AstVariableReference) -> None:
        self._print(f"VarRef: {node.name}")

    def visit_ast_array_reference(self, node: AstArrayReference) -> None:
        self._print(f"ArrRef: {node.name}[")
        self.tab += 1
        self.visit(node.index)
        self.tab -= 1
        self._print("]")

    def visit_ast_binary_operation(self, node: AstBinaryOperation) -> None:
        self._print(f"BinOp: {node.op}")
        self.tab += 1
        self.visit(node.left)
        self.visit(node.right)
        self.tab -= 1

    def visit_ast_if(self, node: AstIf) -> None:
        self._print("IF")
        self.tab += 1

        self._print("CONDITION:")
        self.tab += 1
        self.visit(node.condition)
        self.tab -= 1

        self._print("IF BLOCK:")
        self.tab += 1
        self.visit(node.if_block)
        self.tab -= 1

        if node.else_block:
            self._print("ELSE:")
            self.tab += 1
            self.visit(node.else_block)
            self.tab -= 1

        self.tab -= 1
        self._print("END IF")

    def visit_ast_while(self, node: AstWhile) -> None:
        self._print("WHILE")
        self.tab += 1

        self._print("CONDITION:")
        self.tab += 1
        self.visit(node.condition)
        self.tab -= 1

        self._print("BODY:")
        self.tab += 1
        self.visit(node.body)
        self.tab -= 1

        self.tab -= 1
        self._print("END WHILE")
