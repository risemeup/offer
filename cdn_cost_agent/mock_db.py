"""
模拟数据库 — 用 Python dict 模拟 6 张业务表
内置场景：客户A 3月波形因子变差 + 北京机房分摊占比被动升高
"""

# 表1: 超卖汇总
OVERSELL_SUMMARY = {
    ("客户A", "2月"): {
        "customer": "客户A", "month": "2月",
        "oversell_rate": 1.15, "total_bandwidth_tb": 850,
        "cost_wan": 320.0, "revenue_wan": 368.0,
        "profit_wan": 48.0,
    },
    ("客户A", "3月"): {
        "customer": "客户A", "month": "3月",
        "oversell_rate": 1.05, "total_bandwidth_tb": 880,
        "cost_wan": 340.0, "revenue_wan": 357.0,
        "profit_wan": 17.0,
    },
    ("客户B", "2月"): {
        "customer": "客户B", "month": "2月",
        "oversell_rate": 1.18, "total_bandwidth_tb": 620,
        "cost_wan": 210.0, "revenue_wan": 247.8,
        "profit_wan": 37.8,
    },
    ("客户B", "3月"): {
        "customer": "客户B", "month": "3月",
        "oversell_rate": 1.20, "total_bandwidth_tb": 650,
        "cost_wan": 215.0, "revenue_wan": 258.0,
        "profit_wan": 43.0,
    },
    ("客户C", "2月"): {
        "customer": "客户C", "month": "2月",
        "oversell_rate": 1.10, "total_bandwidth_tb": 430,
        "cost_wan": 180.0, "revenue_wan": 198.0,
        "profit_wan": 18.0,
    },
    ("客户C", "3月"): {
        "customer": "客户C", "month": "3月",
        "oversell_rate": 1.12, "total_bandwidth_tb": 450,
        "cost_wan": 185.0, "revenue_wan": 207.2,
        "profit_wan": 22.2,
    },
}

# 表2: 收益因子
REVENUE_FACTORS = {
    ("客户A", "2月"): {
        "customer": "客户A", "month": "2月",
        "waveform_factor": 0.85,       # 波形因子 (越高越好, 表示流量曲线与整体越匹配)
        "schedule_deviation": 0.03,     # 调度偏差 (越低越好)
        "bandwidth_utilization": 0.78,  # 带宽利用率
        "peak_avg_ratio": 1.35,         # 峰均比
        "unit_price": 0.43,             # 单价(万元/TB)
    },
    ("客户A", "3月"): {
        "customer": "客户A", "month": "3月",
        "waveform_factor": 0.72,        # 明显变差!
        "schedule_deviation": 0.05,      # 略有增加
        "bandwidth_utilization": 0.75,
        "peak_avg_ratio": 1.52,          # 峰均比升高
        "unit_price": 0.41,
    },
    ("客户B", "2月"): {
        "customer": "客户B", "month": "2月",
        "waveform_factor": 0.88,
        "schedule_deviation": 0.02,
        "bandwidth_utilization": 0.82,
        "peak_avg_ratio": 1.25,
        "unit_price": 0.40,
    },
    ("客户B", "3月"): {
        "customer": "客户B", "month": "3月",
        "waveform_factor": 0.90,
        "schedule_deviation": 0.02,
        "bandwidth_utilization": 0.83,
        "peak_avg_ratio": 1.22,
        "unit_price": 0.40,
    },
    ("客户C", "2月"): {
        "customer": "客户C", "month": "2月",
        "waveform_factor": 0.80,
        "schedule_deviation": 0.04,
        "bandwidth_utilization": 0.76,
        "peak_avg_ratio": 1.40,
        "unit_price": 0.46,
    },
    ("客户C", "3月"): {
        "customer": "客户C", "month": "3月",
        "waveform_factor": 0.81,
        "schedule_deviation": 0.04,
        "bandwidth_utilization": 0.77,
        "peak_avg_ratio": 1.38,
        "unit_price": 0.46,
    },
}

