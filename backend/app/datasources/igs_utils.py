"""IGS数据解析工具（从原项目迁移并规范化）"""

import numpy as np
import gzip
import os
import datetime
from typing import Optional, Dict, List, Tuple
from pathlib import Path


# ============================================================
# ECEF → 经纬度
# ============================================================
def ecef_to_llh(x, y, z):
    a, e2 = 6378137.0, 0.00669437999014
    lon = np.degrees(np.arctan2(y, x))
    p = np.sqrt(x**2 + y**2)
    lat = np.arctan2(z, p * (1 - e2))
    for _ in range(5):
        N = a / np.sqrt(1 - e2 * np.sin(lat)**2)
        H = p / np.cos(lat) - N
        lat = np.arctan2(z, p * (1 - e2 * N / (N + H)))
    return np.degrees(lat), lon, H


# ============================================================
# GPT3 简化版气象参数
# ============================================================
def gpt3_pressure_temp(lat, lon, H, doy):
    lat_rad = np.radians(lat)
    lat_abs = abs(lat)
    P0 = 1013.25 * (1 - 0.0026 * np.cos(2 * lat_rad))
    season_P = 2.0 * np.cos(2 * np.pi * (doy - 28) / 365.25)
    P = (P0 + season_P * (1 - 0.3 * lat_abs / 90)) * np.exp(-H / 8400)
    T0 = 288.15 - 0.5 * lat_abs
    season_T = 15.0 * np.cos(2 * np.pi * (doy - 200) / 365.25)
    T = T0 + season_T * (1 - 0.4 * lat_abs / 90) - 0.0065 * H
    T_c = T - 273.15
    e_sat = 6.112 * np.exp(17.62 * T_c / (243.12 + T_c))
    rh = (0.7 - 0.25 * lat_abs / 90 + 0.15 * np.cos(2 * np.pi * (doy - 190) / 365.25))
    rh = np.clip(rh * np.exp(-H / 2000), 0.1, 1.0)
    e = e_sat * rh
    return P, T, e


# ============================================================
# Saastamoinen 模型
# ============================================================
def saastamoinen_ztd(P, T, e, lat, H):
    lat_rad = np.radians(lat)
    f_lat_H = 1 - 0.00266 * np.cos(2 * lat_rad) - 2.8e-7 * H
    ZHD = 0.0022768 * P / f_lat_H
    ZWD = 0.002277 * (1255 / T + 0.05) * e
    return ZHD + ZWD


# ============================================================
# IGS .TRO 文件解析
# ============================================================
def parse_tro_file(filepath: str) -> Optional[Dict]:
    """解析 IGS .TRO (对流层 SINEX) 文件"""
    try:
        if filepath.endswith('.gz'):
            with gzip.open(filepath, 'rt', encoding='utf-8', errors='replace') as f:
                content = f.read()
        else:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
    except Exception:
        return None

    lines = content.split('\n')
    result = {'epochs': []}
    station_code = os.path.basename(filepath).split('_')[4][:4]
    x = y = z = None

    # 解析站点坐标
    in_coord = False
    for line in lines:
        if line.startswith('+TROP/STA_COORDINATES'):
            in_coord = True; continue
        if line.startswith('-TROP/STA_COORDINATES'):
            in_coord = False; continue
        if in_coord and line.startswith(' ' + station_code) and not line.startswith('*'):
            parts = line.split()
            if len(parts) >= 4:
                try: x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                except ValueError: pass

    # 解析 SITE/ID
    in_site = False
    for line in lines:
        if line.startswith('+SITE/ID'):
            in_site = True; continue
        if line.startswith('-SITE/ID'):
            in_site = False; continue
        if in_site and station_code in line and not line.startswith('*'):
            parts = line.split()
            try:
                if len(parts) >= 12:
                    lon_d = float(parts[5]); lon_m = float(parts[6]); lon_s = float(parts[7])
                    lat_d = float(parts[8]); lat_m = float(parts[9]); lat_s = float(parts[10])
                    result['lon'] = lon_d + lon_m/60 + lon_s/3600
                    result['lat'] = lat_d + lat_m/60 + lat_s/3600
                    result['H'] = float(parts[11])
            except (ValueError, IndexError): pass

    if x is not None:
        lat, lon, H = ecef_to_llh(x, y, z)
        result['lat'] = lat; result['lon'] = lon; result['H'] = H

    result['station'] = station_code

    # 解析 ZTD 数据
    in_sol = False
    for line in lines:
        if line.startswith('+TROP/SOLUTION'):
            in_sol = True; continue
        if line.startswith('-TROP/SOLUTION'):
            in_sol = False; continue
        if in_sol and not line.startswith('*'):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    epoch_str = parts[1]
                    yr, doy, sec = epoch_str.split(':')
                    ztd = float(parts[2]) / 1000.0
                    sigma = float(parts[3]) / 1000.0 if len(parts) > 3 else 0.005
                    gn = float(parts[4]) / 1000.0 if len(parts) > 4 else 0
                    ge = float(parts[5]) / 1000.0 if len(parts) > 5 else 0
                    result['epochs'].append({
                        'year': int(yr), 'doy': int(doy),
                        'hour': int(sec) / 3600.0,
                        'ztd': ztd, 'sigma': sigma, 'gn': gn, 'ge': ge,
                    })
                except (ValueError, IndexError): continue

    return result if result['epochs'] else None


