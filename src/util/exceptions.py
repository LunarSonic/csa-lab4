class CompileError(Exception):
    def __init__(self, message, token=None) -> None:
        self.message = message
        self.token = token
        if token and hasattr(token, "line") and hasattr(token, "column"):
            super().__init__(f"{message} at line {token.line}, column {token.column}")
        else:
            super().__init__(message)


class LexicalError(CompileError):
    pass


class UnknownSymbolError(LexicalError):
    def __init__(self, char, token=None) -> None:
        super().__init__(f"Unknown symbol: '{char}'", token)


class ParseError(CompileError):
    pass


class UnexpectedTokenError(ParseError):
    def __init__(self, token, expected=None) -> None:
        if expected:
            message = f"Unexpected token: '{token.value}', expected '{expected}'"
        else:
            message = f"Unexpected token: '{token.value}'"
        super().__init__(message)


class SemanticError(CompileError):
    pass


class NameAlreadyDeclaredError(SemanticError):
    def __init__(self, name, token=None) -> None:
        super().__init__(f"Variable '{name}' is already declared", token)


class NameNotDeclaredError(SemanticError):
    def __init__(self, name, token=None) -> None:
        super().__init__(f"Variable '{name}' is not declared", token)


class TypeMismatchError(SemanticError):
    def __init__(self, expected, actual, token=None) -> None:
        super().__init__(f"Type mismatch: expected {expected}, got {actual}", token)


class InvalidConditionError(SemanticError):
    def __init__(self, token=None) -> None:
        super().__init__("Condition must be INT", token)


class UnsupportedTypeError(SemanticError):
    def __init__(self, type_, token=None) -> None:
        super().__init__(f"Unsupported type '{type_}", token)


class NotAnArrayError(SemanticError):
    def __init__(self, name, token=None) -> None:
        super().__init__(f"'{name}' is not an array", token)


class InvalidArrayIndexError(SemanticError):
    def __init__(self, token=None) -> None:
        super().__init__("Array index must be INT", token)


class AssignmentTypeError(SemanticError):
    def __init__(self, var_name: str, actual=None, token=None) -> None:
        if actual:
            message = f"Cannot assign value of type '{actual}' to variable '{var_name}'"
        else:
            message = f"Invalid assignment to variable '{var_name}'"
        super().__init__(message, token)


class ArrayInitializationError(SemanticError):
    def __init__(self, name, token=None) -> None:
        super().__init__(f"Array '{name}' must be initialized with a size in braces", token)


class IllegalDeclarationError(SemanticError):
    def __init__(self, name, token=None) -> None:
        super().__init__(
            f"Variable '{name}' cannot be declared inside a block. All declarations must be at the top level", token
        )
