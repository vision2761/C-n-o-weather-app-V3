# app_V3.py —— 昆岛机场气象系统 V3
# 包含：天气预报 / 多条 METAR 解析 / 降水记录（1206→12:06）/ 自动降水事件分析

import streamlit as st
import pandas as pd
import re
from datetime import datetime

from db_V3 import (
    init_db,
    insert_forecast, get_forecasts,
    insert_metar, get_recent_metars,
    insert_rain_event, get_rain_events, get_rain_stats_by_day
)

from metar_parser_V3 import parse_metar
from rain_analysis_V3 import analyze_rain_events, plot_rain_events


st.set_page_config(page_title="昆岛机场气象系统 V3", layout="wide")

# 初始化数据库
init_db()

# ============================================================
# 1）天气预报
# ============================================================
def page_forecast():
    st.header("📋 昆岛天气预报录入与查询")

    c1, c2 = st.columns(2)
    with c1:
        date_val = st.date_input("预报日期")
    with c2:
        wind = st.text_input("风向/风速（如 030/05）")

    c3, c4 = st.columns(2)
    with c3:
        temp_min = st.number_input("最低气温 (℃)", value=25.0, format="%.1f")
    with c4:
        temp_max = st.number_input("最高气温 (℃)", value=28.0, format="%.1f")

    weather = st.text_input("天气现象")

    if st.button("保存预报记录"):
        insert_forecast(str(date_val), wind, temp_min, temp_max, weather)
        st.success("保存成功")

    st.markdown("---")
    st.subheader("📑 历史预报")

    s1, s2 = st.columns(2)
    with s1:
        start = st.date_input("开始日期")
    with s2:
        end = st.date_input("结束日期")

    if st.button("查询预报"):
        rows = get_forecasts(str(start), str(end))
        if rows:
            df = pd.DataFrame(rows, columns=["日期", "风", "最低", "最高", "天气"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("无记录")

# ============================================================
# 2）METAR 多条解析
# ============================================================
def page_metar():
    st.header("🛬 METAR 报文解析（支持一键粘贴多条）")

    raw_block = st.text_area(
        "输入报文（每条以 '=' 结束）：",
        height=180,
        placeholder=(
            "例：\n"
            "Rx 210326Z METAR VVCS 210330Z 07008KT ... =\n"
            "Rx 210332Z METAR VVCT 210330Z 01006KT ... =\n"
        )
    )

    if st.button("解析并保存全部报文"):
        text = raw_block.strip()
        if not text:
            st.warning("请先输入内容")
            return

        parts = text.split("=")
        count = 0

        for p in parts:
            t = p.strip()
            if not t:
                continue
            one_line = " ".join(t.split())
            rec = parse_metar(one_line)
            insert_metar(rec)
            count += 1

        st.success(f"已解析 {count} 条报文")

    st.markdown("---")
    st.subheader("📑 最近 METAR 记录")

    rows = get_recent_metars(limit=200)
    if not rows:
        st.info("暂无数据")
        return

    df = pd.DataFrame(
        rows,
        columns=[
            "UTC时间", "站号", "原始报文",
            "风向", "风速", "阵风",
            "能见度", "温度", "露点",
            "天气", "是否雨", "雨型",
            "云1量", "云1高(m)",
            "云2量", "云2高(m)",
            "云3量", "云3高(m)",
        ]
    )

    # 增加越南时间（UTC+7）
    def to_vn(t):
        if not isinstance(t, str):
            return ""
        m = re.match(r"(\d{2})(\d{2})(\d{2})Z", t)
        if not m:
            return ""
        dd, hh, mm = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hh2 = hh + 7
        add = 0
        if hh2 >= 24:
            hh2 -= 24
            add = 1
        return f"{dd+add:02d}日 {hh2:02d}:{mm:02d}"

    df.insert(1, "越南时间(UTC+7)", df["UTC时间"].apply(to_vn))

    st.dataframe(df, use_container_width=True)

# ============================================================
# 3）降水记录（支持数字时间输入）
# ============================================================
def page_rain():
    st.header("🌧 降水过程记录")

    c1, c2 = st.columns(2)
    with c1:
        date_val = st.date_input("日期")
    with c2:
        time_raw = st.text_input("时间（如 537, 1206, 06）")

    # 数字时间智能解析
    def parse_time(s):
        s = s.strip()
        if not s.isdigit():
            return None
        if len(s)==4:
            hh, mm = s[:2], s[2:]
        elif len(s)==3:
            hh, mm = "0"+s[0], s[1:]
        elif len(s)==2:
            hh, mm = "00", s
        elif len(s)==1:
            hh, mm = "00", "0"+s
        else:
            return None
        if not (0<=int(hh)<=23 and 0<=int(mm)<=59):
            return None
        return f"{hh}:{mm}"

    hhmm = parse_time(time_raw)
    time_str = f"{date_val} {hhmm}" if hhmm else None

    rain = st.selectbox("雨强", ["毛毛雨","小雨","中雨","大雨","暴雨","雷阵雨","雨停"])
    code = st.text_input("报文代码（可选）")
    note = st.text_input("备注（可选）")

    if st.button("保存降水记录"):
        if not time_str:
            st.error("时间格式错误")
        else:
            insert_rain_event(time_str, rain, code, note)
            st.success(f"记录成功：{time_str} — {rain}")

    st.markdown("---")
    st.subheader("历史降水记录")

    s1, s2 = st.columns(2)
    with s1:
        start = st.date_input("开始日期")
    with s2:
        end = st.date_input("结束日期")

    if st.button("查询降水记录"):
        rows = get_rain_events(str(start), str(end))
        if rows:
            df = pd.DataFrame(rows, columns=["时间","雨强","报文代码","备注"])
            df["时间"] = pd.to_datetime(df["时间"])
            st.dataframe(df, use_container_width=True)

# ============================================================
# 4）自动降水事件分析（事件分段 + 图表）
# ============================================================
def page_rain_analysis():
    st.header("📘 自动降水事件分析（V3）")

    s1, s2 = st.columns(2)
    with s1:
        start = st.date_input("开始日期")
    with s2:
        end = st.date_input("结束日期")

    if st.button("生成降水事件分析"):
        rows = get_rain_events(str(start), str(end))
        if not rows:
            st.info("无降水记录")
            return

        df = pd.DataFrame(rows, columns=["时间","雨强","代码","备注"])
        df["时间"] = pd.to_datetime(df["时间"])

        events = analyze_rain_events(df)

        # 文本报告
        for ev in events:
            st.markdown(ev["report"])

        # 图表
        chart = plot_rain_events(events)
        st.altair_chart(chart, use_container_width=True)

# ============================================================
# 主程序
# ============================================================
def main():
    st.title("✈ 昆岛机场气象记录系统 V3")

    page = st.sidebar.radio(
        "功能选择", 
        [
            "天气预报",
            "METAR 多条解析",
            "降水记录",
            "自动降水事件分析（V3）",
        ]
    )

    if page == "天气预报": page_forecast()
    elif page == "METAR 多条解析": page_metar()
    elif page == "降水记录": page_rain()
    elif page == "自动降水事件分析（V3）": page_rain_analysis()


if __name__ == "__main__":
    main()
