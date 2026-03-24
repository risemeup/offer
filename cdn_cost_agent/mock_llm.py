"""
Mock LLM 客户端 — 模拟大模型的推理能力，无需 API Key

接口与真实 LLM SDK 对齐。替换为真实实现时，只需修改 chat() 方法：

    import anthropic

    class RealLLMClient:
        def __init__(self, api_key: str):
            self.client = anthropic.Anthropic(api_key=api_key)

        def chat(self, messages: list[dict]) -> str:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[m for m in messages if m["role"] != "system"],
                system=next((m["content"] for m in messages if m["role"] == "system"), ""),
            )
            return response.content[0].text
"""

import json
import re


class MockLLMClient:
    """
    模拟 LLM 客户端。
    chat() 方法接收标准 messages 列表，返回文本响应。
    内部通过 system prompt 中的 [task:xxx] 标记路由到对应的模拟逻辑。
    """

    def chat(self, messages: list[dict]) -> str:
        """
        Chat Completion API（Mock 实现）

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": str}, ...]
        Returns:
            模拟的 LLM 文本响应
        """
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        user = "\n".join(m["content"] for m in messages if m["role"] == "user")

        # 根据 system prompt 中的任务标记路由
        if "[task:classify]" in system:
            return self._handle_classify(user)
        elif "[task:step]" in system:
            return self._handle_step(system, user)
        elif "[task:analyze]" in system:
            return self._handle_analyze(system, user)
        elif "[task:condition]" in system:
            return self._handle_condition(system, user)
        elif "[task:report]" in system:
            return self._handle_report(user)
        else:
            return "我是 CDN 客户成本分析 Agent，请输入您的分析问题。"

    # ==================== 问题分类 ====================

    def _handle_classify(self, user_msg: str) -> str:
        """模拟 LLM 对问题进行分类和参数提取"""
        customers = re.findall(r'客户[A-Z]', user_msg)
        month_nums = re.findall(r'(\d{1,2})月', user_msg)
        months = list(dict.fromkeys(f"{m}月" for m in month_nums))

        compare_keywords = ["为什么", "对比", "比较", "差了", "变差", "不如", "更好", "更差", "变化", "下降", "升高"]
        is_compare = any(kw in user_msg for kw in compare_keywords)

        if is_compare and len(customers) >= 2:
            qtype = "customer_compare"
        elif is_compare and len(months) >= 2:
            qtype = "month_compare"
        elif is_compare and len(months) == 1 and len(customers) >= 1:
            qtype = "month_compare"
            month_num = int(re.search(r'(\d+)', months[0]).group(1))
            if month_num > 1:
                months = [f"{month_num - 1}月", months[0]]
        else:
            qtype = "query"

        if not customers:
            customers = ["客户A"]
        if not months:
            months = ["3月"]

        return json.dumps({
            "type": qtype,
            "customers": customers,
            "months": months,
        }, ensure_ascii=False)

    # ==================== 步骤规划（Thought + Action） ====================

    def _handle_step(self, system: str, user_msg: str) -> str:
        """模拟 LLM 为当前步骤生成 Thought 和 Action"""
        ctx = json.loads(user_msg)
        tool_name = ctx["tool_name"]
        customers = ctx["customers"]
        months = ctx["months"]
        qtype = ctx["question_type"]
        observations = ctx.get("observations", {})

        thought = self._generate_pre_thought(tool_name, qtype, customers, months, observations)
        tool_calls = self._generate_tool_calls(tool_name, qtype, customers, months, observations)

        return json.dumps({
            "thought": thought,
            "tool_calls": tool_calls,
        }, ensure_ascii=False)

    def _generate_pre_thought(self, tool, qtype, customers, months, observations):
        """生成执行前的思考"""
        c = customers[0]
        if tool == "get_oversell":
            if qtype == "query":
                return f"首先需要查询{c}{'、'.join(months)}的超卖汇总数据，了解整体盈亏状况。"
            elif qtype == "month_compare":
                return f"需要对比{c}在{'和'.join(months)}的超卖率变化，确认是否存在明显波动。"
            else:
                return f"需要分别查询{'和'.join(customers)}的超卖数据，对比超卖率差异。"

        elif tool == "get_revenue_factors":
            if qtype == "customer_compare":
                return f"超卖率已获取，现在需要查看{'和'.join(customers)}的收益因子，定位哪个因子导致了差异。"
            return f"超卖率已确认变化，现在需要拆解收益因子（波形因子、调度偏差、峰均比等），定位变化最大的因子。"

        elif tool == "get_room_breakdown":
            if qtype == "customer_compare":
                return f"因子差异已明确，进一步查看{'和'.join(customers)}的机房成本分布，分析结构性差异。"
            return "因子层面已定位问题，现在需要从机房维度检查成本分摊是否有异常变化。"

        elif tool == "get_room_detail":
            anomaly_rooms = observations.get("_anomaly_rooms", ["北京"])
            return f"{'、'.join(anomaly_rooms)}机房分摊占比变化异常，需要查看明细数据，判断是客户自身流量增加（主动）还是其他客户迁走导致（被动）。"

        elif tool == "get_burst_impact":
            latest = sorted(months, key=lambda x: int(x.replace("月", "")))[-1]
            return f"峰均比升高明显，可能存在突发流量，需要查看{c}{latest}的突发影响数据。"

        elif tool == "verify_calculation":
            return "为确保分析结论的准确性，需要用计算工具校验超卖率等关键指标。"

        return "继续分析。"

    def _generate_tool_calls(self, tool, qtype, customers, months, observations):
        """生成工具调用参数列表"""
        sorted_months = sorted(months, key=lambda x: int(x.replace("月", "")))

        if tool == "get_oversell":
            if qtype == "customer_compare":
                return [{"tool": tool, "params": {"customer": c, "months": sorted_months}} for c in customers]
            return [{"tool": tool, "params": {"customer": customers[0], "months": sorted_months}}]

        elif tool == "get_revenue_factors":
            if qtype == "customer_compare":
                return [{"tool": tool, "params": {"customer": c, "months": sorted_months}} for c in customers]
            return [{"tool": tool, "params": {"customer": customers[0], "months": sorted_months}}]

        elif tool == "get_room_breakdown":
            if qtype == "customer_compare":
                m = sorted_months[-1]
                return [{"tool": tool, "params": {"customer": c, "month": m, "top_n": 5}} for c in customers]
            return [{"tool": tool, "params": {"customer": customers[0], "month": m, "top_n": 5}} for m in sorted_months]

        elif tool == "get_room_detail":
            anomaly_rooms = observations.get("_anomaly_rooms", ["北京"])
            return [{"tool": tool, "params": {"customer": customers[0], "room": r, "months": sorted_months}} for r in anomaly_rooms]

        elif tool == "get_burst_impact":
            latest = sorted_months[-1]
            if qtype == "customer_compare":
                return [{"tool": tool, "params": {"customer": c, "month": latest}} for c in customers]
            return [{"tool": tool, "params": {"customer": customers[0], "month": latest}}]

        elif tool == "verify_calculation":
            # 从已有观察中取数据构造验证表达式
            oversell_obs = observations.get("get_oversell", {})
            latest = sorted_months[-1]
            data = oversell_obs.get(latest) or oversell_obs.get(customers[0], {}).get(latest)
            if data and isinstance(data, dict) and "revenue_wan" in data:
                expr = f"{data['revenue_wan']}/{data['cost_wan']}"
                return [{"tool": tool, "params": {"expression": expr}}]
            return [{"tool": tool, "params": {"expression": "357.0/340.0"}}]

        return []

    # ==================== 观察分析 ====================

    def _handle_analyze(self, system: str, user_msg: str) -> str:
        """模拟 LLM 对工具返回数据的分析"""
        ctx = json.loads(user_msg)
        tool_name = ctx["tool_name"]
        results = ctx["results"]  # list of {params, result}
        qtype = ctx["question_type"]
        observations = ctx.get("observations", {})

        if tool_name == "get_oversell":
            return self._analyze_oversell(results, qtype)
        elif tool_name == "get_revenue_factors":
            return self._analyze_factors(results, qtype)
        elif tool_name == "get_room_breakdown":
            return self._analyze_room_breakdown(results, qtype)
        elif tool_name == "get_room_detail":
            return self._analyze_room_detail(results)
        elif tool_name == "get_burst_impact":
            return self._analyze_burst(results)
        elif tool_name == "verify_calculation":
            return self._analyze_verify(results)
        return "数据分析完成。"

    def _analyze_oversell(self, results, qtype):
        # 收集所有数据点
        all_data = {}
        for r in results:
            if isinstance(r["result"], dict):
                for month, data in r["result"].items():
                    if data:
                        key = f"{data.get('customer', '')}-{month}"
                        all_data[key] = data

        if qtype == "customer_compare":
            items = list(all_data.values())
            if len(items) >= 2:
                parts = []
                for d in items:
                    parts.append(f"{d['customer']}超卖率{d['oversell_rate']}，利润{d['profit_wan']}万")
                return "；".join(parts) + "。需要进一步分析收益因子差异。"

        if qtype == "month_compare" or len(all_data) >= 2:
            values = sorted(all_data.values(), key=lambda x: int(x["month"].replace("月", "")))
            if len(values) >= 2:
                d1, d2 = values[0], values[1]
                diff = d2["oversell_rate"] - d1["oversell_rate"]
                direction = "下降" if diff < 0 else "上升"
                return (f"超卖率从{d1['month']}的{d1['oversell_rate']}{direction}到{d2['month']}的{d2['oversell_rate']}"
                        f"（变化{diff:+.2f}），利润从{d1['profit_wan']}万变为{d2['profit_wan']}万"
                        f"（变化{d2['profit_wan']-d1['profit_wan']:+.1f}万）。需要查收益因子找原因。")

        if all_data:
            d = list(all_data.values())[0]
            return (f"{d['customer']}{d['month']}超卖率{d['oversell_rate']}，"
                    f"成本{d['cost_wan']}万，收入{d['revenue_wan']}万，利润{d['profit_wan']}万。")

        return "未查到有效数据。"

    def _analyze_factors(self, results, qtype):
        all_data = {}
        for r in results:
            if isinstance(r["result"], dict):
                for month, data in r["result"].items():
                    if data:
                        key = f"{data.get('customer', '')}-{month}"
                        all_data[key] = data

        if qtype == "customer_compare":
            items = list(all_data.values())
            if len(items) >= 2:
                d1, d2 = items[0], items[1]
                diffs = []
                if abs(d2["waveform_factor"] - d1["waveform_factor"]) > 0.05:
                    diffs.append(f"波形因子（{d1['customer']}={d1['waveform_factor']} vs {d2['customer']}={d2['waveform_factor']}）")
                if abs(d2["schedule_deviation"] - d1["schedule_deviation"]) > 0.01:
                    diffs.append(f"调度偏差（{d1['customer']}={d1['schedule_deviation']} vs {d2['customer']}={d2['schedule_deviation']}）")
                if abs(d2["peak_avg_ratio"] - d1["peak_avg_ratio"]) > 0.1:
                    diffs.append(f"峰均比（{d1['customer']}={d1['peak_avg_ratio']} vs {d2['customer']}={d2['peak_avg_ratio']}）")
                    return json.dumps({"analysis": "主要差异因子：" + "；".join(diffs), "_has_peak_anomaly": True}, ensure_ascii=False)
                if diffs:
                    return json.dumps({"analysis": "主要差异因子：" + "；".join(diffs), "_has_peak_anomaly": False}, ensure_ascii=False)
                return json.dumps({"analysis": "因子差异不大，需从机房维度分析。", "_has_peak_anomaly": False}, ensure_ascii=False)

        # 纵向对比
        values = sorted(all_data.values(), key=lambda x: int(x["month"].replace("月", "")))
        if len(values) >= 2:
            d1, d2 = values[0], values[1]
            findings = []
            wf_diff = d2["waveform_factor"] - d1["waveform_factor"]
            if abs(wf_diff) > 0.05:
                direction = "下降" if wf_diff < 0 else "上升"
                findings.append(f"波形因子{direction}{abs(wf_diff):.2f}（{d1['waveform_factor']}→{d2['waveform_factor']}），这是主要影响因素")
            sd_diff = d2["schedule_deviation"] - d1["schedule_deviation"]
            if abs(sd_diff) > 0.01:
                findings.append(f"调度偏差增大（{d1['schedule_deviation']}→{d2['schedule_deviation']}）")
            par_diff = d2["peak_avg_ratio"] - d1["peak_avg_ratio"]
            has_peak = abs(par_diff) > 0.1
            if has_peak:
                findings.append(f"峰均比升高（{d1['peak_avg_ratio']}→{d2['peak_avg_ratio']}），疑似有突发流量")

            analysis = "关键发现：" + "；".join(findings) + "。" if findings else "收益因子整体稳定。"
            return json.dumps({"analysis": analysis, "_has_peak_anomaly": has_peak}, ensure_ascii=False)

        if values:
            d = values[0]
            return json.dumps({
                "analysis": f"波形因子={d['waveform_factor']}，调度偏差={d['schedule_deviation']}，"
                            f"带宽利用率={d['bandwidth_utilization']}，峰均比={d['peak_avg_ratio']}。",
                "_has_peak_anomaly": False,
            }, ensure_ascii=False)

        return json.dumps({"analysis": "数据不完整。", "_has_peak_anomaly": False}, ensure_ascii=False)

    def _analyze_room_breakdown(self, results, qtype):
        if qtype == "customer_compare":
            parts = []
            for r in results:
                data = r["result"]
                if data:
                    top = data[0]
                    customer = r["params"]["customer"]
                    parts.append(f"{customer}成本最高机房: {top['room']}（占比{top['share_ratio']:.0%}，成本{top['cost_wan']}万）")
            return json.dumps({"analysis": "；".join(parts), "_anomaly_rooms": []}, ensure_ascii=False)

        # 纵向对比 - 比较两个月的机房数据
        month_data = {}
        for r in results:
            month = r["params"]["month"]
            month_data[month] = {item["room"]: item for item in r["result"]}

        if len(month_data) >= 2:
            ms = sorted(month_data.keys(), key=lambda x: int(x.replace("月", "")))
            rooms1, rooms2 = month_data[ms[0]], month_data[ms[1]]
            anomalies = []
            anomaly_rooms = []
            for room in rooms2:
                if room in rooms1:
                    diff = rooms2[room]["share_ratio"] - rooms1[room]["share_ratio"]
                    if abs(diff) > 0.10:
                        direction = "升高" if diff > 0 else "降低"
                        anomalies.append(
                            f"{room}机房分摊占比{direction}"
                            f"（{rooms1[room]['share_ratio']:.0%}→{rooms2[room]['share_ratio']:.0%}），"
                            f"成本{rooms1[room]['cost_wan']}万→{rooms2[room]['cost_wan']}万"
                        )
                        anomaly_rooms.append(room)
            if anomalies:
                analysis = "机房异常发现：" + "；".join(anomalies) + "。需要查明细确认根因。"
            else:
                analysis = "各机房分摊占比稳定，无明显异常。"
            return json.dumps({"analysis": analysis, "_anomaly_rooms": anomaly_rooms}, ensure_ascii=False)

        return json.dumps({"analysis": "数据不足，无法对比。", "_anomaly_rooms": []}, ensure_ascii=False)

    def _analyze_room_detail(self, results):
        for r in results:
            data = r["result"]
            months_data = {m: d for m, d in data.items() if d}
            if len(months_data) >= 2:
                ms = sorted(months_data.keys(), key=lambda x: int(x.replace("月", "")))
                d1, d2 = months_data[ms[0]], months_data[ms[1]]
                findings = []
                if d1["total_room_bandwidth_tb"] > 0:
                    bw_change = (d2["total_room_bandwidth_tb"] - d1["total_room_bandwidth_tb"]) / d1["total_room_bandwidth_tb"]
                    if bw_change < -0.2:
                        findings.append(f"机房总带宽从{d1['total_room_bandwidth_tb']}TB缩减到{d2['total_room_bandwidth_tb']}TB（减少{abs(bw_change):.0%}）")
                cust_diff = d2["other_customers_count"] - d1["other_customers_count"]
                if cust_diff < -3:
                    findings.append(f"同机房其他客户从{d1['other_customers_count']}家减少到{d2['other_customers_count']}家，有客户迁走")
                uc_diff = d2["unit_cost"] - d1["unit_cost"]
                if uc_diff > 0.1:
                    findings.append(f"单位成本从{d1['unit_cost']}升至{d2['unit_cost']}（涨幅{uc_diff/d1['unit_cost']:.0%}）")

                if findings:
                    room = r["params"]["room"]
                    return (f"【{room}机房根因定位】" + "；".join(findings) + "。"
                            f"结论：其他客户迁走导致机房固定成本由更少客户分摊，{r['params']['customer']}分摊占比被动升高。")
            elif months_data:
                d = list(months_data.values())[0]
                return f"机房带宽{d['bandwidth_tb']}TB，峰值{d['peak_bandwidth_gbps']}Gbps，单位成本{d['unit_cost']}。"
        return "未查到机房明细。"

    def _analyze_burst(self, results):
        parts = []
        for r in results:
            data = r["result"]
            if data is None:
                parts.append("未查到突发数据。")
            elif data["burst_count"] == 0:
                parts.append(f"{data['customer']}无突发流量影响。")
            else:
                parts.append(
                    f"{data['customer']}{data['month']}发生{data['burst_count']}次突发，"
                    f"峰值{data['burst_peak_gbps']}Gbps，额外成本{data['burst_extra_cost_wan']}万。"
                    f"原因：{data['burst_cause']}。"
                )
        return "".join(parts)

    def _analyze_verify(self, results):
        parts = []
        for r in results:
            data = r["result"]
            if data.get("error"):
                parts.append(f"计算出错: {data['error']}")
            else:
                parts.append(f"验证 {data['expression']} = {data['result']}，与数据一致。")
        return "".join(parts)

    # ==================== 条件评估 ====================

    def _handle_condition(self, system: str, user_msg: str) -> str:
        """模拟 LLM 评估条件步骤是否需要执行"""
        ctx = json.loads(user_msg)
        condition = ctx["condition"]
        observations = ctx.get("observations", {})

        if "机房分摊占比变化" in condition:
            anomaly_rooms = observations.get("_anomaly_rooms", [])
            if anomaly_rooms:
                return json.dumps({
                    "execute": True,
                    "reason": f"{'、'.join(anomaly_rooms)}机房分摊占比变化超过10个百分点，需要深入查看明细",
                }, ensure_ascii=False)
            return json.dumps({"execute": False, "reason": "各机房分摊占比变化在正常范围内"}, ensure_ascii=False)

        elif "峰均比" in condition or "突发" in condition:
            if observations.get("_has_peak_anomaly"):
                return json.dumps({
                    "execute": True,
                    "reason": "峰均比升高明显，需要确认是否存在突发流量",
                }, ensure_ascii=False)
            return json.dumps({"execute": False, "reason": "峰均比变化不大，无突发嫌疑"}, ensure_ascii=False)

        elif "验证" in condition or "计算" in condition:
            has_data = bool(observations.get("get_oversell"))
            return json.dumps({
                "execute": has_data,
                "reason": "有超卖数据可供验证" if has_data else "无需验证",
            }, ensure_ascii=False)

        return json.dumps({"execute": False, "reason": "条件不满足"}, ensure_ascii=False)

    # ==================== 报告生成 ====================

    def _handle_report(self, user_msg: str) -> str:
        """模拟 LLM 生成最终分析报告"""
        ctx = json.loads(user_msg)
        qtype = ctx["question_type"]

        if qtype == "query":
            return self._report_query(ctx)
        elif qtype == "month_compare":
            return self._report_month_compare(ctx)
        elif qtype == "customer_compare":
            return self._report_customer_compare(ctx)
        return "暂无法生成报告。"

    def _report_query(self, ctx):
        c = ctx["customers"][0]
        m = sorted(ctx["months"], key=lambda x: int(x.replace("月", "")))[-1]
        obs = ctx.get("observations", {})
        oversell = obs.get("get_oversell", {})
        factors = obs.get("get_revenue_factors", {})

        # 从嵌套结构中提取数据
        data = oversell.get(c, {}).get(m) or oversell.get(m)
        fdata = factors.get(c, {}).get(m) or factors.get(m)

        if not data:
            return f"未找到{c}{m}的数据。"

        lines = [
            f"## {c} {m} 超卖分析报告",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 超卖率 | {data['oversell_rate']} |",
            f"| 总带宽 | {data['total_bandwidth_tb']} TB |",
            f"| 成本 | {data['cost_wan']} 万元 |",
            f"| 收入 | {data['revenue_wan']} 万元 |",
            f"| 利润 | {data['profit_wan']} 万元 |",
        ]
        if fdata:
            lines += [
                "", "### 收益因子明细",
                f"- 波形因子: {fdata['waveform_factor']}（流量曲线匹配度，越高越好）",
                f"- 调度偏差: {fdata['schedule_deviation']}（越低越好）",
                f"- 带宽利用率: {fdata['bandwidth_utilization']}",
                f"- 峰均比: {fdata['peak_avg_ratio']}（越低越好）",
                f"- 单价: {fdata['unit_price']} 万元/TB",
            ]
        return "\n".join(lines)

    def _report_month_compare(self, ctx):
        c = ctx["customers"][0]
        ms = sorted(ctx["months"], key=lambda x: int(x.replace("月", "")))
        obs = ctx.get("observations", {})
        analyses = ctx.get("analyses", [])

        oversell = obs.get("get_oversell", {})
        factors = obs.get("get_revenue_factors", {})
        room_detail = obs.get("get_room_detail", {})
        anomaly_rooms = obs.get("_anomaly_rooms", [])
        burst = obs.get("get_burst_impact")

        d1 = oversell.get(c, {}).get(ms[0]) or oversell.get(ms[0], {})
        d2 = oversell.get(c, {}).get(ms[1]) or oversell.get(ms[1], {})
        f1 = factors.get(c, {}).get(ms[0]) or factors.get(ms[0], {})
        f2 = factors.get(c, {}).get(ms[1]) or factors.get(ms[1], {})

        lines = [
            f"## {c} 超卖纵向对比分析报告（{ms[0]} vs {ms[1]}）",
            "",
            "### 1. 超卖率变化",
            f"- {ms[0]}: 超卖率 {d1.get('oversell_rate', 'N/A')}，利润 {d1.get('profit_wan', 'N/A')} 万",
            f"- {ms[1]}: 超卖率 {d2.get('oversell_rate', 'N/A')}，利润 {d2.get('profit_wan', 'N/A')} 万",
        ]

        if d1 and d2 and "oversell_rate" in d1 and "oversell_rate" in d2:
            rate_diff = d2["oversell_rate"] - d1["oversell_rate"]
            profit_diff = d2["profit_wan"] - d1["profit_wan"]
            lines.append(f"- 变化: 超卖率 {rate_diff:+.2f}，利润 {profit_diff:+.1f} 万")

        lines += ["", "### 2. 根因分析", ""]

        root_causes = []
        if f1 and f2 and "waveform_factor" in f1:
            wf_diff = f2["waveform_factor"] - f1["waveform_factor"]
            if abs(wf_diff) > 0.05:
                root_causes.append(
                    f"**波形因子恶化**：从 {f1['waveform_factor']} 下降到 {f2['waveform_factor']}"
                    f"（降幅 {abs(wf_diff):.2f}），客户流量曲线与机房整体流量匹配度变差，"
                    "带宽无法被有效超卖"
                )
            sd_diff = f2["schedule_deviation"] - f1["schedule_deviation"]
            if abs(sd_diff) > 0.01:
                root_causes.append(
                    f"**调度偏差增大**：从 {f1['schedule_deviation']} 增加到 {f2['schedule_deviation']}，"
                    "流量调度精度下降"
                )

        if anomaly_rooms:
            for room in anomaly_rooms:
                cause = (f"**{room}机房分摊占比被动升高**：该机房其他客户迁走，"
                         f"固定成本由更少客户分摊，{c}分摊成本大幅上升")
                rd = room_detail.get(room, {})
                if len(rd) >= 2:
                    rms = sorted(rd.keys(), key=lambda x: int(x.replace("月", "")))
                    rd1, rd2 = rd[rms[0]], rd[rms[1]]
                    if rd1 and rd2:
                        cause += (f"（机房总带宽 {rd1['total_room_bandwidth_tb']}TB → {rd2['total_room_bandwidth_tb']}TB，"
                                  f"其他客户 {rd1['other_customers_count']} → {rd2['other_customers_count']} 家）")
                root_causes.append(cause)

        if burst and isinstance(burst, dict) and burst.get("burst_count", 0) > 0:
            root_causes.append(
                f"**突发流量影响**：{ms[-1]}发生 {burst['burst_count']} 次突发，"
                f"额外成本 {burst['burst_extra_cost_wan']} 万。原因：{burst['burst_cause']}"
            )

        for i, cause in enumerate(root_causes, 1):
            lines.append(f"{i}. {cause}")
        if not root_causes:
            lines.append("未发现明显根因，建议进一步排查。")

        lines += [
            "", "### 3. 建议措施",
            "1. 优化客户流量调度策略，改善波形因子",
            "2. 评估异常机房的客户迁移情况，必要时重新调整资源分配",
            "3. 与客户沟通流量模式变化，协商突发流量管控方案",
        ]
        return "\n".join(lines)

    def _report_customer_compare(self, ctx):
        customers = ctx["customers"]
        m = sorted(ctx["months"], key=lambda x: int(x.replace("月", "")))[-1]
        c1, c2 = customers[0], customers[1]
        obs = ctx.get("observations", {})

        d1 = obs.get("get_oversell", {}).get(c1, {}).get(m, {})
        d2 = obs.get("get_oversell", {}).get(c2, {}).get(m, {})
        f1 = obs.get("get_revenue_factors", {}).get(c1, {}).get(m, {})
        f2 = obs.get("get_revenue_factors", {}).get(c2, {}).get(m, {})

        lines = [
            f"## 客户横向对比分析报告（{c1} vs {c2}，{m}）",
            "",
            "### 1. 超卖率对比",
            f"| 指标 | {c1} | {c2} |",
            f"|------|------|------|",
        ]
        if d1 and d2:
            lines += [
                f"| 超卖率 | {d1.get('oversell_rate', 'N/A')} | {d2.get('oversell_rate', 'N/A')} |",
                f"| 利润(万) | {d1.get('profit_wan', 'N/A')} | {d2.get('profit_wan', 'N/A')} |",
                f"| 带宽(TB) | {d1.get('total_bandwidth_tb', 'N/A')} | {d2.get('total_bandwidth_tb', 'N/A')} |",
            ]

        lines += ["", "### 2. 因子差异", ""]
        diffs = []
        if f1 and f2:
            factor_names = {
                "waveform_factor": ("波形因子", "越高越好"),
                "schedule_deviation": ("调度偏差", "越低越好"),
                "bandwidth_utilization": ("带宽利用率", "越高越好"),
                "peak_avg_ratio": ("峰均比", "越低越好"),
            }
            lines += [f"| 因子 | {c1} | {c2} | 说明 |", "|------|------|------|------|"]
            for key, (name, note) in factor_names.items():
                v1, v2 = f1.get(key, 0), f2.get(key, 0)
                lines.append(f"| {name} | {v1} | {v2} | {note} |")
                if abs(v2 - v1) > 0.05:
                    diffs.append((name, v1, v2, note))

        lines += ["", "### 3. 差异根因", ""]
        if diffs:
            for name, v1, v2, note in diffs:
                lines.append(f"- **{name}**：{c1}={v1}，{c2}={v2}（{note}）")
            lines += [
                "",
                f"**结论**：{c1}超卖率不如{c2}的主要原因是波形因子和调度偏差表现不如{c2}，"
                f"建议优化{c1}的流量调度策略和流量波形管理。",
            ]
        else:
            lines.append("两个客户的因子差异不大，需要从机房维度进一步分析。")

        return "\n".join(lines)
