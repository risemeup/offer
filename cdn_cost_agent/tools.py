"""
6 个业务查询工具 — 封装对模拟数据库的查询
"""

from mock_db import (
    OVERSELL_SUMMARY, REVENUE_FACTORS, ROOM_BREAKDOWN,
    ROOM_DETAIL, BURST_IMPACT, CUSTOMER_INFO,
)


# ---------- 工具注册表 ----------

TOOL_REGISTRY = {}


def register_tool(name, description, params):
    """装饰器：注册工具的元信息"""
    def decorator(func):
        TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "params": params,
            "func": func,
        }
        return func
    return decorator


# ---------- 6 个业务工具 ----------

@register_tool(
    name="get_oversell",
    description="查询客户超卖汇总数据（超卖率、成本、收入、利润）",
    params=["customer", "months"],
)
def get_oversell(customer: str, months: list[str]) -> dict:
    results = {}
    for m in months:
        key = (customer, m)
        if key in OVERSELL_SUMMARY:
            results[m] = OVERSELL_SUMMARY[key]
        else:
            results[m] = None
    return results


@register_tool(
    name="get_revenue_factors",
    description="查询客户收益因子（波形因子、调度偏差、带宽利用率、峰均比、单价）",
    params=["customer", "months"],
)
def get_revenue_factors(customer: str, months: list[str]) -> dict:
    results = {}
    for m in months:
        key = (customer, m)
        if key in REVENUE_FACTORS:
            results[m] = REVENUE_FACTORS[key]
        else:
            results[m] = None
    return results


@register_tool(
    name="get_room_breakdown",
    description="查询客户在各机房的分摊情况（分摊占比、成本、带宽），按成本降序排列",
    params=["customer", "month", "top_n"],
)
def get_room_breakdown(customer: str, month: str, top_n: int = 5) -> list[dict]:
    key = (customer, month)
    if key in ROOM_BREAKDOWN:
        rooms = sorted(ROOM_BREAKDOWN[key], key=lambda x: x["cost_wan"], reverse=True)
        return rooms[:top_n]
    return []


@register_tool(
    name="get_room_detail",
    description="查询客户在指定机房的详细数据（峰值带宽、单位成本、机房总带宽、其他客户数）",
    params=["customer", "room", "months"],
)
def get_room_detail(customer: str, room: str, months: list[str]) -> dict:
    results = {}
    for m in months:
        key = (customer, room, m)
        if key in ROOM_DETAIL:
            results[m] = ROOM_DETAIL[key]
        else:
            results[m] = None
    return results


@register_tool(
    name="get_burst_impact",
    description="查询客户突发流量影响（突发次数、峰值、额外成本、原因）",
    params=["customer", "month"],
)
def get_burst_impact(customer: str, month: str) -> dict | None:
    key = (customer, month)
    return BURST_IMPACT.get(key)


@register_tool(
    name="verify_calculation",
    description="计算校验工具，验证数值计算是否正确",
    params=["expression"],
)
def verify_calculation(expression: str) -> dict:
    """安全地计算数学表达式并返回结果"""
    try:
        # 只允许基本数学运算
        allowed = set("0123456789.+-*/() ")
        if not all(c in allowed for c in expression):
            return {"expression": expression, "result": None, "error": "不支持的字符"}
        result = eval(expression)  # noqa: S307 — demo only, input is sanitized
        return {"expression": expression, "result": round(result, 4), "error": None}
    except Exception as e:
        return {"expression": expression, "result": None, "error": str(e)}


# ---------- 工具调用入口 ----------

def call_tool(tool_name: str, **kwargs):
    """统一的工具调用入口"""
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"未知工具: {tool_name}"}
    func = TOOL_REGISTRY[tool_name]["func"]
    return func(**kwargs)
