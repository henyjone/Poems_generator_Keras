"""
NLP Decomposer - 自然语言原子行为拆解器

将自然语言表达拆解为若干个原子行为（Atomic Actions），然后依次执行。
支持条件执行和无条件执行，支持大模型生成和代码生成两种行为类型。
"""

from nlp_decomposer.action import AtomicAction, ActionRegistry, action
from nlp_decomposer.plan import ActionStep, ActionPlan
from nlp_decomposer.decomposer import NLDecomposer
from nlp_decomposer.executor import PlanExecutor

__all__ = [
    "AtomicAction",
    "ActionRegistry",
    "action",
    "ActionStep",
    "ActionPlan",
    "NLDecomposer",
    "PlanExecutor",
]
