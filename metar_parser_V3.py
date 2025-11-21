# metar_parser_improved.py —— 增强版 METAR 报文解析模块
# 根据真实报文优化，修复所有识别问题

import re
from typing import Dict, List, Optional

def parse_metar(text: str) -> Dict:
    """
    解析METAR报文
    
    Args:
        text: METAR报文文本（支持多行，支持Rx前缀）
    
    Returns:
        解析结果字典
    """
    # 预处理
    text = text.strip()
    text = " ".join(text.split())  # 合并多行，去除多余空格
    text = text.replace("=", "")   # 去除结束标记
    
    # 去除Rx前缀（如：Rx 210330Z METAR...）
    text = re.sub(r'^Rx\s+\d{6}Z\s+', '', text)
    
    result = {
        "raw": text,
        "station": None,
        "obs_time": None,
        "wind_direction": None,
        "wind_speed": None,
        "wind_gust": None,
        "wind_variable": None,
        "visibility": None,
        "visibility_description": None,
        "temperature": None,
        "dewpoint": None,
        "pressure_qnh": None,
        "is_raining": False,
        "rain_type": None,
        "weather": [],
        "clouds": [],
        "cavok": False,
        "is_corrected": False,
    }
    
    # ================== 检测修正报 ==================
    if re.search(r'\bCOR\b', text):
        result["is_corrected"] = True
    
    # ================== 站号识别 ==================
    m_sta = re.search(r'\b(?:METAR|SPECI)\s+([A-Z]{4})\b', text)
    if m_sta:
        result["station"] = m_sta.group(1)
    else:
        # 备用：找第一个4字母大写（排除关键词）
        excluded = {'METAR', 'SPECI', 'AUTO', 'CAVOK', 'NOSIG'}
        for word in text.split():
            if len(word) == 4 and word.isupper() and word.isalpha() and word not in excluded:
                result["station"] = word
                break
    
    # ================== 时间识别 ==================
    times = re.findall(r'\b(\d{6})Z\b', text)
    if times:
        result["obs_time"] = times[-1] + "Z"
    
    # ================== 风向风速 ==================
    wind_match = re.search(r'\b(VRB|\d{3})(\d{2,3})(?:G(\d{2,3}))?(KT|MPS|KMH)?\b', text)
    if wind_match:
        direction = wind_match.group(1)
        if direction != "VRB":
            result["wind_direction"] = int(direction)
        
        speed = int(wind_match.group(2))
        unit = wind_match.group(4) or "KT"
        
        # 统一转换为KT
        if unit == "MPS":
            speed = round(speed * 1.944)
        elif unit == "KMH":
            speed = round(speed * 0.54)
        result["wind_speed"] = speed
        
        if wind_match.group(3):
            gust = int(wind_match.group(3))
            if unit == "MPS":
                gust = round(gust * 1.944)
            elif unit == "KMH":
                gust = round(gust * 0.54)
            result["wind_gust"] = gust
    
    # 风向变化
    var_match = re.search(r'\b(\d{3})V(\d{3})\b', text)
    if var_match:
        result["wind_variable"] = f"{var_match.group(1)}-{var_match.group(2)}"
    
    # ================== CAVOK检测 ==================
    result["cavok"] = bool(re.search(r'\bCAVOK\b', text))
    if result["cavok"]:
        result["visibility"] = 9999
        result["visibility_description"] = "CAVOK - 能见度≥10km，无显著云，无重要天气"
    
    # ================== 能见度（修复版） ==================
    if not result["cavok"]:
        # 在风之后、天气现象或云或温度之前找能见度
        # 排除时间(6位数)、云高(FEW020格式)、气压(Q1026格式)
        vis_pattern = r'(?:KT|MPS|KMH|\d{3}V\d{3})\s+(\d{4})(?=\s+(?:[+\-]?[A-Z]{2,}|FEW|SCT|BKN|OVC|NSC|SKC|CLR|NCD|M?\d{2}/|\d{3}V\d{3}|$))'
        vis_match = re.search(vis_pattern, text)
        
        if vis_match:
            vis_val = int(vis_match.group(1))
            result["visibility"] = vis_val
            
            if vis_val == 9999:
                result["visibility_description"] = "≥10公里"
            elif vis_val >= 8000:
                result["visibility_description"] = "很好"
            elif vis_val >= 5000:
                result["visibility_description"] = "良好"
            elif vis_val >= 3000:
                result["visibility_description"] = "中等"
            elif vis_val >= 1500:
                result["visibility_description"] = "较差"
            elif vis_val >= 800:
                result["visibility_description"] = "差"
            else:
                result["visibility_description"] = "很差"
    
    # ================== 温度/露点 ==================
    temp_match = re.search(r'\b(M?\d{2})/(M?\d{2})\b', text)
    if temp_match:
        t = temp_match.group(1)
        d = temp_match.group(2)
        result["temperature"] = -int(t[1:]) if t.startswith("M") else int(t)
        result["dewpoint"] = -int(d[1:]) if d.startswith("M") else int(d)
    
    # ================== 气压 ==================
    pressure_match = re.search(r'\bQ(\d{4})\b', text)
    if pressure_match:
        result["pressure_qnh"] = int(pressure_match.group(1))
    else:
        pressure_match_a = re.search(r'\bA(\d{4})\b', text)
        if pressure_match_a:
            inhg = int(pressure_match_a.group(1)) / 100
            result["pressure_qnh"] = round(inhg * 33.8639)
    
    # ================== 云层（修复版） ==================
    # NSC/SKC/CLR/NCD
    if re.search(r'\b(?:NSC|SKC|CLR|NCD)\b', text):
        nsc_type = re.search(r'\b(NSC|SKC|CLR|NCD)\b', text).group(1)
        desc_map = {
            "NSC": "无显著云",
            "SKC": "天空无云",
            "CLR": "晴空",
            "NCD": "无云被探测到"
        }
        result["clouds"].append({
            "amount": nsc_type,
            "height_m": 0,
            "description": desc_map.get(nsc_type, "无云")
        })
    
    # 云层: FEW005, SCT013, BKN021等
    cloud_matches = re.findall(r'\b(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?\b', text)
    for amt, h, cb in cloud_matches:
        ft = int(h) * 100
        m_height = round(ft * 0.3048)
        
        amount_desc = {
            "FEW": "少云 1-2/8",
            "SCT": "疏云 3-4/8",
            "BKN": "多云 5-7/8",
            "OVC": "满天云 8/8"
        }
        
        cloud_info = {
            "amount": amt,
            "height_m": m_height,
            "height_ft": ft,
            "description": amount_desc.get(amt, amt)
        }
        
        if cb == "CB":
            cloud_info["type"] = "积雨云"
        elif cb == "TCU":
            cloud_info["type"] = "浓积云"
        
        result["clouds"].append(cloud_info)
    
    # ================== 天气现象 ==================
    WEATHER_PATTERNS = {
        # 强度 + 类型组合
        r'\+TSRA': ('强雷雨', True, '大雨'),
        r'\-TSRA': ('弱雷雨', True, '小雨'),
        r'\bTSRA\b': ('雷雨', True, '中雨'),
        
        r'\+SHRA': ('强阵雨', True, '大雨'),
        r'\-SHRA': ('弱阵雨', True, '小雨'),
        r'\bSHRA\b': ('阵雨', True, '中雨'),
        
        r'\+RA': ('大雨', True, '大雨'),
        r'\-RA': ('小雨', True, '小雨'),
        r'\bRA\b': ('中雨', True, '中雨'),
        
        r'\+DZ': ('强毛毛雨', True, '小雨'),
        r'\-DZ': ('弱毛毛雨', True, '小雨'),
        r'\bDZ\b': ('毛毛雨', True, '小雨'),
        
        # 其他降水
        r'\+SN': ('大雪', False, None),
        r'\-SN': ('小雪', False, None),
        r'\bSN\b': ('中雪', False, None),
        
        # 雷暴
        r'\+TS': ('强雷暴', False, None),
        r'\bTS\b': ('雷暴', False, None),
        
        # 能见度障碍
        r'\bFG\b': ('雾', False, None),
        r'\bBR\b': ('薄雾', False, None),
        r'\bHZ\b': ('霾', False, None),
        r'\bMIFG\b': ('浅雾', False, None),
        r'\bBCFG\b': ('局部雾', False, None),
        r'\bVCFG\b': ('临近有雾', False, None),
        
        # 其他
        r'\bSQ\b': ('飑', False, None),
        r'\bFC\b': ('龙卷/漏斗云', False, None),
        r'\bSS\b': ('沙暴', False, None),
        r'\bDS\b': ('尘暴', False, None),
    }
    
    for pattern, (desc, israin, rainlevel) in WEATHER_PATTERNS.items():
        if re.search(pattern, text):
            if desc not in result["weather"]:
                result["weather"].append(desc)
            if israin:
                result["is_raining"] = True
                if result["rain_type"] is None:
                    result["rain_type"] = rainlevel
                elif rainlevel == '大雨' and result["rain_type"] != '大雨':
                    result["rain_type"] = rainlevel
    
    # NOSIG
    if re.search(r'\bNOSIG\b', text):
        result["weather"].append("无明显变化")
    
    return result


