import math
import ast
import operator
from typing import Any
from tools.base import tool
from core.security import SecurityLevel

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
}


def _safe_eval(expr: str):
    tree = ast.parse(expr.strip(), mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Constante não numérica: {node.value}")
        elif isinstance(node, ast.BinOp):
            op_func = SAFE_OPS.get(type(node.op))
            if not op_func:
                raise ValueError(f"Operação não permitida: {type(node.op).__name__}")
            return op_func(_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            op_func = SAFE_OPS.get(type(node.op))
            if not op_func:
                raise ValueError(f"Operação não permitida: {type(node.op).__name__}")
            return op_func(_eval(node.operand))
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name not in SAFE_NAMES:
                raise ValueError(f"Função não permitida: {func_name}")
            args = [_eval(arg) for arg in node.args]
            return SAFE_NAMES[func_name](*args)
        elif isinstance(node, ast.Name):
            if node.id in SAFE_NAMES:
                return SAFE_NAMES[node.id]
            raise ValueError(f"Nome não permitido: {node.id}")
        raise ValueError(f"Expressão não suportada: {type(node).__name__}")

    return _eval(tree)


@tool("calculate", security_level=SecurityLevel.SAFE, cloud_compatible=True)
def calculate(args: Any) -> str:
    """Avalia expressões matemáticas com funções seguras (sin, cos, sqrt, log, etc)."""
    expr = args if isinstance(args, str) else args.get("expression", "")
    if not expr:
        return "Nenhuma expressão fornecida."

    try:
        result = _safe_eval(expr)
        if isinstance(result, float):
            if result == int(result):
                result = int(result)
            else:
                result = round(result, 10)
        return str(result)
    except Exception as e:
        return f"Erro: {e}"
