"""
NLP Decomposer Web 服务

Flask 后端，提供：
- 查看已注册的原子行为列表
- 手动构建执行计划并执行
- 使用 LLM 自动拆解自然语言（需配置 LLM）

启动: python -m nlp_decomposer.web.app
"""

from __future__ import annotations

import json
import os
from typing import Optional

from flask import Flask, jsonify, render_template, request

from nlp_decomposer.action import ActionRegistry, get_default_registry
from nlp_decomposer.decomposer import NLDecomposer
from nlp_decomposer.executor import PlanExecutor
from nlp_decomposer.plan import ActionPlan, ActionStep

# 导入内置原子行为
import nlp_decomposer.actions  # noqa: F401

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

registry = get_default_registry()
executor = PlanExecutor(registry=registry)

# LLM 配置 —— 可选，通过环境变量或启动参数设置
_llm_call = None


def configure_llm(llm_call_fn):
    """配置 LLM 调用函数"""
    global _llm_call
    _llm_call = llm_call_fn


# ---------- API 路由 ----------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/actions", methods=["GET"])
def list_actions():
    """获取所有已注册的原子行为"""
    actions = []
    for act in registry.list_actions():
        actions.append({
            "name": act.name,
            "description": act.description,
            "action_type": act.action_type,
            "parameters": act.parameters,
        })
    return jsonify({"actions": actions})


@app.route("/api/execute", methods=["POST"])
def execute_plan():
    """执行一个手动构建的执行计划

    请求体:
    {
        "steps": [
            {
                "step_id": "s1",
                "action_name": "add",
                "params": {"a": 3, "b": 5},
                "condition": null
            }
        ]
    }
    """
    data = request.get_json()
    if not data or "steps" not in data:
        return jsonify({"error": "请求体需要包含 steps 字段"}), 400

    plan = ActionPlan(original_text=data.get("original_text", ""))
    for step_data in data["steps"]:
        if "step_id" not in step_data or "action_name" not in step_data:
            return jsonify({"error": "每个步骤需要 step_id 和 action_name"}), 400
        plan.steps.append(ActionStep.from_dict(step_data))

    # 如果有 LLM 行为，注入 llm_call
    if _llm_call:
        # 在执行前把 _llm_call 注入到初始 context
        exec_result = _execute_with_llm(plan)
    else:
        exec_result = executor.execute(plan)

    return jsonify({
        "results": {k: _serialize(v) for k, v in exec_result.results.items()},
        "skipped": exec_result.skipped,
        "errors": exec_result.errors,
        "execution_order": exec_result.execution_order,
    })


@app.route("/api/decompose", methods=["POST"])
def decompose():
    """使用 LLM 自动拆解自然语言

    请求体: {"text": "自然语言指令"}
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "请求体需要包含 text 字段"}), 400

    if _llm_call is None:
        return jsonify({"error": "未配置 LLM，无法进行自动拆解。请设置环境变量或在代码中配置。"}), 503

    decomposer = NLDecomposer(registry=registry, llm_call=_llm_call)
    try:
        plan = decomposer.decompose_with_retry(data["text"])
    except Exception as e:
        return jsonify({"error": f"拆解失败: {str(e)}"}), 500

    return jsonify({"plan": plan.to_dict()})


@app.route("/api/decompose_and_execute", methods=["POST"])
def decompose_and_execute():
    """自动拆解并执行

    请求体: {"text": "自然语言指令"}
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "请求体需要包含 text 字段"}), 400

    if _llm_call is None:
        return jsonify({"error": "未配置 LLM，无法进行自动拆解。"}), 503

    decomposer = NLDecomposer(registry=registry, llm_call=_llm_call)
    try:
        plan = decomposer.decompose_with_retry(data["text"])
    except Exception as e:
        return jsonify({"error": f"拆解失败: {str(e)}"}), 500

    if _llm_call:
        exec_result = _execute_with_llm(plan)
    else:
        exec_result = executor.execute(plan)

    return jsonify({
        "plan": plan.to_dict(),
        "results": {k: _serialize(v) for k, v in exec_result.results.items()},
        "skipped": exec_result.skipped,
        "errors": exec_result.errors,
        "execution_order": exec_result.execution_order,
    })


# ---------- 辅助函数 ----------


def _execute_with_llm(plan: ActionPlan):
    """执行计划时注入 LLM 调用能力"""
    result = executor.execute.__func__
    # 创建一个临时执行器，在执行过程中注入 _llm_call
    exec_result = executor.execute(plan)
    # 检查是否有 LLM 行为因缺少 _llm_call 而失败，重新执行
    if exec_result.errors and _llm_call:
        # 为包含 LLM 行为的计划重新构建执行
        from nlp_decomposer.executor import ExecutionResult
        new_result = ExecutionResult()
        for step in plan.steps:
            new_result.execution_order.append(step.step_id)
            if step.condition:
                try:
                    should_run = executor._evaluate_condition(
                        step.condition, new_result.results
                    )
                except Exception as e:
                    new_result.errors[step.step_id] = f"条件评估失败: {e}"
                    continue
                if not should_run:
                    new_result.skipped.append(step.step_id)
                    continue
            try:
                action = registry.get(step.action_name)
            except KeyError as e:
                new_result.errors[step.step_id] = str(e)
                continue
            try:
                resolved_params = executor._resolve_params(
                    step.params, new_result.results
                )
            except KeyError as e:
                new_result.errors[step.step_id] = f"参数解析失败: {e}"
                continue
            try:
                context = dict(new_result.results)
                context["_llm_call"] = _llm_call
                result_val = action.execute(context=context, **resolved_params)
                new_result.results[step.step_id] = result_val
            except Exception as e:
                new_result.errors[step.step_id] = f"执行失败: {e}"
        return new_result
    return exec_result


def _serialize(value):
    """将执行结果序列化为 JSON 兼容格式"""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    return str(value)


def _try_configure_openai():
    """尝试通过环境变量配置 OpenAI 兼容的 LLM"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return

    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    try:
        from openai import OpenAI
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)

        def llm_call(system_prompt, user_prompt):
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
            )
            return resp.choices[0].message.content

        configure_llm(llm_call)
        print(f"[NLP Decomposer] 已通过 OpenAI API 配置 LLM (model={model})")
    except ImportError:
        print("[NLP Decomposer] 检测到 OPENAI_API_KEY 但未安装 openai 库，LLM 功能不可用")


if __name__ == "__main__":
    _try_configure_openai()
    print("[NLP Decomposer] Web 服务启动于 http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
