# -*- coding: utf-8 -*-
"""语义归一化层 —— 把非正式格式描述转成可确认的中间结构。

输入：一段口语化/非正规的格式要求文字，或一张要求截图
输出：{
  "format_spec": {...},          # 已能确定的格式规则（不完整，缺的角色由确认表单补）
  "content_requirements": [...], # 内容要求清单
  "ambiguities": [...]           # 模糊项 + 建议值，供用户确认
}
"""

import os
import re

AMBIGUITY_PROMPT = """你是一个文档格式规范解析器。用户给的是一份非正式、口语化的格式要求（可能是聊天记录、随手记、口头转述）。

请把里面的要求拆解成三部分，只输出 JSON：

1. "format_spec"：已能确定的格式规范，按角色组织。每个角色可包含：
   font_eastasia（中文字体）、size_pt（字号磅值）、alignment（left/center/right/justify）、
   bold、line_spacing、first_line_indent_chars 等。
   角色枚举：title / subtitle / heading_1 / heading_2 / heading_3 / body /
   signature / date / abstract_heading / abstract_body / keywords / chapter_heading /
   bibliography_heading / bibliography_entry / figure_caption / table_caption。
   **只填原文明确提到的字段，不要编造。**

2. "content_requirements"：内容要求清单。每条是一个对象：
   {"item": "封面", "requirement": "必须包含题目、姓名、学号、指导老师", "fields": ["题目","姓名","学号","指导老师"]}

3. "ambiguities"：所有模糊、无法直接确定的描述，逐条列出：
   {"original": "原文描述", "issue": "为什么模糊", "suggestion": "建议值"}
   模糊描述不要编造精确值，放到这里。

只输出 JSON，不要任何解释。"""


def _clean_json(result):
    """去掉 DeepSeek 偶尔多回的 response_format 回显字段。"""
    if isinstance(result, dict):
        result.pop("type", None)
    return result


def extract_semantic(spec_text=None, image_paths=None, llm=None):
    """从文字或图片提取语义结构。

    spec_text: 非正式格式描述文字（可选）
    image_paths: 图片路径列表（可选）
    至少提供其一。返回清洗后的 dict。
    """
    if llm is None:
        from core.llm import LLMClient
        llm = LLMClient()

    prompt = AMBIGUITY_PROMPT
    if spec_text:
        prompt += "\n\n用户的格式要求文字如下：\n" + spec_text

    if image_paths:
        result = llm.chat_vision_json(prompt, image_paths)
    else:
        result = llm.chat_json(prompt)

    result = _clean_json(result)

    # 兜底：确保三个键都存在
    result.setdefault("format_spec", {})
    result.setdefault("content_requirements", [])
    result.setdefault("ambiguities", [])
    return result


# 常见角色中文名，供表单展示
ROLE_LABELS = {
    "title": "标题",
    "subtitle": "副标题",
    "heading_1": "一级标题",
    "heading_2": "二级标题",
    "heading_3": "三级标题",
    "body": "正文",
    "signature": "落款",
    "date": "日期",
    "abstract_heading": "摘要标题",
    "abstract_body": "摘要正文",
    "keywords": "关键词",
    "chapter_heading": "章节标题",
    "bibliography_heading": "参考文献标题",
    "bibliography_entry": "参考文献条目",
    "figure_caption": "图题",
    "table_caption": "表题",
}

# 常见字号（磅值 → 中文名），供表单下拉
SIZE_PT_OPTIONS = {
    "初号": 42, "小初": 36, "一号": 26, "小一": 24,
    "二号": 22, "小二": 18, "三号": 16, "小三": 15,
    "四号": 14, "小四": 12, "五号": 10.5, "小五": 9,
}

ALIGNMENT_LABELS = {
    "left": "左对齐", "center": "居中", "right": "右对齐", "justify": "两端对齐",
}

FONT_OPTIONS = [
    "宋体", "黑体", "仿宋", "楷体", "微软雅黑",
    "方正小标宋简体", "仿宋_GB2312", "楷体_GB2312", "Times New Roman", "Arial",
]


def pt_to_label(pt):
    """磅值 → 最接近的中文字号名。"""
    if pt is None:
        return ""
    try:
        pt = float(pt)
    except (TypeError, ValueError):
        return str(pt)
    best = min(SIZE_PT_OPTIONS.items(), key=lambda kv: abs(kv[1] - pt))
    return f"{best[0]}（{best[1]}pt）"


def label_to_pt(label):
    """中文字号名 → 磅值；失败返回 None。"""
    if not label:
        return None
    match = re.search(r"（([\d.]+)pt）", str(label))
    if match:
        return float(match.group(1))
    return SIZE_PT_OPTIONS.get(str(label).strip())
