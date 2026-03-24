"""
Agent 核心循环 — 约束型 ReAct 模式
所有推理决策均通过 LLM 完成：分类、思考、动作规划、条件评估、报告生成
"""

import json
from classifier import classify
from prompts import DECISION_TREES, STEP_PROMPT, ANALYZE_PROMPT, CONDITION_PROMPT, REPORT_PROMPT
from tools import call_tool, TOOL_REGISTRY


# ANSI 颜色
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def run_agent(question: str, llm) -> str:
    """运行 Agent 主循环，返回最终分析报告"""

    # ===== Step 0: LLM 分类 =====
    classification = classify(question, llm)
    qtype = classification["type"]
    customers = classification["customers"]
    months = classification["months"]

    tree = DECISION_TREES.get(qtype)
    if not tree:
        return "无法识别的问题类型。"

    _print_header(tree["name"], customers, months)

    # 全局上下文：累积所有观察和分析结果
    context = {
        "question_type": qtype,
        "customers": customers,
        "months": months,
        "observations": {},     # 工具返回的原始数据
        "analyses": [],         # LLM 的分析结论
    }

    step_num = 0

    # ===== 执行必查步骤 =====
    for step in tree["required_steps"]:
        step_num += 1
        _execute_step(step, step_num, llm, context)

    # ===== LLM 评估条件步骤 =====
    for step in tree["conditional_steps"]:
        should, reason = _evaluate_condition(step, llm, context)
        if should:
            step_num += 1
            print(f"  {DIM}条件满足: {reason}{RESET}")
            _execute_step(step, step_num, llm, context)
        else:
            print(f"  {DIM}跳过条件步骤「{step['description']}」: {reason}{RESET}")

    # ===== LLM 生成报告 =====
    print(f"\n{BOLD}{MAGENTA}📊 LLM 生成分析报告...{RESET}\n")
    report = _generate_report(llm, context)
    return report


def _execute_step(step: dict, step_num: int, llm, context: dict):
    """执行一个决策树步骤：LLM Thought → LLM Action → Tool Observation → LLM Analysis"""

    tool_name = step["tool"]
    tool_info = TOOL_REGISTRY.get(tool_name, {})

    print(f"\n{BOLD}--- Step {step_num}: {step['description']} ---{RESET}")

    # ===== 1. LLM 生成 Thought + Action 规划 =====
    step_prompt = STEP_PROMPT.format(
        step_description=step["description"],
        tool_name=tool_name,
        tool_params=", ".join(tool_info.get("params", [])),
    )
    step_context = json.dumps({
        "tool_name": tool_name,
        "question_type": context["question_type"],
        "customers": context["customers"],
        "months": context["months"],
        "observations": context["observations"],
    }, ensure_ascii=False)

    plan_response = llm.chat([
        {"role": "system", "content": step_prompt},
        {"role": "user", "content": step_context},
    ])
    plan = json.loads(plan_response)

    thought = plan["thought"]
    tool_calls = plan["tool_calls"]

    _print_thought(thought)

    # ===== 2. 执行工具调用 =====
    call_results = []
    for tc in tool_calls:
        _print_action(tc["tool"], tc["params"])
        result = call_tool(tc["tool"], **tc["params"])
        call_results.append({"params": tc["params"], "result": result})
        _print_observation(result)

    # ===== 3. LLM 分析观察结果 =====
    analyze_context = json.dumps({
        "tool_name": tool_name,
        "question_type": context["question_type"],
        "customers": context["customers"],
        "months": context["months"],
        "results": call_results,
        "observations": context["observations"],
    }, ensure_ascii=False, default=str)

    analysis_response = llm.chat([
        {"role": "system", "content": ANALYZE_PROMPT.format(
            step_description=step["description"],
            tool_name=tool_name,
        )},
        {"role": "user", "content": analyze_context},
    ])

    # 解析分析结果（可能是纯文本或含结构化标记的 JSON）
    analysis_text, structured = _parse_analysis(analysis_response)
    _print_analysis(analysis_text)

    # ===== 4. 更新上下文 =====
    context["analyses"].append({
        "step": step["description"],
        "tool": tool_name,
        "analysis": analysis_text,
    })

    # 存储原始观察数据
    _store_observations(tool_name, call_results, context)

    # 存储结构化标记（如异常机房列表、峰值异常标记）
    for k, v in structured.items():
        if k.startswith("_"):
            context["observations"][k] = v


