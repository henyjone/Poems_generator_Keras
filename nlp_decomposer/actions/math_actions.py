"""
数学计算相关的原子行为（代码类型）
"""

from nlp_decomposer.action import action


@action(
    name="add",
    description="计算两个数的和",
    parameters={"a": "第一个数", "b": "第二个数"},
)
def add(context, a=0, b=0):
    return float(a) + float(b)


@action(
    name="subtract",
    description="计算两个数的差（a - b）",
    parameters={"a": "被减数", "b": "减数"},
)
def subtract(context, a=0, b=0):
    return float(a) - float(b)


@action(
    name="multiply",
    description="计算两个数的积",
    parameters={"a": "第一个数", "b": "第二个数"},
)
def multiply(context, a=0, b=0):
    return float(a) * float(b)


@action(
    name="divide",
    description="计算两个数的商（a / b）",
    parameters={"a": "被除数", "b": "除数"},
)
def divide(context, a=0, b=1):
    b = float(b)
    if b == 0:
        raise ValueError("除数不能为零")
    return float(a) / b


@action(
    name="compare",
    description="比较两个数的大小，返回 'greater'、'less' 或 'equal'",
    parameters={"a": "第一个数", "b": "第二个数"},
)
def compare(context, a=0, b=0):
    a, b = float(a), float(b)
    if a > b:
        return "greater"
    elif a < b:
        return "less"
    return "equal"


@action(
    name="max_value",
    description="返回一组数中的最大值",
    parameters={"numbers": "数字列表"},
)
def max_value(context, numbers=None):
    if not numbers:
        raise ValueError("数字列表不能为空")
    return max(float(n) for n in numbers)


@action(
    name="min_value",
    description="返回一组数中的最小值",
    parameters={"numbers": "数字列表"},
)
def min_value(context, numbers=None):
    if not numbers:
        raise ValueError("数字列表不能为空")
    return min(float(n) for n in numbers)
