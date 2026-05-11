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


class AstFormatter(NodeVisitor):
    def __init__(self) -> None:
        self.indent_level = 0

    def format(self, node: Ast) -> str:
        result = str(self.visit(node))
        if result.startswith("(") and result.endswith(")"):
            return result[1:-1]
        return result

    def _indent(self) -> str:
        return "    " * self.indent_level

    def visit_ast_block(self, node: AstBlock) -> str:
        lines = []
        for child in node.children:
            res = self.visit(child)
            if res:
                lines.append(str(res))
        return "\n".join(lines)

    def visit_ast_declaration(self, node: AstDeclaration) -> str:
        val_str = ""
        if node.value:
            val = str(self.visit(node.value))
            if val.startswith("(") and val.endswith(")"):
                val = val[1:-1]
            val_str = f" = {val}"
        assert node.type_ is not None, "Declaration node must have a type"
        return f"{self._indent()}{node.type_.name.lower()} {node.name}{val_str};"

    def visit_ast_assign(self, node: AstAssign) -> str:
        expr = str(self.visit(node.expression))
        if expr.startswith("(") and expr.endswith(")"):
            expr = expr[1:-1]
        return f"{self._indent()}{self.visit(node.ref)} = {expr};"

    def visit_ast_if(self, node: AstIf) -> str:
        cond = str(self.visit(node.condition))
        if cond.startswith("(") and cond.endswith(")"):
            cond = cond[1:-1]

        res = f"{self._indent()}if ({cond}) {{\n"
        self.indent_level += 1
        res += self.visit(node.if_block)
        self.indent_level -= 1
        res += f"\n{self._indent()}}}"

        if node.else_block:
            res += " else {\n"
            self.indent_level += 1
            res += self.visit(node.else_block)
            self.indent_level -= 1
            res += f"\n{self._indent()}}}"
        return res

    def visit_ast_while(self, node: AstWhile) -> str:
        cond = str(self.visit(node.condition))
        if cond.startswith("(") and cond.endswith(")"):
            cond = cond[1:-1]

        res = f"{self._indent()}while ({cond}) {{\n"
        self.indent_level += 1
        res += self.visit(node.body)
        self.indent_level -= 1
        res += f"\n{self._indent()}}}"
        return res

    def visit_ast_print(self, node: AstPrint) -> str:
        val = str(self.visit(node.value))
        if val.startswith("(") and val.endswith(")"):
            val = val[1:-1]
        return f"{self._indent()}print({val});"

    def visit_ast_read(self, node: AstRead) -> str:
        return f"{self._indent()}read({self.visit(node.variable)});"

    def visit_ast_binary_operation(self, node: AstBinaryOperation) -> str:
        return f"({self.visit(node.left)} {node.op} {self.visit(node.right)})"

    def visit_ast_unary_operation(self, node: AstUnaryOperation) -> str:
        return f"{node.op}{self.visit(node.expression)}"

    def visit_ast_number(self, node: AstNumber) -> str:
        return str(node.value)

    def visit_ast_string(self, node: AstString) -> str:
        val = node.value.replace("\n", "\\n")
        return f'"{val}"'

    def visit_ast_variable_reference(self, node: AstVariableReference) -> str:
        return node.name

    def visit_ast_array_reference(self, node: AstArrayReference) -> str:
        idx = str(self.visit(node.index))
        if idx.startswith("(") and idx.endswith(")"):
            idx = idx[1:-1]
        return f"{node.name}[{idx}]"

    def visit_ast_array(self, node: AstArray) -> str:
        return f"{{{node.size}}}"