# 表3: 机房分摊
ROOM_BREAKDOWN = {
    ("客户A", "2月"): [
        {"room": "北京", "share_ratio": 0.20, "cost_wan": 64.0, "bandwidth_tb": 170},
        {"room": "上海", "share_ratio": 0.25, "cost_wan": 80.0, "bandwidth_tb": 212},
        {"room": "广州", "share_ratio": 0.22, "cost_wan": 70.4, "bandwidth_tb": 187},
        {"room": "深圳", "share_ratio": 0.18, "cost_wan": 57.6, "bandwidth_tb": 153},
        {"room": "成都", "share_ratio": 0.15, "cost_wan": 48.0, "bandwidth_tb": 128},
    ],
    ("客户A", "3月"): [
        {"room": "北京", "share_ratio": 0.35, "cost_wan": 119.0, "bandwidth_tb": 176},  # 占比大幅升高!
        {"room": "上海", "share_ratio": 0.22, "cost_wan": 74.8, "bandwidth_tb": 194},
        {"room": "广州", "share_ratio": 0.18, "cost_wan": 61.2, "bandwidth_tb": 158},
        {"room": "深圳", "share_ratio": 0.15, "cost_wan": 51.0, "bandwidth_tb": 132},
        {"room": "成都", "share_ratio": 0.10, "cost_wan": 34.0, "bandwidth_tb": 88},
    ],
    ("客户B", "2月"): [
        {"room": "北京", "share_ratio": 0.18, "cost_wan": 37.8, "bandwidth_tb": 112},
        {"room": "上海", "share_ratio": 0.28, "cost_wan": 58.8, "bandwidth_tb": 174},
        {"room": "广州", "share_ratio": 0.22, "cost_wan": 46.2, "bandwidth_tb": 136},
        {"room": "深圳", "share_ratio": 0.20, "cost_wan": 42.0, "bandwidth_tb": 124},
        {"room": "成都", "share_ratio": 0.12, "cost_wan": 25.2, "bandwidth_tb": 74},
    ],
    ("客户B", "3月"): [
        {"room": "北京", "share_ratio": 0.17, "cost_wan": 36.6, "bandwidth_tb": 110},
        {"room": "上海", "share_ratio": 0.30, "cost_wan": 64.5, "bandwidth_tb": 195},
        {"room": "广州", "share_ratio": 0.22, "cost_wan": 47.3, "bandwidth_tb": 143},
        {"room": "深圳", "share_ratio": 0.19, "cost_wan": 40.9, "bandwidth_tb": 124},
        {"room": "成都", "share_ratio": 0.12, "cost_wan": 25.8, "bandwidth_tb": 78},
    ],
    ("客户C", "2月"): [
        {"room": "北京", "share_ratio": 0.22, "cost_wan": 39.6, "bandwidth_tb": 95},
        {"room": "上海", "share_ratio": 0.24, "cost_wan": 43.2, "bandwidth_tb": 103},
        {"room": "广州", "share_ratio": 0.20, "cost_wan": 36.0, "bandwidth_tb": 86},
        {"room": "深圳", "share_ratio": 0.18, "cost_wan": 32.4, "bandwidth_tb": 77},
        {"room": "成都", "share_ratio": 0.16, "cost_wan": 28.8, "bandwidth_tb": 69},
    ],
    ("客户C", "3月"): [
        {"room": "北京", "share_ratio": 0.21, "cost_wan": 38.9, "bandwidth_tb": 95},
        {"room": "上海", "share_ratio": 0.25, "cost_wan": 46.3, "bandwidth_tb": 113},
        {"room": "广州", "share_ratio": 0.20, "cost_wan": 37.0, "bandwidth_tb": 90},
        {"room": "深圳", "share_ratio": 0.18, "cost_wan": 33.3, "bandwidth_tb": 81},
        {"room": "成都", "share_ratio": 0.16, "cost_wan": 29.6, "bandwidth_tb": 72},
    ],
}

