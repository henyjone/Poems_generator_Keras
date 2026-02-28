"""
文本处理相关的原子行为（代码类型）
"""

from nlp_decomposer.action import action


@action(
    name="count_chars",
    description="统计文本的字符数",
    parameters={"text": "输入文本"},
)
def count_chars(context, text=""):
    return len(text)


@action(
    name="count_words",
    description="统计文本的词数（按空格分词）",
    parameters={"text": "输入文本"},
)
def count_words(context, text=""):
    return len(text.split())


@action(
    name="replace_text",
    description="替换文本中的指定内容",
    parameters={"text": "输入文本", "old": "要替换的内容", "new": "替换为的内容"},
)
def replace_text(context, text="", old="", new=""):
    return text.replace(old, new)


@action(
    name="concat_text",
    description="拼接多段文本",
    parameters={"parts": "文本列表", "separator": "分隔符（默认空字符串）"},
)
def concat_text(context, parts=None, separator=""):
    if parts is None:
        parts = []
    return separator.join(str(p) for p in parts)


@action(
    name="split_text",
    description="按分隔符拆分文本为列表",
    parameters={"text": "输入文本", "separator": "分隔符"},
)
def split_text(context, text="", separator="\n"):
    return text.split(separator)


@action(
    name="extract_substring",
    description="提取文本的子串",
    parameters={"text": "输入文本", "start": "起始位置", "end": "结束位置"},
)
def extract_substring(context, text="", start=0, end=None):
    return text[start:end]


@action(
    name="to_uppercase",
    description="将文本转换为大写",
    parameters={"text": "输入文本"},
)
def to_uppercase(context, text=""):
    return text.upper()


@action(
    name="to_lowercase",
    description="将文本转换为小写",
    parameters={"text": "输入文本"},
)
def to_lowercase(context, text=""):
    return text.lower()


@action(
    name="format_template",
    description="使用模板格式化文本，模板中用 {key} 表示占位符",
    parameters={"template": "模板字符串", "values": "键值对字典"},
)
def format_template(context, template="", values=None):
    if values is None:
        values = {}
    return template.format(**values)


@action(
    name="contains_text",
    description="检查文本是否包含指定内容，返回布尔值",
    parameters={"text": "输入文本", "keyword": "要查找的关键字"},
)
def contains_text(context, text="", keyword=""):
    return keyword in text
