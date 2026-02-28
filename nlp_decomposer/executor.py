"""
执行计划执行器

PlanExecutor: 按计划依次执行原子行为，支持条件判断和结果引用
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from nlp_decomposer.action import ActionRegistry, get_default_registry
from nlp_decomposer.plan import ActionPlan, ActionStep


class ExecutionResult:
    """执行结果集合"""

    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.skipped: List[str] = []
        self.errors: Dict[str, str] = {}
        self.execution_order: List[str] = []

    def __getitem__(self, key: str) -> Any:
        return self.results[key]

    def __contains__(self, key: str) -> bool:
        return key in self.results

    def summary(self) -> str:
        lines = [f"执行完成: {len(self.results)} 步成功"]
        if self.skipped:
            lines.append(f"  跳过: {self.skipped}")
        if self.errors:
            lines.append(f"  失败: {list(self.errors.keys())}")
        for step_id in self.execution_order:
            if step_id in self.results:
                val = self.results[step_id]
                val_str = str(val)
                if len(val_str) > 100:
                    val_str = val_str[:100] + "..."
                lines.append(f"  [{step_id}] = {val_str}")
            elif step_id in self.errors:
                lines.append(f"  [{step_id}] 错误: {self.errors[step_id]}")
        return "\n".join(lines)


class PlanExecutor:
    """执行计划执行器

    按顺序执行 ActionPlan 中的每个步骤，支持:
    - 条件执行: 根据 condition 表达式决定是否执行
    - 结果引用: 参数值中的 $results.step_id 会被替换为实际结果
    - 错误处理: 单步失败可选择继续或中止
    """

    def __init__(
        self,
        registry: Optional[ActionRegistry] = None,
        stop_on_error: bool = False,
    ):
        self.registry = registry or get_default_registry()
        self.stop_on_error = stop_on_error

    def _resolve_ref(self, value: Any, results: Dict[str, Any]) -> Any:
        """解析参数中的引用表达式

        支持:
        - "$results.step_id" -> results["step_id"]
        - "$results.step_id.key" -> results["step_id"]["key"] 或 .key 属性
        - 字符串中嵌入引用: "前缀$results.step_id后缀"
        """
        if not isinstance(value, str):
            return value

        # 完全匹配: 整个值就是一个引用
        full_match = re.fullmatch(r"\$results\.(\w+(?:\.\w+)*)", value)
        if full_match:
            return self._get_nested(results, full_match.group(1))

        # 部分匹配: 字符串中包含引用，替换为字符串表示
        def replacer(m):
            return str(self._get_nested(results, m.group(1)))

        return re.sub(r"\$results\.(\w+(?:\.\w+)*)", replacer, value)

    def _get_nested(self, results: Dict[str, Any], path: str) -> Any:
        """按路径获取嵌套值，如 "step1.key.subkey" """
        parts = path.split(".")
        current = results
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"无法解析引用路径: $results.{path}（在 '{part}' 处失败）")
        return current

    def _resolve_params(
        self, params: Dict[str, Any], results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析步骤参数中所有的引用"""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, list):
                resolved[key] = [self._resolve_ref(v, results) for v in value]
            elif isinstance(value, dict):
                resolved[key] = self._resolve_params(value, results)
            else:
                resolved[key] = self._resolve_ref(value, results)
        return resolved

    def _evaluate_condition(
        self, condition: str, results: Dict[str, Any]
    ) -> bool:
        """评估条件表达式

        条件中可以使用 $results.step_id 引用之前步骤的结果。
        支持简单的比较表达式和布尔值判断。
        """
        if not condition:
            return True

        # 替换引用为实际值
        def replacer(m):
            val = self._get_nested(results, m.group(1))
            if isinstance(val, str):
                return repr(val)
            return repr(val)

        expr = re.sub(r"\$results\.(\w+(?:\.\w+)*)", replacer, condition)

        # 安全评估: 只允许比较运算和基本类型
        allowed_names = {"True": True, "False": False, "None": None, "true": True, "false": False}
        try:
            return bool(eval(expr, {"__builtins__": {}}, allowed_names))  # noqa: S307
        except Exception as e:
            raise ValueError(f"条件表达式求值失败: '{condition}' -> '{expr}': {e}") from e

    def execute(self, plan: ActionPlan) -> ExecutionResult:
        """执行完整的行为计划

        Args:
            plan: 执行计划

        Returns:
            ExecutionResult 包含所有步骤的结果
        """
        exec_result = ExecutionResult()

        for step in plan.steps:
            exec_result.execution_order.append(step.step_id)

            # 条件判断
            if step.condition:
                try:
                    should_run = self._evaluate_condition(
                        step.condition, exec_result.results
                    )
                except Exception as e:
                    exec_result.errors[step.step_id] = f"条件评估失败: {e}"
                    if self.stop_on_error:
                        break
                    continue

                if not should_run:
                    exec_result.skipped.append(step.step_id)
                    continue

            # 获取原子行为
            try:
                action = self.registry.get(step.action_name)
            except KeyError as e:
                exec_result.errors[step.step_id] = str(e)
                if self.stop_on_error:
                    break
                continue

            # 解析参数引用
            try:
                resolved_params = self._resolve_params(
                    step.params, exec_result.results
                )
            except KeyError as e:
                exec_result.errors[step.step_id] = f"参数解析失败: {e}"
                if self.stop_on_error:
                    break
                continue

            # 执行行为
            try:
                result = action.execute(
                    context=exec_result.results, **resolved_params
                )
                exec_result.results[step.step_id] = result
            except Exception as e:
                exec_result.errors[step.step_id] = f"执行失败: {e}"
                if self.stop_on_error:
                    break

        return exec_result
