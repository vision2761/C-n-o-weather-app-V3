# metar_parser_improved.py —— 增强版 METAR 报文解析模块
# 支持更多格式和边界情况，修复识别问题

import re
from typing import Dict, List, Optional

def parse_metar(text: str) -> Dict:
    """
    解析METAR报文
    
    Args:
        text: METAR报文文本（支持多行）
    
    Returns:
        解析结果字典
    """
    # 预处理：去除首尾空格，合并多行为一行，去除多余空格
    text = text.strip()
    text = " ".join(text.split())
    # 去除等号（报文结束标记）
    text = text.replace("=", "")
    
    result = {
        "raw": text,
        "station": None,
        "obs_time": None,
        "wind_direction": None,
        "wind_speed": None,
        "wind_gust": None,
        "wind_variable": None,  # 风向变化范围
        "visibility": None,
        "visibility_description": None,
        "temperature": None,
        "dewpoint": None,
        "pressure_qnh": None,  # QNH气压
        "is_raining": False,
        "rain_type": None,
        "weather": [],
        "clouds": [],
        "cavok": False,  # 天气晴好
        "is_corrected": False,  # 是否修正报
    }
    
    # ================== 检测修正报 ==================
    if re.search(r'\bCOR\b', text):
        result["is_corrected"] = True
    
    # ================== 站号识别（改进） ==================
    # 模式1: METAR 或 SPECI 后跟站号
    m_sta = re.search(r'\b(?:METAR|SPECI)\s+([A-Z]{4})\b', text)
    if m_sta:
        result["station"] = m_sta.group(1)
    else:
        # 模式2: 报文开头的4字母站号（排除常见关键词）
        excluded = {'METAR', 'SPECI', 'AUTO', 'CAVOK', 'NOSIG', 'TEMPO', 'BECMG'}
        words = text.split()
        for word in words:
            if len(word) == 4 and word.isupper() and word.isalpha() and word not in excluded:
                result["station"] = word
                break
    
    # ================== 报文时间 ==================
    # 格式: DDHHmmZ (日期时分)
    times = re.findall(r'\b(\d{6})Z\b', text)
    if times:
        result["obs_time"] = times[-1] + "Z"  # 取最后一个（主报时间）
    
    # ================== 风向风速 ==================
    # 格式: dddffKT 或 dddffGfmfmKT 或 VRBffKT 或 dddffMPS
    wind_match = re.search(r'\b(VRB|\d{3})(\d{2,3})(?:G(\d{2,3}))?(KT|MPS)\b', text)
    if wind_match:
        direction = wind_match.group(1)
        if direction != "VRB":
            result["wind_direction"] = int(direction)
        speed = int(wind_match.group(2))
        unit = wind_match.group(4)
        
        # 统一转换为KT（节）
        if unit == "MPS":
            speed = round(speed * 1.944)  # m/s 转 kt
        result["wind_speed"] = speed
        
        if wind_match.group(3):
            gust = int(wind_match.group(3))
            if unit == "MPS":
                gust = round(gust * 1.944)
            result["wind_gust"] = gust
    
    # 风向变化范围 (如: 270V330)
    var_match = re.search(r'\b(\d{3})V(\d{3})\b', text)
    if var_match:
        result["wind_variable"] = f"{var_match.group(1)}-{var_match.group(2)}"
    
    # ================== 能见度（改进，避免误匹配） ==================
    result["cavok"] = bool(re.search(r'\bCAVOK\b', text))
    
    if not result["cavok"]:
        # 模式1: 标准4位数字能见度（在温度前，在风后）
        # 必须确保不是云高、不是气压、不是温度
        vis_match = re.search(r'\b(0000|[0-9]{4})\b(?=\s+(?:[A-Z+\-]|FEW|SCT|BKN|OVC|SKC|CLR|NSC|M?\d{2}/|$))', text)
        if vis_match:
            vis_val = int(vis_match.group(1))
            # 排除明显是云高的值（通常是3位数乘以100）和气压值
            if vis_val != 1010 and vis_val != 1013:  # 排除常见气压值
                result["visibility"] = vis_val
                if vis_val == 9999:
                    result["visibility_description"] = "10公里或以上"
                elif vis_val >= 5000:
                    result["visibility_description"] = "良好"
                elif vis_val >= 3000:
                    result["visibility_description"] = "中等"
                elif vis_val >= 1000:
                    result["visibility_description"] = "较差"
                else:
                    result["visibility_description"] = "很差"
        
        # 模式2: 9999（最大能见度）
        if re.search(r'\b9999\b', text):
            result["visibility"] = 9999
            result["visibility_description"] = "10公里或以上"
    else:
        result["visibility_description"] = "CAVOK - 天气晴好"
    
    # ================== 温度 / 露点 ==================
    # 格式: TT/DD 或 Mxx/Mxx (M表示负温度)
    # 确保在QNH前面，避免误匹配
    temp_match = re.search(r'\b(M?\d{2})/(M?\d{2})\b(?=.*(?:Q\d{4}|A\d{4}|$))', text)
    if temp_match:
        t = temp_match.group(1)
        d = temp_match.group(2)
        result["temperature"] = -int(t[1:]) if t.startswith("M") else int(t)
        result["dewpoint"] = -int(d[1:]) if d.startswith("M") else int(d)
    
    # ================== 气压 QNH ==================
    # 格式: Qpppp (hPa) 或 Axxxx (inHg)
    pressure_match = re.search(r'\bQ(\d{4})\b', text)
    if pressure_match:
        result["pressure_qnh"] = int(pressure_match.group(1))
    else:
        # 美国格式 A2992 (inHg * 100)
        pressure_match_a = re.search(r'\bA(\d{4})\b', text)
        if pressure_match_a:
            inhg = int(pressure_match_a.group(1)) / 100
            # 转换为 hPa: 1 inHg = 33.8639 hPa
            result["pressure_qnh"] = round(inhg * 33.8639)
    
    # ================== 云层 ==================
    # 清空天空
    if re.search(r'\b(?:SKC|CLR|NSC|NCD)\b', text):
        result["clouds"].append({
            "amount": "SKC",
            "height_m": 0,
            "description": "天空无云"
        })
    else:
        # 云层格式: FEW020 SCT100 BKN250 OVC015CB
        cloud_matches = re.findall(r'\b(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?\b', text)
        for amt, h, cb in cloud_matches:
            ft = int(h) * 100
            m_height = round(ft * 0.3048)
            
            amount_desc = {
                "FEW": "少云(1-2/8)",
                "SCT": "疏云(3-4/8)", 
                "BKN": "多云(5-7/8)",
                "OVC": "阴天(8/8)"
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
    
    # ================== 天气现象（改进和扩展） ==================
    WEATHER_PATTERNS = {
        # 降水类型
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
        
        # 雷暴
        r'\+TS': ('强雷暴', False, None),
        r'\-TS': ('弱雷暴', False, None),
        r'\bTS\b': ('雷暴', False, None),
        
        # 能见度障碍
        r'\bFG\b': ('雾', False, None),
        r'\bBR\b': ('薄雾', False, None),
        r'\bHZ\b': ('霾', False, None),
        r'\bMIFG\b': ('浅雾', False, None),
        r'\bBCFG\b': ('局部雾', False, None),
        r'\bPRFG\b': ('部分雾', False, None),
        
        # 其他天气
        r'\bSQ\b': ('飑', False, None),
        r'\bFC\b': ('龙卷/漏斗云', False, None),
        r'\bSS\b': ('沙暴', False, None),
        r'\bDS\b': ('尘暴', False, None),
        r'\bVA\b': ('火山灰', False, None),
    }
    
    for pattern, (desc, israin, rainlevel) in WEATHER_PATTERNS.items():
        if re.search(pattern, text):
            if desc not in result["weather"]:  # 避免重复
                result["weather"].append(desc)
            if israin:
                result["is_raining"] = True
                # 优先保留更强的雨型
                if result["rain_type"] is None or (rainlevel == '大雨' and result["rain_type"] != '大雨'):
                    result["rain_type"] = rainlevel
    
    # ================== 特殊情况处理 ==================
    # NSW (No Significant Weather) - 无重要天气
    if re.search(r'\bNSW\b', text):
        result["weather"].append("无重要天气")
    
    # NOSIG (No Significant Change) - 无明显变化
    if re.search(r'\bNOSIG\b', text):
        result["weather"].append("无明显变化趋势")
    
    return result


def format_metar_result(result: Dict) -> str:
    """
    格式化输出METAR解析结果
    
    Args:
        result: parse_metar 返回的结果字典
    
    Returns:
        格式化的字符串
    """
    lines = []
    lines.append("="*70)
    lines.append("METAR 报文解析结果")
    lines.append("="*70)
    
    if result.get("is_corrected"):
        lines.append("⚠️  [修正报]")
    
    lines.append(f"📄 原始报文: {result['raw']}")
    lines.append("-"*70)
    
    if result['station']:
        lines.append(f"📍 站号: {result['station']}")
    
    if result['obs_time']:
        day = result['obs_time'][:2]
        hour = result['obs_time'][2:4]
        minute = result['obs_time'][4:6]
        lines.append(f"🕐 观测时间: {day}日 {hour}:{minute} UTC")
    
    if result['wind_speed'] is not None:
        wind_info = f"💨 风: "
        if result['wind_direction'] is not None:
            wind_info += f"{result['wind_direction']}° "
        else:
            wind_info += "变化风向 "
        wind_info += f"{result['wind_speed']} kt"
        if result['wind_gust']:
            wind_info += f" (阵风 {result['wind_gust']} kt)"
        if result['wind_variable']:
            wind_info += f" [风向变化: {result['wind_variable']}]"
        lines.append(wind_info)
    
    if result['visibility'] is not None:
        lines.append(f"👁️  能见度: {result['visibility']} m ({result.get('visibility_description', '')})")
    elif result['cavok']:
        lines.append(f"👁️  能见度: CAVOK (天气晴好，能见度≥10km)")
    
    if result['temperature'] is not None:
        lines.append(f"🌡️  温度: {result['temperature']}°C")
    if result['dewpoint'] is not None:
        lines.append(f"💧 露点: {result['dewpoint']}°C")
        if result['temperature'] is not None:
            spread = result['temperature'] - result['dewpoint']
            lines.append(f"   温露差: {spread}°C")
    
    if result['pressure_qnh']:
        lines.append(f"🔽 气压: {result['pressure_qnh']} hPa")
    
    if result['weather']:
        lines.append(f"🌤️  天气现象: {', '.join(result['weather'])}")
    
    if result['clouds']:
        lines.append("☁️  云层:")
        for cloud in result['clouds']:
            cloud_str = f"   {cloud['description']}"
            if 'height_ft' in cloud:
                cloud_str += f" - {cloud['height_m']}m ({cloud['height_ft']}ft)"
            if 'type' in cloud:
                cloud_str += f" [{cloud['type']}]"
            lines.append(cloud_str)
    
    lines.append("-"*70)
    
    if result['is_raining']:
        lines.append(f"🌧️  降雨状态: ✅ 正在降雨")
        lines.append(f"☔ 雨型: {result['rain_type']}")
    else:
        lines.append(f"🌧️  降雨状态: ❌ 无降雨")
    
    lines.append("="*70)
    
    return "\n".join(lines)


# ============ 测试代码 ============
if __name__ == "__main__":
    # 测试用例
    test_metars = [
        "METAR VVCS 211200Z 27015G25KT 9999 -RA FEW020 SCT100 28/24 Q1010 NOSIG=",
        "SPECI VVCS 211330Z 09012KT 3000 TSRA BKN015CB 26/23 Q1008=",
        "METAR VVCS 211500Z VRB03KT CAVOK 30/22 Q1012=",
        "METAR VVCS 211800Z 28018G30KT 250V310 2000 +SHRA BKN012 OVC025CB 24/22 Q1009=",
        "METAR VVCS 212100Z 00000KT 0800 FG SKC M02/M05 Q1020=",
    ]
    
    for i, metar in enumerate(test_metars, 1):
        print(f"\n\n{'='*70}")
        print(f"测试用例 {i}")
        print(f"{'='*70}")
        result = parse_metar(metar)
        print(format_metar_result(result))
