# rain_analysis_V3.py —— 自动识别降水事件 & 生成图表（matplotlib 版本）
# 支持 Streamlit Cloud（需要 requirements.txt 中包含 matplotlib）

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.font_manager import FontProperties

# ================================
# 中文字体（自动处理）
# ================================
try:
    font = FontProperties(fname="/System/Library/Fonts/STHeiti Medium.ttc")  # macOS
    plt.rcParams['font.family'] = font.get_name()
except:
    plt.rcParams['font.family'] = "sans-serif"
    plt.rcParams['font.sans-serif'] = ["SimHei", "Arial Unicode MS"]

plt.rcParams['axes.unicode_minus'] = False  # 避免负号乱码

# ================================
# 雨强 → 数值映射
# ================================
RAIN_LEVEL_MAP = {
    "雨停": 0,
    "毛毛雨": 0.5,
    "小雨": 1,
    "中雨": 2,
    "大雨": 3,
    "暴雨": 4,
    "雷阵雨": 3.5,
}

# ---------------------------------------------------------
# 自动分段：把连续降水记录合并成降水事件
# ---------------------------------------------------------
def analyze_rain_events(df):
    df["强度"] = df["雨强"].map(RAIN_LEVEL_MAP)
    df = df.sort_values("时间")

    events = []
    current = []

    for _, row in df.iterrows():
        if row["雨强"] != "雨停":
            current.append(row)
        else:
            # 雨停作为结束标志
            current.append(row)
            events.append(current)
            current = []

    # 未雨停也算一个事件
    if current:
        events.append(current)

    return [format_event(ev) for ev in events]

# ---------------------------------------------------------
# 格式化单个降水事件
# ---------------------------------------------------------
def format_event(records):
    times = [r["时间"] for r in records]
    rains = [r["雨强"] for r in records]
    strengths = [RAIN_LEVEL_MAP[r] for r in rains]

    start = times[0]
    end = times[-1]

    duration = (end - start).total_seconds() / 60
    max_rain = rains[strengths.index(max(strengths))]

    process = " → ".join(rains)

    report = f"""
### 【降水事件】
- 时间：{start.strftime('%Y-%m-%d %H:%M')} — {end.strftime('%H:%M')}（{int(duration)} 分钟）
- 过程：{process}
- 最强雨强：{max_rain}
"""

    return {"records": records, "report": report}

# ---------------------------------------------------------
# 事件图表（matplotlib）
# ---------------------------------------------------------
def plot_rain_events(events):
    fig, ax = plt.subplots(figsize=(12, 5))

    # 颜色循环
    colors = ["blue", "orange", "green", "red", "purple", "brown", "cyan"]

    for idx, ev in enumerate(events):
        records = ev["records"]

        times = [r["时间"] for r in records]
        vals = [RAIN_LEVEL_MAP[r["雨强"]] for r in records]

        ax.plot(
            times, vals,
            marker="o",
            linewidth=2,
            markersize=7,
            color=colors[idx % len(colors)],
            label=f"事件 {idx+1}"
        )

    ax.set_ylabel("降水强度等级", fontsize=12)
    ax.set_title("降水事件强度随时间变化", fontsize=14)

    ax.grid(True, linestyle="--", alpha=0.6)
    plt.xticks(rotation=45, ha="right")

    ax.legend()
    plt.tight_layout()

    return fig
