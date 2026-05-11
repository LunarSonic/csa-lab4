from enum import Enum


class Token:
    def __init__(self, type_, value, line=None, column=None) -> None:
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r})"


class TokenType(Enum):
    IF = "if"
    ELSE = "else"
    WHILE = "while"
    PRINT = "print"
    READ = "read"
    INT = "int"
    LONG = "long"
    STRING_TYPE = "string"
    ARRAY = "array"

    ASSIGN = "="
    PLUS = "+"
    MINUS = "-"
    MUL = "*"
    DIV = "/"
    MOD = "%"

    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER = ">"
    LESS = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="

    AND = "&&"
    OR = "||"
    BIT_AND = "&"
    BIT_OR = "|"
    NOT = "!"

    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"

    SEMICOLON = ";"

    NUMBER = "NUMBER"
    VARIABLE_NAME = "ID"
    STRING = "STRING"
    EOF = "EOF"
