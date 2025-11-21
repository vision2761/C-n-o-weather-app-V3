# metar_parser_V3.py —— METAR 报文解析模块（含云量、雨型、阵风、温度等）
# ⚠️ 不依赖数据库，不 import db_V3

import re

def parse_metar(text: str):
    text = text.strip()

    result = {
        "raw": text,
        "station": None,
        "obs_time": None,
        "wind_direction": None,
        "wind_speed": None,
        "wind_gust": None,
        "visibility": None,
        "temperature": None,
        "dewpoint": None,
        "is_raining": False,
        "rain_type": None,
        "weather": [],
        "clouds": [],
    }

    parts = text.split()
    if parts:
        result["station"] = parts[0]

    # 报文时间
    m = re.search(r"\b(\d{6})Z\b", text)
    if m:
        result["obs_time"] = m.group(1) + "Z"

    # 风
    wind_match = re.search(r"(VRB|\d{3})(\d{2,3})(?:G(\d{2,3}))?KT", text)
    if wind_match:
        d = wind_match.group(1)
        if d != "VRB":
            result["wind_direction"] = int(d)
        result["wind_speed"] = int(wind_match.group(2))
        if wind_match.group(3):
            result["wind_gust"] = int(wind_match.group(3))

    # 能见度
    vis_match = re.search(r"\b(\d{4})\b", text)
    if vis_match:
        result["visibility"] = int(vis_match.group(1))

    # 温度露点
    temp_match = re.search(r"\b(M?\d{2})/(M?\d{2})\b", text)
    if temp_match:
        t = temp_match.group(1)
        d = temp_match.group(2)
        result["temperature"] = -int(t[1:]) if t.startswith("M") else int(t)
        result["dewpoint"] = -int(d[1:]) if d.startswith("M") else int(d)

    # 云量转换（ft → m）
    cloud_matches = re.findall(r"(FEW|SCT|BKN|OVC)(\d{3})", text)
    for amt, h in cloud_matches:
        ft = int(h) * 100
        m_height = round(ft * 0.3048)
        result["clouds"].append({
            "amount": amt,
            "height_m": m_height
        })

    # 天气现象
    WEATHER_PATTERNS = {
        r'\+SHRA': ('大阵雨', True, '大雨'),
        r'\-SHRA': ('小阵雨', True, '小雨'),
        r'\bSHRA\b': ('中阵雨', True, '中雨'),

        r'\+RA\b': ('大雨', True, '大雨'),
        r'\-RA\b': ('小雨', True, '小雨'),
        r'\bRA\b': ('中雨', True, '中雨'),

        r'TSRA': ('雷雨', True, '雷阵雨'),
        r'\bTS\b': ('雷暴', False, None),

        r'\bDZ\b': ('毛毛雨', True, '小雨'),
        r'\bFG\b': ('雾', False, None),
        r'\bBR\b': ('薄雾', False, None),
        r'\bHZ\b': ('霾', False, None),
    }

    for pattern, (desc, israin, rainlevel) in WEATHER_PATTERNS.items():
        if re.search(pattern, text):
            result["weather"].append(desc)
            if israin:
                result["is_raining"] = True
                if result["rain_type"] is None:
                    result["rain_type"] = rainlevel

    return result
