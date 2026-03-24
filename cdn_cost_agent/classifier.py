"""
问题分类器 — 通过 LLM 对用户问题进行分类和参数提取
"""

import json
from prompts import CLASSIFY_PROMPT


def classify(question: str, llm) -> dict:
    """
    调用 LLM 对问题进行分类。

    Returns:
        {"type": "query"|"month_compare"|"customer_compare",
         "customers": [...], "months": [...]}
    """
    messages = [
        {"role": "system", "content": CLASSIFY_PROMPT},
        {"role": "user", "content": question},
    ]

    response = llm.chat(messages)
    result = json.loads(response)

    return {
        "type": result["type"],
        "customers": result["customers"],
        "months": result["months"],
        "raw_question": question,
    }
