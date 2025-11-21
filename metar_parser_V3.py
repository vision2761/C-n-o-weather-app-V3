# metar_parser_V3_fixed.py
# 修复：站号识别、越南时间、本地时间、批量解析、云高(m)

import re
from datetime import datetime, timedelta


# ---------------------------------------------------------
# 工具函数：解析单条 METAR
# ---------------------------------------------------------
def parse_single_metar(text: str):
    text = text.strip()

    result = {
        "raw": text,
        "station": None,
        "obs_time_utc": None,
        "obs_time_vietnam": None,
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

    # -----------------------------------------------------
    # 站号：METAR 后的 4 字母 ICAO 代码
    # -----------------------------------------------------
    m = re.search(r"METAR\s+([A-Z]{4})", text)
    if m:
        result["station"] = m.group(1)

    # -----------------------------------------------------
    # 报文时间（UTC）
    # 格式：210330Z（21 日，03:30 UTC）
    # -----------------------------------------------------
    t = re.search(r"\b(\d{6})Z\b", text)
    if t:
        raw = t.group(1)  # 210330
        day = int(raw[0:2])
        hour = int(raw[2:4])
        minute = int(raw[4:6])

        # 默认按当前月 / 年推算
        now = datetime.utcnow()
        obs_time_utc = datetime(now.year, now.month, day, hour, minute)
        vn_time = obs_time_utc + timedelta(hours=7)

        result["obs_time_utc"] = obs_time_utc.strftime("%Y-%m-%d %H:%M UTC")
        result["obs_time_vietnam"] = vn_time.strftime("%Y-%m-%d %H:%M (越南)")

    # -----------------------------------------------------
    # 风，如 07008KT 或 340V120 变化风向
    # -----------------------------------------------------
    wind = re.search(r"(VRB|\d{3})(\d{2,3})(?:G(\d{2,3}))?KT", text)
    if wind:
        if wind.group(1) != "VRB":
            result["wind_direction"] = int(wind.group(1))
        result["wind_speed"] = int(wind.group(2))
        if wind.group(3):
            result["wind_gust"] = int(wind.group(3))

    # -----------------------------------------------------
    # 能见度（4 位数字）
    # -----------------------------------------------------
    vis = re.search(r"\b(\d{4})\b", text)
    if vis:
        result["visibility"] = int(vis.group(1))

    # -----------------------------------------------------
    # 温度 / 露点
    # -----------------------------------------------------
    tempd = re.search(r"\b(M?\d{2})/(M?\d{2})\b", text)
    if tempd:
        t = tempd.group(1)
        d = tempd.group(2)
        result["temperature"] = -int(t[1:]) if t.startswith("M") else int(t)
        result["dewpoint"] = -int(d[1:]) if d.startswith("M") else int(d)

    # -----------------------------------------------------
    # 云量 FEW / SCT / BKN / OVC
    # -----------------------------------------------------
    clouds = re.findall(r"(FEW|SCT|BKN|OVC)(\d{3})", text)
    for amt, h in clouds:
        ft = int(h) * 100
        m = round(ft * 0.3048)
        result["clouds"].append({
            "amount": amt,
            "height_m": f"{m} m"
        })

    # -----------------------------------------------------
    # 天气现象
    # -----------------------------------------------------
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

    for pattern, (desc, israin, level) in WEATHER_PATTERNS.items():
        if re.search(pattern, text):
            result["weather"].append(desc)
            if israin:
                result["is_raining"] = True
                if result["rain_type"] is None:
                    result["rain_type"] = level

    return result


# ---------------------------------------------------------
# 批量解析：多个报文一次输入
# ---------------------------------------------------------
def parse_multiple_metar(text_block: str):
    # 用等号和换行分段
    raw_segments = re.split(r"=\s*|\n+", text_block)
    segments = [s.strip() for s in raw_segments if s.strip()]

    parsed = []
    for seg in segments:
        parsed.append(parse_single_metar(seg))

    return parsed
