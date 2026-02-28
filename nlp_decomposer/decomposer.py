"""
自然语言拆解器

NLDecomposer: 使用大模型将自然语言拆解为原子行为执行计划
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Optional

from nlp_decomposer.action import ActionRegistry, get_default_registry
from nlp_decomposer.plan import ActionPlan, ActionStep


# 系统提示模板
SYSTEM_PROMPT = """你是一个自然语言行为拆解器。你的任务是将用户的自然语言指令拆解为若干个原子行为的执行计划。

可用的原子行为列表:
{actions_description}

规则:
1. 每个步骤必须使用上述列表中已有的原子行为
2. 每个步骤需要一个唯一的 step_id（英文标识）
3. 步骤参数值可以是字面量，也可以用 "$results.step_id" 引用前面步骤的结果
4. 如果某步骤需要满足条件才执行，设置 condition 字段（可用 $results.step_id 引用结果做判断）
5. 无条件执行的步骤不设置 condition

请严格按以下 JSON 格式输出，不要输出其他内容:
{{
  "explanation": "对拆解逻辑的简要解释",
  "steps": [
    {{
      "step_id": "步骤标识",
      "action_name": "原子行为名称",
      "params": {{"参数名": "参数值"}},
      "condition": null 或 "条件表达式"
    }}
  ]
}}"""

USER_PROMPT = """请将以下自然语言指令拆解为原子行为执行计划:

{user_text}"""


class NLDecomposer:
    """自然语言拆解器

    使用大模型将自然语言文本拆解为原子行为的执行计划。

    支持两种 LLM 调用方式:
    1. 传入 OpenAI 兼容的 client 对象
    2. 传入自定义的 llm_call 函数: (system_prompt, user_prompt) -> str
    """

    def __init__(
        self,
        registry: Optional[ActionRegistry] = None,
        llm_client: Optional[Any] = None,
        llm_model: str = "gpt-4o-mini",
        llm_call: Optional[Callable[[str, str], str]] = None,
    ):
        """
        Args:
            registry: 原子行为注册表，默认使用全局注册表
            llm_client: OpenAI 兼容的客户端对象（有 chat.completions.create 方法）
            llm_model: 使用的模型名称
            llm_call: 自定义 LLM 调用函数，签名 (system_prompt, user_prompt) -> str
                       若同时提供 llm_client 和 llm_call，优先使用 llm_call
        """
        self.registry = registry or get_default_registry()
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.llm_call = llm_call

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用大模型"""
        if self.llm_call:
            return self.llm_call(system_prompt, user_prompt)

        if self.llm_client:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
            )
            return response.choices[0].message.content

        raise RuntimeError(
            "未配置 LLM：请提供 llm_client（OpenAI 兼容客户端）或 llm_call（自定义函数）"
        )

    def _parse_response(self, response_text: str, original_text: str) -> ActionPlan:
        """解析大模型返回的 JSON 为 ActionPlan"""
        # 尝试从返回文本中提取 JSON
        text = response_text.strip()

        # 如果被 markdown 代码块包裹，去除
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)

        data = json.loads(text)

        plan = ActionPlan(
            original_text=original_text,
            explanation=data.get("explanation", ""),
        )

        for step_data in data.get("steps", []):
            action_name = step_data["action_name"]
            # 校验行为是否存在
            if action_name not in self.registry:
                raise ValueError(
                    f"大模型返回了未知的原子行为: '{action_name}'。"
                    f"已注册: {[a.name for a in self.registry.list_actions()]}"
                )
            plan.steps.append(ActionStep.from_dict(step_data))

        return plan

    def decompose(self, text: str) -> ActionPlan:
        """将自然语言文本拆解为执行计划

        Args:
            text: 自然语言指令

        Returns:
            ActionPlan 执行计划
        """
        actions_desc = self.registry.get_prompt_descriptions()
        system_prompt = SYSTEM_PROMPT.format(actions_description=actions_desc)
        user_prompt = USER_PROMPT.format(user_text=text)

        response = self._call_llm(system_prompt, user_prompt)
        return self._parse_response(response, original_text=text)

    def decompose_with_retry(self, text: str, max_retries: int = 2) -> ActionPlan:
        """带重试的拆解（解析失败时重试）"""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return self.decompose(text)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                last_error = e
                if attempt < max_retries:
                    continue
        raise RuntimeError(
            f"拆解失败（已重试 {max_retries} 次）: {last_error}"
        ) from last_error
