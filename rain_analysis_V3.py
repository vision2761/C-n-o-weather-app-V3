# rain_analysis_V3.py —— 自动识别降水事件 & 生成图表

import matplotlib.pyplot as plt
import pandas as pd

# 雨强 → 数值映射
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

    events = []
    current = []

    for _, row in df.iterrows():
        if row["雨强"] != "雨停":
            current.append(row)
        else:
            if current:
                events.append(current + [row])  # 包含结束
                current = []

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
# 事件图表
# ---------------------------------------------------------
def plot_rain_events(events):
    fig, ax = plt.subplots(figsize=(10, 4))

    colors = ["blue", "orange", "green", "red", "purple", "brown"]

    for idx, ev in enumerate(events):
        times = [r["时间"] for r in ev["records"]]
        vals = [RAIN_LEVEL_MAP[r["雨强"]] for r in ev["records"]]

        ax.plot(times, vals, marker="o", color=colors[idx % len(colors)], label=f"事件 {idx+1}")

    ax.set_ylabel("降水强度等级")
    ax.set_title("降水事件强度随时间变化")
    ax.grid(True)
    ax.legend()

    return fig