# ============================================================
# RINEX 气象文件解析 (.25m)
# ============================================================
def parse_rinex_met(filepath: str) -> Optional[Dict]:
    try:
        if filepath.endswith('.gz'):
            with gzip.open(filepath, 'rt', encoding='utf-8', errors='replace') as f:
                content = f.read()
        else:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
    except Exception:
        return None

    lines = content.split('\n')
    met_data = {}
    in_header = True

    for line in lines:
        if 'END OF HEADER' in line:
            in_header = False; continue
        if in_header or len(line) < 20: continue
        parts = line.split()
        if len(parts) < 8: continue
        try:
            yr = int(parts[0]); mo = int(parts[1]); day = int(parts[2])
            hh = int(parts[3]); mm = int(parts[4]); ss = int(parts[5])
            PR = float(parts[6]); TD = float(parts[7]); HR = float(parts[8])
            e_sat = 6.112 * np.exp(17.62 * TD / (243.12 + TD))
            e_val = e_sat * HR / 100.0
            doy = datetime.date(2000 + yr, mo, day).timetuple().tm_yday
            key = (2000 + yr, doy, hh * 3600 + mm * 60 + ss)
            met_data[key] = {'P': PR, 'T': TD + 273.15, 'e': e_val}
        except (ValueError, IndexError): continue

    return met_data if met_data else None


# ============================================================
# 批量加载对流层数据并构建特征矩阵
# ============================================================
def load_troposphere_dataset(
    tro_files: List[str],
    met_files: Optional[List[str]] = None,
) -> Tuple[np.ndarray, np.ndarray, dict]:
    """加载 TRO + 气象数据，构建特征矩阵和 ZTD 目标值

    Returns:
        X: (n, 9) 特征矩阵 [lat, H, sin_doy, cos_doy, sin_hour, cos_hour, P, T, e]
        y: (n,) ZTD 目标值
        meta: 元信息字典
    """
    # 1. 加载气象数据
    met_db = {}
    if met_files:
        for f in met_files:
            basename = os.path.basename(f)
            station = basename[:4].upper()
            met_data = parse_rinex_met(f)
            if met_data:
                for key, val in met_data.items():
                    met_db[(station,) + key] = val

    # 按站点+DOY 索引气象
    met_by_station_doy = {}
    for (mst, myr, mdoy, msec), mval in met_db.items():
        key = (mst, myr, mdoy)
        met_by_station_doy.setdefault(key, []).append((msec, mval))

    # 2. 解析 TRO 文件
    all_records = []
    for f in tro_files:
        parsed = parse_tro_file(f)
        if parsed is None or 'lat' not in parsed:
            continue
        st = parsed['station']
        lat = parsed['lat']
        H_val = parsed.get('H', 0)
        for ep in parsed['epochs']:
            yr = ep['year']
            if yr < 100: yr += 2000
            doy = ep['doy']
            sec = int(ep['hour'] * 3600)
            ztd = ep['ztd']

            # 匹配实测气象
            P_real, T_real, e_real = gpt3_pressure_temp(lat, 110, H_val, doy)
            met_records = met_by_station_doy.get((st, yr, doy), [])
            best_dist = 9999
            for msec, mval in met_records:
                dist = abs(msec - sec)
                if dist < 900 and dist < best_dist:
                    best_dist = dist
                    P_real, T_real, e_real = mval['P'], mval['T'], mval['e']

            all_records.append({
                'station': st, 'lat': lat, 'H': H_val,
                'doy': doy, 'hour': ep['hour'], 'ztd': ztd,
                'P': P_real, 'T': T_real, 'e': e_real,
            })

    if not all_records:
        raise ValueError("未能从 TRO 文件中提取到有效 ZTD 数据")

    # 3. 构建特征矩阵
    n = len(all_records)
    lat_arr = np.array([r['lat'] for r in all_records])
    H_arr = np.array([r['H'] for r in all_records])
    doy_arr = np.array([r['doy'] for r in all_records])
    hour_arr = np.array([r['hour'] for r in all_records])
    P_arr = np.array([r['P'] for r in all_records])
    T_arr = np.array([r['T'] for r in all_records])
    e_arr = np.array([r['e'] for r in all_records])
    y = np.array([r['ztd'] for r in all_records])

    doy_rad = 2 * np.pi * (doy_arr - 1) / 365.25
    hour_rad = 2 * np.pi * hour_arr / 24.0

    X = np.column_stack([
        lat_arr, H_arr,
        np.sin(doy_rad), np.cos(doy_rad),
        np.sin(hour_rad), np.cos(hour_rad),
        P_arr, T_arr, e_arr,
    ])

    meta = {
        'stations': sorted(set(r['station'] for r in all_records)),
        'n_total': n,
        'feature_names': ['lat', 'H', 'sin_doy', 'cos_doy', 'sin_hour', 'cos_hour', 'P', 'T', 'e'],
        'target_name': 'ZTD',
        'all_records': all_records,
    }

    return X, y, meta


# ============================================================
# 下载 IGS 数据（通过匿名 FTP）
# ============================================================
IGS_CHINA_STATIONS = [
    {'name': 'BJFS', 'lat': 39.6086, 'lon': 115.8924, 'H': 87.4},
    {'name': 'SHAO', 'lat': 31.0996, 'lon': 121.2004, 'H': 22.6},
    {'name': 'URUM', 'lat': 43.5903, 'lon': 87.2569, 'H': 858.9},
    {'name': 'WUHN', 'lat': 30.5317, 'lon': 114.3573, 'H': 27.4},
    {'name': 'TWTF', 'lat': 24.9536, 'lon': 121.1645, 'H': 202.0},
    {'name': 'CHAN', 'lat': 43.7904, 'lon': 125.4435, 'H': 273.0},
]

CDDIS_TROPO_URL = "https://cddis.nasa.gov/archive/gnss/products/troposphere/zpd"
