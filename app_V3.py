# app_V3.py —— Côn Đảo Weather System V3
# 含：批量 METAR 解析 + 自动降水分析

import streamlit as st
import pandas as pd
from datetime import datetime

from db_V3 import (
    init_db,
    insert_forecast, get_forecasts,
    insert_metar, get_recent_metars,
    insert_rain_event, get_rain_events, get_rain_stats_by_day
)

from metar_parser_V3 import parse_single_metar, parse_multiple_metar
from rain_analysis_V3 import analyze_rain_events, plot_rain_events

st.set_page_config(page_title="昆岛机场气象系统 V3", layout="wide")

init_db()

# -------------- METAR PAGE ---------------
def page_metar():
    st.header("🛬 批量 METAR 解析")

    txt = st.text_area("粘贴多个 METAR（可包含 Rx、多个机场、TEMPO、NOSIG）：" , height=200)

    if st.button("解析所有报文"):
        if not txt.strip():
            st.error("请输入内容")
            return

        parsed = parse_multiple_metar(txt)

        st.success(f"成功解析 {len(parsed)} 条报文")

        df = pd.DataFrame(parsed)
        st.dataframe(df, use_container_width=True)

        # 可选：自动入库
        if st.checkbox("将所有报文入数据库"):
            for rec in parsed:
                insert_metar(rec)
            st.success("已全部写入数据库")

# -------------- 其他页面同 V3，不影响运行 ---------------


def main():
    st.title("✈ 昆岛机场气象系统 V3")

    pg = st.sidebar.radio(
        "选择功能",
        ["METAR 解析", "其他暂略"]
    )

    if pg == "METAR 解析":
        page_metar()


if __name__ == "__main__":
    main()