# 表4: 机房明细（含更多维度）
ROOM_DETAIL = {
    ("客户A", "北京", "2月"): {
        "room": "北京", "customer": "客户A", "month": "2月",
        "bandwidth_tb": 170, "peak_bandwidth_gbps": 52,
        "cost_wan": 64.0, "unit_cost": 0.376,
        "total_room_bandwidth_tb": 850,   # 整个机房总带宽
        "other_customers_count": 12,       # 该机房其他客户数
        "room_utilization": 0.82,
    },
    ("客户A", "北京", "3月"): {
        "room": "北京", "customer": "客户A", "month": "3月",
        "bandwidth_tb": 176, "peak_bandwidth_gbps": 68,   # 峰值升高
        "cost_wan": 119.0, "unit_cost": 0.676,             # 单位成本大幅升高!
        "total_room_bandwidth_tb": 500,    # 机房总带宽缩减! (其他客户迁走)
        "other_customers_count": 5,         # 其他客户数减少!
        "room_utilization": 0.65,           # 利用率下降
    },
    ("客户A", "上海", "2月"): {
        "room": "上海", "customer": "客户A", "month": "2月",
        "bandwidth_tb": 212, "peak_bandwidth_gbps": 61,
        "cost_wan": 80.0, "unit_cost": 0.377,
        "total_room_bandwidth_tb": 900,
        "other_customers_count": 15,
        "room_utilization": 0.85,
    },
    ("客户A", "上海", "3月"): {
        "room": "上海", "customer": "客户A", "month": "3月",
        "bandwidth_tb": 194, "peak_bandwidth_gbps": 58,
        "cost_wan": 74.8, "unit_cost": 0.386,
        "total_room_bandwidth_tb": 880,
        "other_customers_count": 14,
        "room_utilization": 0.83,
    },
    ("客户B", "北京", "3月"): {
        "room": "北京", "customer": "客户B", "month": "3月",
        "bandwidth_tb": 110, "peak_bandwidth_gbps": 32,
        "cost_wan": 36.6, "unit_cost": 0.333,
        "total_room_bandwidth_tb": 500,
        "other_customers_count": 5,
        "room_utilization": 0.65,
    },
}

# 表5: 突发影响
BURST_IMPACT = {
    ("客户A", "2月"): {
        "customer": "客户A", "month": "2月",
        "burst_count": 2,
        "burst_peak_gbps": 15,
        "burst_extra_cost_wan": 3.2,
        "burst_duration_hours": 4,
        "burst_cause": "春节活动流量高峰",
    },
    ("客户A", "3月"): {
        "customer": "客户A", "month": "3月",
        "burst_count": 5,           # 突发次数增加
        "burst_peak_gbps": 28,      # 突发峰值更高
        "burst_extra_cost_wan": 8.5, # 额外成本增加
        "burst_duration_hours": 12,
        "burst_cause": "业务活动频繁，多次超出带宽基线",
    },
    ("客户B", "3月"): {
        "customer": "客户B", "month": "3月",
        "burst_count": 1,
        "burst_peak_gbps": 8,
        "burst_extra_cost_wan": 1.5,
        "burst_duration_hours": 2,
        "burst_cause": "偶发流量尖峰",
    },
    ("客户C", "3月"): {
        "customer": "客户C", "month": "3月",
        "burst_count": 0,
        "burst_peak_gbps": 0,
        "burst_extra_cost_wan": 0,
        "burst_duration_hours": 0,
        "burst_cause": "无突发",
    },
}

# 表6: 客户基本信息
CUSTOMER_INFO = {
    "客户A": {
        "name": "客户A", "industry": "视频直播",
        "contract_bandwidth_gbps": 200, "contract_start": "2025-01",
        "billing_model": "95峰值计费", "priority": "P0",
    },
    "客户B": {
        "name": "客户B", "industry": "电商",
        "contract_bandwidth_gbps": 150, "contract_start": "2024-06",
        "billing_model": "95峰值计费", "priority": "P1",
    },
    "客户C": {
        "name": "客户C", "industry": "游戏",
        "contract_bandwidth_gbps": 100, "contract_start": "2025-03",
        "billing_model": "月均计费", "priority": "P1",
    },
}
