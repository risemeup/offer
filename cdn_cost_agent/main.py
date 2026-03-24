"""
CDN 客户成本分析 Agent — 入口
交互式命令行，支持预设问题和自定义输入
"""

from mock_llm import MockLLMClient
from agent import run_agent

BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"

EXAMPLE_QUESTIONS = [
    "客户A 3月的超卖是多少？",
    "客户A 3月超卖为什么比2月差了？",
    "客户A 3月超卖为什么不如客户B？",
]


def main():
    # 初始化 LLM 客户端（Mock 实现，无需 API Key）
    # 替换为真实 LLM 时: llm = RealLLMClient(api_key="sk-...")
    llm = MockLLMClient()

    print(f"""
{BOLD}╔══════════════════════════════════════════════════╗
║       CDN 客户成本分析 Agent (Demo)               ║
║       约束型 ReAct 模式 · LLM 驱动                ║
╚══════════════════════════════════════════════════╝{RESET}

{DIM}LLM 后端: MockLLMClient（模拟实现，无需 API Key）
替换为真实 LLM 只需修改 mock_llm.py 中的 chat() 方法{RESET}

{DIM}预设可演示问题：{RESET}""")

    for i, q in enumerate(EXAMPLE_QUESTIONS, 1):
        print(f"  {BOLD}[{i}]{RESET} {q}")

    print(f"\n{DIM}输入问题编号(1-3)、自定义问题、或 q 退出{RESET}")

    while True:
        try:
            user_input = input(f"\n{BOLD}> {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input or user_input.lower() == "q":
            print("再见！")
            break

        if user_input in ("1", "2", "3"):
            question = EXAMPLE_QUESTIONS[int(user_input) - 1]
            print(f"{DIM}→ {question}{RESET}")
        else:
            question = user_input

        report = run_agent(question, llm)
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(report)
        print(f"{BOLD}{'='*60}{RESET}")


if __name__ == "__main__":
    main()
