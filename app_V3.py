# app_V3.py —— 昆岛机场气象系统 v3
# 新增模块：自动降水事件分析

import streamlit as st
import pandas as pd
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
#  1）天气预报页面
# ============================================================
def page_forecast():
    st.header("📋 昆岛天气预报录入与查询")

    c1, c2 = st.columns(2)
    with c1:
        date_val = st.date_input("预报日期")
    with c2:
        wind = st.text_input("风向/风速（如：030/05）")

    c3, c4 = st.columns(2)
    with c3:
        temp_min = st.number_input("最低气温 (℃)", value=25.0)
    with c4:
        temp_max = st.number_input("最高气温 (℃)", value=28.0)

    weather = st.text_input("天气现象（如：分散对流伴短时阵雨）")

    if st.button("保存预报记录"):
        insert_forecast(str(date_val), wind, temp_min, temp_max, weather)
        st.success("保存成功")

    st.markdown("---")
    st.subheader("📑 历史天气预报")

    start = st.date_input("开始日期", key="fc_s")
    end = st.date_input("结束日期", key="fc_e")

    if st.button("查询历史预报"):
        rows = get_forecasts(str(start), str(end))
        if rows:
            df = pd.DataFrame(rows, columns=["日期","风向风速","最低温","最高温","天气"])
            df["平均温"] = (df["最低温"] + df["最高温"])/2
            df["日期"] = pd.to_datetime(df["日期"])
            st.dataframe(df, use_container_width=True)
            st.line_chart(df.set_index("日期")["平均温"], height=300)
        else:
            st.info("无记录")

# ============================================================
#  2）METAR 页面
# ============================================================
def page_metar():
    st.header("🛬 METAR / SPECI 解析")

    raw = st.text_area("输入 METAR 报文：")
    if st.button("解析并保存"):
        if raw.strip():
            rec = parse_metar(raw)
            insert_metar(rec)
            st.success("解析完成")
            st.json(rec)

    st.markdown("---")
    st.subheader("📑 最近解析记录")

    rows = get_recent_metars(100)
    if rows:
        df = pd.DataFrame(rows, columns=[
            "报文时间","站号","原始报文",
            "风向","风速","阵风","能见度",
            "温度","露点","天气","是否雨","雨型",
            "云量1","云高1","云量2","云高2","云量3","云高3"
        ])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("暂无数据")

# ============================================================
#  3）降水过程记录（含智能时间输入）
# ============================================================
def page_rain():
    st.header("🌧 降水变化记录（精确到分钟）")

    # 日期 + 数字时间输入
    c1, c2 = st.columns(2)
    with c1:
        date_val = st.date_input("日期")
    with c2:
        time_raw = st.text_input("时间（如 537 → 05:37, 1206 → 12:06）")

    # 智能解析时间
    def parse_time_numeric(s):
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

    time_hhmm = parse_time_numeric(time_raw)
    time_str = f"{date_val} {time_hhmm}" if time_hhmm else None

    rain = st.selectbox("雨强", ["毛毛雨","小雨","中雨","大雨","暴雨","雷阵雨","雨停"])
    rain_code = st.text_input("报文代码（如 -RA, +RA, TSRA 等）")
    note = st.text_input("备注")

    if st.button("保存记录"):
        if not time_str:
            st.error("时间格式错误，请输入数字如 537 / 1206")
        else:
            insert_rain_event(time_str, rain, rain_code, note)
            st.success(f"已记录：{time_str} — {rain}")

    st.markdown("---")
    st.subheader("📑 历史降水记录")

    s1, s2 = st.columns(2)
    with s1:
        start = st.date_input("开始日期", key="rain_s")
    with s2:
        end = st.date_input("结束日期", key="rain_e")

    if st.button("查询降水历史"):
        rows = get_rain_events(str(start), str(end))
        if rows:
            df = pd.DataFrame(rows, columns=["时间","雨强","报文代码","备注"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("无记录")

# ============================================================
#  4）自动降水事件分析（新增页面）
# ============================================================
def page_rain_auto():
    st.header("📘 降水事件自动分析（自动分段）")

    c1, c2 = st.columns(2)
    with c1:
        start = st.date_input("开始日期", key="auto_s")
    with c2:
        end = st.date_input("结束日期", key="auto_e")

    if st.button("生成降水事件分析"):
        rows = get_rain_events(str(start), str(end))
        if not rows:
            st.info("无降水记录")
            return

        df = pd.DataFrame(rows, columns=["时间","雨强","报文代码","备注"])
        df["时间"] = pd.to_datetime(df["时间"])
        df = df.sort_values("时间")

        events = analyze_rain_events(df)

        # 文本版输出
        st.subheader("📝 降水事件文本报告")
        for i, ev in enumerate(events, start=1):
            st.markdown(ev["report"])

        # 图形版输出
        st.subheader("📈 降水事件图表")
        fig = plot_rain_events(events)
        st.pyplot(fig)

# ============================================================
# 主程序
# ============================================================
def main():
    st.title("✈ 昆岛机场气象记录系统 V3")

    pg = st.sidebar.radio(
        "选择功能",
        ["天气预报", "METAR解析", "降水记录", "自动降水分析"]
    )

    if pg=="天气预报":
        page_forecast()
    elif pg=="METAR解析":
        page_metar()
    elif pg=="降水记录":
        page_rain()
    elif pg=="自动降水分析":
        page_rain_auto()

if __name__ == "__main__":
    main()
