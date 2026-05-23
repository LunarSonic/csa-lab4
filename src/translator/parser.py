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
)
from src.translator.lexical_analyzer import LexicalAnalyzer
from src.translator.symbol import SymbolType
from src.translator.token import TokenType
from src.util.exceptions import UnexpectedTokenError

type_map = {
    TokenType.INT: SymbolType.INT,
    TokenType.LONG: SymbolType.LONG,
    TokenType.STRING_TYPE: SymbolType.STRING,
    TokenType.ARRAY: SymbolType.ARRAY,
}


class Parser:
    def __init__(self, lexical_analyzer: LexicalAnalyzer) -> None:
        self.lexical_analyzer = lexical_analyzer
        self.current_token = lexical_analyzer.get_next_token()

    def error(self, expected=None):
        raise UnexpectedTokenError(self.current_token, expected)

    def process(self, token_type):
        if self.current_token.type == token_type:
            self.current_token = self.lexical_analyzer.get_next_token()
        else:
            raise UnexpectedTokenError(self.current_token, token_type)

    def parse_program(self):
        statements = []
        while self.current_token.type != TokenType.EOF:
            statements.append(self.parse_statement())
        return AstBlock(statements)

    def parse_statement(self):
        tok = self.current_token
        if tok.type in (TokenType.INT, TokenType.LONG, TokenType.STRING_TYPE, TokenType.ARRAY):
            return self.parse_declaration()
        if tok.type == TokenType.VARIABLE_NAME:
            return self.parse_assignment()
        if tok.type == TokenType.IF:
            return self.parse_if()
        if tok.type == TokenType.WHILE:
            return self.parse_while()
        if tok.type == TokenType.PRINT:
            return self.parse_print()
        if tok.type == TokenType.READ:
            return self.parse_read()
        if tok.type == TokenType.LBRACE:
            return self.parse_block()
        self.error("Unknown statement")
        return None

    def parse_block(self):
        self.process(TokenType.LBRACE)
        statements = []
        while self.current_token.type != TokenType.RBRACE:
            statements.append(self.parse_statement())
        self.process(TokenType.RBRACE)
        return AstBlock(statements)

    def parse_declaration(self):
        type_token = self.current_token
        self.process(type_token.type)
        var_name = self.current_token.value
        self.process(TokenType.VARIABLE_NAME)
        self.process(TokenType.ASSIGN)
        if type_token.type in (TokenType.ARRAY, TokenType.STRING_TYPE) and self.current_token.type == TokenType.LBRACE:
            self.process(TokenType.LBRACE)
            size = int(self.current_token.value)
            self.process(TokenType.NUMBER)
            self.process(TokenType.RBRACE)
            value = AstArray(size)
        else:
            value = self.parse_expression()
        self.process(TokenType.SEMICOLON)
        symbol_type = type_map[type_token.type]
        return AstDeclaration(symbol_type, var_name, value)

    def parse_assignment(self):
        ref: Ast
        var_token = self.current_token
        self.process(TokenType.VARIABLE_NAME)
        if self.current_token.type == TokenType.LBRACKET:
            self.process(TokenType.LBRACKET)
            index_expr = self.parse_expression()
            self.process(TokenType.RBRACKET)
            ref = AstArrayReference(var_token.value, index_expr)
        else:
            ref = AstVariableReference(var_token.value)
        self.process(TokenType.ASSIGN)
        expr = self.parse_expression()
        self.process(TokenType.SEMICOLON)
        return AstAssign(ref, expr)

    def parse_if(self):
        self.process(TokenType.IF)
        self.process(TokenType.LPAREN)
        condition = self.parse_expression()
        self.process(TokenType.RPAREN)
        if_block = self.parse_block()
        else_block = None
        if self.current_token.type == TokenType.ELSE:
            self.process(TokenType.ELSE)
            else_block = self.parse_block()
        return AstIf(condition, if_block, else_block)

    def parse_while(self):
        self.process(TokenType.WHILE)
        self.process(TokenType.LPAREN)
        condition = self.parse_expression()
        self.process(TokenType.RPAREN)
        body = self.parse_block()
        return AstWhile(condition, body)

    def parse_print(self):
        self.process(TokenType.PRINT)
        self.process(TokenType.LPAREN)
        if self.current_token.type == TokenType.STRING:
            value = AstString(self.current_token.value)
            self.process(TokenType.STRING)
        else:
            value = self.parse_expression()
        self.process(TokenType.RPAREN)
        self.process(TokenType.SEMICOLON)
        return AstPrint(value)

    def parse_read(self):
        self.process(TokenType.READ)
        self.process(TokenType.LPAREN)
        var_token = self.current_token
        self.process(TokenType.VARIABLE_NAME)
        ref: Ast
        if self.current_token.type == TokenType.LBRACKET:
            self.process(TokenType.LBRACKET)
            index_expr = self.parse_expression()
            self.process(TokenType.RBRACKET)
            ref = AstArrayReference(var_token.value, index_expr)
        else:
            ref = AstVariableReference(var_token.value)
        self.process(TokenType.RPAREN)
        self.process(TokenType.SEMICOLON)
        return AstRead(ref)

    def parse_expression(self):
        return self.parse_logical_or()

    def parse_logical_or(self):
        node = self.parse_logical_and()
        while self.current_token.type == TokenType.OR:
            op = self.current_token.value
            self.process(TokenType.OR)
            node = AstBinaryOperation(node, op, self.parse_logical_and())
        return node

    def parse_logical_and(self):
        node = self.parse_bitwise_or()
        while self.current_token.type == TokenType.AND:
            op = self.current_token.value
            self.process(TokenType.AND)
            node = AstBinaryOperation(node, op, self.parse_bitwise_or())
        return node

    def parse_bitwise_or(self):
        node = self.parse_bitwise_and()
        while self.current_token.type == TokenType.BIT_OR:
            op = self.current_token.value
            self.process(TokenType.BIT_OR)
            node = AstBinaryOperation(node, op, self.parse_bitwise_and())
        return node

    def parse_bitwise_and(self):
        node = self.parse_equality()
        while self.current_token.type == TokenType.BIT_AND:
            op = self.current_token.value
            self.process(TokenType.BIT_AND)
            node = AstBinaryOperation(node, op, self.parse_equality())
        return node

    def parse_equality(self):
        node = self.parse_relation()
        while self.current_token.type in (TokenType.EQUALS, TokenType.NOT_EQUALS):
            op = self.current_token.value
            self.process(self.current_token.type)
            node = AstBinaryOperation(node, op, self.parse_relation())
        return node

    def parse_relation(self):
        node = self.parse_addition()
        while self.current_token.type in (
            TokenType.GREATER,
            TokenType.LESS,
            TokenType.GREATER_EQUAL,
            TokenType.LESS_EQUAL,
        ):
            op = self.current_token.value
            self.process(self.current_token.type)
            node = AstBinaryOperation(node, op, self.parse_addition())
        return node

    def parse_addition(self):
        node = self.parse_multiplication()
        while self.current_token.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current_token.value
            self.process(self.current_token.type)
            node = AstBinaryOperation(node, op, self.parse_multiplication())
        return node

    def parse_multiplication(self):
        node = self.parse_unary()
        while self.current_token.type in (TokenType.MUL, TokenType.DIV, TokenType.MOD):
            op = self.current_token.value
            self.process(self.current_token.type)
            node = AstBinaryOperation(node, op, self.parse_unary())
        return node

    def parse_unary(self):
        if self.current_token.type in (TokenType.PLUS, TokenType.MINUS, TokenType.NOT):
            op = self.current_token.value
            self.process(self.current_token.type)
            return AstUnaryOperation(op, self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        tok = self.current_token
        if tok.type == TokenType.NUMBER:
            self.process(TokenType.NUMBER)
            return AstNumber(int(tok.value))

        if tok.type == TokenType.STRING:
            val = tok.value
            self.process(TokenType.STRING)
            return AstString(val)

        if tok.type == TokenType.VARIABLE_NAME:
            self.process(TokenType.VARIABLE_NAME)
            if self.current_token.type == TokenType.LBRACKET:
                self.process(TokenType.LBRACKET)
                index_expr = self.parse_expression()
                self.process(TokenType.RBRACKET)
                return AstArrayReference(tok.value, index_expr)
            return AstVariableReference(tok.value)

        if tok.type == TokenType.LPAREN:
            self.process(TokenType.LPAREN)
            expr = self.parse_expression()
            self.process(TokenType.RPAREN)
            return expr
        self.error("Unexpected token in expression")
        raise UnexpectedTokenError(self.current_token, "Primary Expression")
