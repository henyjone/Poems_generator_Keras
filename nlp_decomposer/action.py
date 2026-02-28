"""
原子行为定义与注册表

AtomicAction: 原子行为基类
ActionRegistry: 全局行为注册表
action: 装饰器，快速注册原子行为
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AtomicAction:
    """原子行为

    Attributes:
        name: 行为唯一标识
        description: 行为的自然语言描述（供大模型理解）
        action_type: "code"（代码执行）或 "llm"（大模型生成）
        parameters: 参数说明，格式 {"param_name": "描述"}
        fn: 实际执行函数，签名为 fn(context, **params) -> Any
    """

    name: str
    description: str
    action_type: str = "code"  # "code" | "llm"
    parameters: Dict[str, str] = field(default_factory=dict)
    fn: Optional[Callable] = None

    def execute(self, context: Dict[str, Any], **params) -> Any:
        """执行此原子行为

        Args:
            context: 执行上下文，包含之前步骤的结果
            **params: 行为参数

        Returns:
            行为执行结果
        """
        if self.fn is None:
            raise NotImplementedError(f"原子行为 '{self.name}' 未绑定执行函数")
        return self.fn(context, **params)

    def to_prompt_description(self) -> str:
        """生成供大模型理解的描述文本"""
        params_desc = ""
        if self.parameters:
            params_list = [f"    - {k}: {v}" for k, v in self.parameters.items()]
            params_desc = "\n  参数:\n" + "\n".join(params_list)
        return (
            f"- {self.name}: {self.description} "
            f"[类型: {self.action_type}]{params_desc}"
        )


class ActionRegistry:
    """原子行为注册表"""

    def __init__(self):
        self._actions: Dict[str, AtomicAction] = {}

    def register(self, act: AtomicAction) -> None:
        """注册一个原子行为"""
        self._actions[act.name] = act

    def get(self, name: str) -> AtomicAction:
        """根据名称获取原子行为"""
        if name not in self._actions:
            raise KeyError(f"未找到原子行为: '{name}'，已注册: {list(self._actions.keys())}")
        return self._actions[name]

    def list_actions(self) -> List[AtomicAction]:
        """列出所有已注册的原子行为"""
        return list(self._actions.values())

    def get_prompt_descriptions(self) -> str:
        """生成所有行为的描述文本，用于构建大模型 prompt"""
        lines = [act.to_prompt_description() for act in self._actions.values()]
        return "\n".join(lines)

    def __contains__(self, name: str) -> bool:
        return name in self._actions

    def __len__(self) -> int:
        return len(self._actions)


# ---- 全局默认注册表 ----
_default_registry = ActionRegistry()


def get_default_registry() -> ActionRegistry:
    return _default_registry


def action(
    name: str,
    description: str,
    action_type: str = "code",
    parameters: Optional[Dict[str, str]] = None,
    registry: Optional[ActionRegistry] = None,
):
    """装饰器：将函数注册为原子行为

    用法:
        @action("count_chars", "统计文本字符数", parameters={"text": "输入文本"})
        def count_chars(context, text=""):
            return len(text)
    """
    reg = registry or _default_registry

    def decorator(fn: Callable) -> Callable:
        # 自动推断参数（排除 context）
        params = parameters or {}
        if not params:
            sig = inspect.signature(fn)
            for pname, param in sig.parameters.items():
                if pname == "context":
                    continue
                annotation = param.annotation
                desc = str(annotation) if annotation != inspect.Parameter.empty else "参数"
                params[pname] = desc

        act = AtomicAction(
            name=name,
            description=description,
            action_type=action_type,
            parameters=params,
            fn=fn,
        )
        reg.register(act)
        return fn

    return decorator
