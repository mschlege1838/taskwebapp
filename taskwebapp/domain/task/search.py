
from enum import Enum, auto

# Declaring more complex model than necessary now. Ideally will present SQL-based, Jira-esque interface.
class TaskSearchLogicalOp(Enum):
    AND = auto()
    OR = auto()

class TaskSearchStrOp(Enum):
    STARTS_WITH = auto()
    CONTAINS = auto()
    EQUALS = auto()

class TaskSearchNumOp(Enum):
    EQ = auto()
    GTE = auto()
    LTE = auto()
    GT = auto()
    LT = auto()
    NE = auto()

class TaskSearchField(Enum):
    NAME = auto()
    DUE = auto()
    STATUS = auto()
    TAGS = auto()


class TaskSearchSimpleExpr:
    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value
    
    def __str__(self):
        return f'{self.field.name} {self.op.name} {self.value}'

class TaskSearchIsAnyExpr:
    def __init__(self, field, values):
        self.field = field
        self.values = values
    
    def __str__(self):
        return f'{self.field.name} IS ANY ({", ".join(str(v) for v in self.values)})'

class TaskSearchExpr:
    def __init__(self, left_expr, op, right_expr):
        self.left_expr = left_expr
        self.op = op
        self.right_expr = right_expr
    
    def __str__(self):
        return f'{self.left_expr} {self.op.name} {self.right_expr}'

class TaskSearchGroupExpr:
    def __init__(self, expr):
        self.expr = expr
    
    def __str__(self):
        return f'({self.expr})'