def _evaluate_condition(step: dict, llm, context: dict) -> tuple[bool, str]:
    """调用 LLM 评估条件步骤是否需要执行"""
    cond_context = json.dumps({
        "condition": step.get("condition", ""),
        "step_description": step["description"],
        "observations": context["observations"],
        "analyses": context["analyses"],
    }, ensure_ascii=False, default=str)

    response = llm.chat([
        {"role": "system", "content": CONDITION_PROMPT.format(
            step_description=step["description"],
            condition=step.get("condition", ""),
        )},
        {"role": "user", "content": cond_context},
    ])

    result = json.loads(response)
    return result["execute"], result["reason"]


def _generate_report(llm, context: dict) -> str:
    """调用 LLM 生成最终分析报告"""
    report_context = json.dumps({
        "question_type": context["question_type"],
        "customers": context["customers"],
        "months": context["months"],
        "observations": context["observations"],
        "analyses": context["analyses"],
    }, ensure_ascii=False, default=str)

    return llm.chat([
        {"role": "system", "content": REPORT_PROMPT},
        {"role": "user", "content": report_context},
    ])


# ---------- 上下文数据存储 ----------

def _store_observations(tool_name: str, call_results: list, context: dict):
    """将工具返回的数据按结构化方式存入上下文"""
    obs = context["observations"]

    if tool_name in ("get_oversell", "get_revenue_factors"):
        if tool_name not in obs:
            obs[tool_name] = {}
        for cr in call_results:
            customer = cr["params"]["customer"]
            if customer not in obs[tool_name]:
                obs[tool_name][customer] = {}
            if isinstance(cr["result"], dict):
                obs[tool_name][customer].update(cr["result"])

    elif tool_name == "get_room_breakdown":
        if tool_name not in obs:
            obs[tool_name] = {}
        for cr in call_results:
            key = f"{cr['params']['customer']}_{cr['params']['month']}"
            obs[tool_name][key] = cr["result"]

    elif tool_name == "get_room_detail":
        if tool_name not in obs:
            obs[tool_name] = {}
        for cr in call_results:
            room = cr["params"]["room"]
            obs[tool_name][room] = cr["result"]

    elif tool_name == "get_burst_impact":
        for cr in call_results:
            obs[tool_name] = cr["result"]

    elif tool_name == "verify_calculation":
        for cr in call_results:
            obs[tool_name] = cr["result"]


def _parse_analysis(response: str) -> tuple[str, dict]:
    """解析 LLM 的分析响应，分离文本和结构化标记"""
    try:
        data = json.loads(response)
        text = data.pop("analysis", response)
        return text, data
    except (json.JSONDecodeError, AttributeError):
        return response, {}


# ---------- 输出格式化 ----------

def _print_header(tree_name, customers, months):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}问题分类: {tree_name}{RESET}")
    print(f"客户: {', '.join(customers)} | 月份: {', '.join(months)}")
    print(f"{BOLD}{'='*60}{RESET}")


def _print_thought(thought: str):
    print(f"  {CYAN}💭 Thought: {thought}{RESET}")


def _print_action(tool_name: str, params: dict):
    params_str = ", ".join(f"{k}={v}" for k, v in params.items())
    print(f"  {GREEN}🔧 Action: {tool_name}({params_str}){RESET}")


def _print_observation(result):
    if isinstance(result, dict):
        compact = _compact(result)
        print(f"  {YELLOW}👁 Observation: {compact}{RESET}")
    elif isinstance(result, list):
        print(f"  {YELLOW}👁 Observation: [{len(result)} records]{RESET}")
        for r in result[:3]:
            print(f"  {YELLOW}    {_compact(r)}{RESET}")
        if len(result) > 3:
            print(f"  {YELLOW}    ...({len(result)-3} more){RESET}")
    else:
        print(f"  {YELLOW}👁 Observation: {result}{RESET}")


def _print_analysis(analysis: str):
    print(f"  {MAGENTA}📝 Analysis: {analysis}{RESET}\n")


def _compact(d) -> str:
    if not isinstance(d, dict):
        return str(d)
    parts = []
    for k, v in d.items():
        if isinstance(v, dict):
            parts.append(f"{k}={{...}}")
        elif isinstance(v, list):
            parts.append(f"{k}=[{len(v)}]")
        elif isinstance(v, float):
            parts.append(f"{k}={v:.4g}")
        elif v is None:
            continue
        else:
            parts.append(f"{k}={v}")
    return "{" + ", ".join(parts) + "}"
