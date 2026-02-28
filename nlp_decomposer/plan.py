"""
行为执行计划

ActionStep: 单个执行步骤
ActionPlan: 完整的执行计划
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActionStep:
    """单个执行步骤

    Attributes:
        step_id: 步骤唯一标识，供后续步骤引用结果
        action_name: 对应的原子行为名称
        params: 行为参数。值可以是字面量，也可以是引用表达式：
                - "$results.step_id" 引用某步骤的结果
                - "$results.step_id.key" 引用结果中的某个字段
        condition: 条件表达式（可选）。为 None 表示无条件执行。
                   支持引用 $results.step_id 来做条件判断。
                   例如: "$results.check_length > 10"
    """

    step_id: str
    action_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "step_id": self.step_id,
            "action_name": self.action_name,
            "params": self.params,
        }
        if self.condition:
            d["condition"] = self.condition
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ActionStep:
        return cls(
            step_id=data["step_id"],
            action_name=data["action_name"],
            params=data.get("params", {}),
            condition=data.get("condition"),
        )


@dataclass
class ActionPlan:
    """执行计划：由若干 ActionStep 组成

    Attributes:
        steps: 按顺序执行的步骤列表
        original_text: 原始自然语言文本
        explanation: 大模型对拆解逻辑的解释
    """

    steps: List[ActionStep] = field(default_factory=list)
    original_text: str = ""
    explanation: str = ""

    def add_step(
        self,
        step_id: str,
        action_name: str,
        params: Optional[Dict[str, Any]] = None,
        condition: Optional[str] = None,
    ) -> ActionStep:
        step = ActionStep(
            step_id=step_id,
            action_name=action_name,
            params=params or {},
            condition=condition,
        )
        self.steps.append(step)
        return step

    def to_dict(self) -> dict:
        return {
            "original_text": self.original_text,
            "explanation": self.explanation,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ActionPlan:
        return cls(
            original_text=data.get("original_text", ""),
            explanation=data.get("explanation", ""),
            steps=[ActionStep.from_dict(s) for s in data.get("steps", [])],
        )

    def __str__(self) -> str:
        lines = [f"执行计划 ({len(self.steps)} 步):"]
        if self.original_text:
            lines.append(f"  原文: {self.original_text}")
        if self.explanation:
            lines.append(f"  解释: {self.explanation}")
        for i, step in enumerate(self.steps, 1):
            cond = f" [条件: {step.condition}]" if step.condition else ""
            lines.append(
                f"  {i}. [{step.step_id}] {step.action_name}"
                f"({step.params}){cond}"
            )
        return "\n".join(lines)
