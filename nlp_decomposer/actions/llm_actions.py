"""
大模型相关的原子行为（LLM 类型）

这些行为需要在执行时通过 context["_llm_call"] 提供 LLM 调用能力。
用户也可以自行注册更多 LLM 类型的行为。
"""

from nlp_decomposer.action import action


def _get_llm_call(context):
    """从上下文中获取 LLM 调用函数"""
    llm_call = context.get("_llm_call")
    if llm_call is None:
        raise RuntimeError(
            "LLM 类型行为需要在 context 中提供 '_llm_call' 函数。"
            "请在 PlanExecutor 执行前设置: executor.execute(plan, llm_call=fn)"
        )
    return llm_call


@action(
    name="llm_generate",
    description="使用大模型根据提示词生成文本",
    action_type="llm",
    parameters={"prompt": "提示词"},
)
def llm_generate(context, prompt=""):
    llm_call = _get_llm_call(context)
    return llm_call("你是一个有帮助的助手。", prompt)


@action(
    name="llm_translate",
    description="使用大模型翻译文本",
    action_type="llm",
    parameters={"text": "要翻译的文本", "target_lang": "目标语言（如中文、英文、日文）"},
)
def llm_translate(context, text="", target_lang="中文"):
    llm_call = _get_llm_call(context)
    return llm_call(
        "你是一个专业翻译。",
        f"请将以下内容翻译为{target_lang}，只输出翻译结果:\n{text}",
    )


@action(
    name="llm_summarize",
    description="使用大模型对文本进行摘要",
    action_type="llm",
    parameters={"text": "要摘要的文本", "max_length": "摘要最大长度（字数）"},
)
def llm_summarize(context, text="", max_length=100):
    llm_call = _get_llm_call(context)
    return llm_call(
        "你是一个擅长总结的助手。",
        f"请用不超过{max_length}字对以下内容进行摘要:\n{text}",
    )


@action(
    name="llm_classify",
    description="使用大模型对文本进行分类",
    action_type="llm",
    parameters={"text": "要分类的文本", "categories": "类别列表（逗号分隔）"},
)
def llm_classify(context, text="", categories=""):
    llm_call = _get_llm_call(context)
    return llm_call(
        "你是一个文本分类器。只输出类别名称，不要输出其他内容。",
        f"请将以下文本分类到这些类别之一: {categories}\n\n文本: {text}",
    )


@action(
    name="llm_extract",
    description="使用大模型从文本中提取指定信息",
    action_type="llm",
    parameters={"text": "输入文本", "what": "要提取的信息描述"},
)
def llm_extract(context, text="", what="关键信息"):
    llm_call = _get_llm_call(context)
    return llm_call(
        "你是一个信息提取助手。只输出提取的内容，不要输出其他说明。",
        f"请从以下文本中提取{what}:\n{text}",
    )


@action(
    name="llm_rewrite",
    description="使用大模型改写文本（换一种风格或表达方式）",
    action_type="llm",
    parameters={"text": "输入文本", "style": "目标风格（如正式、口语、文言文）"},
)
def llm_rewrite(context, text="", style="正式"):
    llm_call = _get_llm_call(context)
    return llm_call(
        "你是一个文本改写助手。只输出改写后的文本。",
        f"请将以下文本改写为{style}风格:\n{text}",
    )
