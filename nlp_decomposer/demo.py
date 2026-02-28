"""
NLP Decomposer 完整演示

展示两种使用方式:
1. 手动构建执行计划（不依赖 LLM）
2. 使用 LLM 自动拆解自然语言（需要配置 LLM）

运行: python -m nlp_decomposer.demo
"""

from nlp_decomposer.action import ActionRegistry, AtomicAction, get_default_registry
from nlp_decomposer.plan import ActionPlan
from nlp_decomposer.executor import PlanExecutor
from nlp_decomposer.decomposer import NLDecomposer

# 导入内置原子行为（自动注册到默认注册表）
import nlp_decomposer.actions  # noqa: F401


def demo_manual_plan():
    """演示 1: 手动构建执行计划"""
    print("=" * 60)
    print("演示 1: 手动构建执行计划（纯代码行为）")
    print("=" * 60)

    registry = get_default_registry()
    print(f"\n已注册 {len(registry)} 个原子行为:")
    print(registry.get_prompt_descriptions())

    # 构建一个计划: "计算 3+5 的结果，如果大于 6 则转为大写字符串"
    plan = ActionPlan(original_text="计算 3+5 的结果，如果大于 6 则转为大写字符串")

    # 步骤1: 计算 3+5
    plan.add_step(step_id="sum", action_name="add", params={"a": 3, "b": 5})

    # 步骤2: 比较结果与 6
    plan.add_step(
        step_id="cmp",
        action_name="compare",
        params={"a": "$results.sum", "b": 6},
    )

    # 步骤3: 条件执行 - 仅当比较结果为 greater 时执行
    plan.add_step(
        step_id="to_upper",
        action_name="to_uppercase",
        params={"text": "result is big"},
        condition="$results.cmp == 'greater'",
    )

    print(f"\n{plan}")

    # 执行计划
    executor = PlanExecutor()
    result = executor.execute(plan)
    print(f"\n{result.summary()}")


def demo_conditional_skip():
    """演示 2: 条件不满足时跳过步骤"""
    print("\n" + "=" * 60)
    print("演示 2: 条件不满足时跳过步骤")
    print("=" * 60)

    plan = ActionPlan(original_text="计算 2+1，如果结果大于 10 才拼接文本")

    plan.add_step(step_id="sum", action_name="add", params={"a": 2, "b": 1})
    plan.add_step(
        step_id="concat",
        action_name="concat_text",
        params={"parts": ["结果是: ", "$results.sum"], "separator": ""},
        condition="$results.sum > 10",
    )

    print(f"\n{plan}")

    executor = PlanExecutor()
    result = executor.execute(plan)
    print(f"\n{result.summary()}")
    print(f"跳过的步骤: {result.skipped}")


def demo_chained_text():
    """演示 3: 链式文本处理"""
    print("\n" + "=" * 60)
    print("演示 3: 链式文本处理（结果引用）")
    print("=" * 60)

    plan = ActionPlan(original_text="把 Hello World 转大写，再统计字符数")

    plan.add_step(
        step_id="upper",
        action_name="to_uppercase",
        params={"text": "Hello World"},
    )
    plan.add_step(
        step_id="count",
        action_name="count_chars",
        params={"text": "$results.upper"},
    )
    plan.add_step(
        step_id="report",
        action_name="concat_text",
        params={
            "parts": ["转换结果: ", "$results.upper", "，共 ", "$results.count", " 个字符"],
            "separator": "",
        },
    )

    print(f"\n{plan}")

    executor = PlanExecutor()
    result = executor.execute(plan)
    print(f"\n{result.summary()}")