def format_metar_result(result: Dict) -> str:
    """格式化输出METAR解析结果"""
    lines = []
    lines.append("="*70)
    lines.append("METAR 报文解析结果")
    lines.append("="*70)
    
    if result.get("is_corrected"):
        lines.append("⚠️  [修正报]")
    
    lines.append(f"📄 原始: {result['raw']}")
    lines.append("-"*70)
    
    if result['station']:
        lines.append(f"📍 站号: {result['station']}")
    
    if result['obs_time']:
        day = result['obs_time'][:2]
        hour = result['obs_time'][2:4]
        minute = result['obs_time'][4:6]
        lines.append(f"🕐 时间: {day}日 {hour}:{minute} UTC")
    
    if result['wind_speed'] is not None:
        wind_info = f"💨 风: "
        if result['wind_direction'] is not None:
            wind_info += f"{result['wind_direction']:03d}° "
        else:
            wind_info += "VRB "
        wind_info += f"{result['wind_speed']}kt"
        if result['wind_gust']:
            wind_info += f" 阵风{result['wind_gust']}kt"
        if result['wind_variable']:
            wind_info += f" (变化:{result['wind_variable']})"
        lines.append(wind_info)
    
    if result['visibility'] is not None:
        lines.append(f"👁️  能见度: {result['visibility']}m ({result.get('visibility_description', '')})")
    
    if result['temperature'] is not None:
        lines.append(f"🌡️  温度: {result['temperature']}°C")
    if result['dewpoint'] is not None:
        lines.append(f"💧 露点: {result['dewpoint']}°C")
        if result['temperature'] is not None:
            spread = result['temperature'] - result['dewpoint']
            lines.append(f"   温露差: {spread}°C")
    
    if result['pressure_qnh']:
        lines.append(f"🔽 气压: {result['pressure_qnh']}hPa")
    
    if result['weather']:
        lines.append(f"🌤️  天气: {', '.join(result['weather'])}")
    
    if result['clouds']:
        lines.append("☁️  云层:")
        for cloud in result['clouds']:
            if cloud['height_m'] > 0:
                cloud_str = f"   {cloud['description']} - {cloud['height_m']}m ({cloud['height_ft']}ft)"
                if 'type' in cloud:
                    cloud_str += f" [{cloud['type']}]"
                lines.append(cloud_str)
            else:
                lines.append(f"   {cloud['description']}")
    
    lines.append("-"*70)
    
    if result['is_raining']:
        lines.append(f"🌧️  降雨: ✅ {result['rain_type']}")
    else:
        lines.append(f"🌧️  降雨: ❌ 无")
    
    lines.append("="*70)
    
    return "\n".join(lines)


# ============ 测试 ============
if __name__ == "__main__":
    # 使用用户提供的真实报文测试
    test_metars = [
        "Rx 210330Z METAR VVDB 210330Z 19003KT 120V240 8000 NSC 17/13 Q1026 NOSIG=",
        "Rx 210331Z METAR VVCR 210330Z 36012KT 6000 -RA FEW005 SCT013 BKN021 25/24",
        "METAR VVCS 211200Z 27015G25KT 9999 -RA FEW020 SCT100 28/24 Q1010 NOSIG=",
        "METAR VVCS 211500Z VRB03KT CAVOK 30/22 Q1012=",
    ]
    
    for i, metar in enumerate(test_metars, 1):
        print(f"\n测试 {i}:")
        result = parse_metar(metar)
        print(format_metar_result(result))