def demo_custom_action():
    """演示 4: 注册自定义原子行为"""
    print("\n" + "=" * 60)
    print("演示 4: 注册自定义原子行为")
    print("=" * 60)

    # 创建独立的注册表
    my_registry = ActionRegistry()

    # 方式1: 直接创建 AtomicAction
    my_registry.register(AtomicAction(
        name="greet",
        description="生成问候语",
        parameters={"name": "人名"},
        fn=lambda context, name="": f"你好，{name}！欢迎使用 NLP Decomposer。",
    ))

    # 方式2: 使用装饰器（指定注册表）
    from nlp_decomposer.action import action as register_action

    @register_action(
        name="reverse_text",
        description="反转文本",
        parameters={"text": "输入文本"},
        registry=my_registry,
    )
    def reverse_text(context, text=""):
        return text[::-1]

    # 构建并执行计划
    plan = ActionPlan(original_text="先问候张三，再把问候语反转")
    plan.add_step(step_id="hello", action_name="greet", params={"name": "张三"})
    plan.add_step(
        step_id="reversed",
        action_name="reverse_text",
        params={"text": "$results.hello"},
    )

    print(f"\n{plan}")

    executor = PlanExecutor(registry=my_registry)
    result = executor.execute(plan)
    print(f"\n{result.summary()}")


def demo_llm_decompose():
    """演示 5: 使用 LLM 自动拆解自然语言（模拟）"""
    print("\n" + "=" * 60)
    print("演示 5: 使用 LLM 自动拆解自然语言（模拟）")
    print("=" * 60)

    # 模拟 LLM 的返回（实际使用时替换为真正的 LLM 调用）
    import json

    mock_responses = {
        "default": json.dumps(
            {
                "explanation": "用户想先统计文本字符数，然后判断是否超过5个字符，如果是则转为大写",
                "steps": [
                    {
                        "step_id": "count",
                        "action_name": "count_chars",
                        "params": {"text": "你好世界"},
                    },
                    {
                        "step_id": "upper",
                        "action_name": "to_uppercase",
                        "params": {"text": "你好世界"},
                        "condition": "$results.count > 5",
                    },
                    {
                        "step_id": "report",
                        "action_name": "concat_text",
                        "params": {
                            "parts": ["字符数: ", "$results.count"],
                            "separator": "",
                        },
                    },
                ],
            },
            ensure_ascii=False,
        )
    }

    def mock_llm_call(system_prompt, user_prompt):
        """模拟 LLM 调用"""
        print(f"  [模拟 LLM 调用]")
        print(f"  系统提示: {system_prompt[:80]}...")
        print(f"  用户输入: {user_prompt[:80]}...")
        return mock_responses["default"]

    registry = get_default_registry()
    decomposer = NLDecomposer(registry=registry, llm_call=mock_llm_call)

    text = "统计'你好世界'的字符数，如果超过5个字符就转为大写，最后输出字符数报告"
    print(f"\n输入: {text}")

    plan = decomposer.decompose(text)
    print(f"\n拆解结果:\n{plan}")

    executor = PlanExecutor()
    result = executor.execute(plan)
    print(f"\n{result.summary()}")


def demo_llm_actions():
    """演示 6: 展示 LLM 类型行为的计划（需要真实 LLM 才能执行）"""
    print("\n" + "=" * 60)
    print("演示 6: LLM 类型行为的执行计划构建")
    print("=" * 60)

    plan = ActionPlan(
        original_text="将一段英文翻译为中文，然后用文言文风格改写"
    )
    plan.add_step(
        step_id="translate",
        action_name="llm_translate",
        params={"text": "The quick brown fox jumps over the lazy dog", "target_lang": "中文"},
    )
    plan.add_step(
        step_id="rewrite",
        action_name="llm_rewrite",
        params={"text": "$results.translate", "style": "文言文"},
    )

    print(f"\n{plan}")
    print("\n(此计划需要配置真实的 LLM 客户端才能执行)")
    print("配置方式: 在 context 中设置 _llm_call 函数")
    print("  executor = PlanExecutor()")
    print("  # 执行前在 plan 的 context 注入 llm_call")


if __name__ == "__main__":
    demo_manual_plan()
    demo_conditional_skip()
    demo_chained_text()
    demo_custom_action()
    demo_llm_decompose()
    demo_llm_actions()

    print("\n" + "=" * 60)
    print("所有演示完成！")
    print("=" * 60)
