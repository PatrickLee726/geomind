"""GNSS基线网平差 Pipeline

蒙特卡洛模拟 + ML注意力定权 vs 经典四种方案对比

核心思路（对应PPT"人工经验定权→数据智能定权"）：
  - 同一GNSS网形，蒙特卡洛生成N组含粗差+天线偏差的观测
  - ML从基线特征(长度/残差/站级统计)学习每条基线的可靠性权重
  - 测试集对比: 等权 / 协方差定权 / 抗差估计 / ML智能定权
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Tuple

from ..core.base import Pipeline, AdjustConfig, PipelineResult, StepResult, DataSource, DataSourceType, DataProfile
from ..config import RESULT_DIR
import pandas as pd

plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def _ensure_torch():
    global torch, nn
    try:
        import torch
        import torch.nn as nn
        return True
    except ImportError:
        return False


# ================================================================
# GNSS 网形模拟（从 classical/gnss_network.py 提炼）
# ================================================================

@dataclass
class Station:
    name: str
    x: float; y: float; z: float
    fixed: bool = False


@dataclass
class Baseline:
    from_station: str
    to_station: str
    dx: float; dy: float; dz: float
    cov_xx: float; cov_yy: float; cov_zz: float
    cov_xy: float = 0.0; cov_xz: float = 0.0; cov_yz: float = 0.0

    @property
    def length(self):
        return np.sqrt(self.dx**2 + self.dy**2 + self.dz**2)

    @property
    def weight_matrix(self):
        mat = np.array([
            [self.cov_xx, self.cov_xy, self.cov_xz],
            [self.cov_xy, self.cov_yy, self.cov_yz],
            [self.cov_xz, self.cov_yz, self.cov_zz],
        ])
        return np.linalg.inv(mat)


class GNSSNetwork:
    def __init__(self, stations, baselines):
        self.stations = stations
        self.baselines = baselines

    @property
    def unknown_stations(self):
        return [s for s in self.stations if not s.fixed]

    @property
    def known_stations(self):
        return [s for s in self.stations if s.fixed]

    def _station_idx(self, name, unknowns):
        for i, s in enumerate(unknowns):
            if s.name == name:
                return i
        return None

    def build_design_matrix(self):
        n_unknown = len(self.unknown_stations)
        n_bl = len(self.baselines)
        m = 3 * n_bl
        unknowns = self.unknown_stations
        name_to_idx = {s.name: i for i, s in enumerate(unknowns)}

        B = np.zeros((m, 3 * n_unknown))
        P = np.zeros((m, m))
        l = np.zeros((m, 1))

        for k, bl in enumerate(self.baselines):
            row_start = 3 * k
            row_end = row_start + 3
            obs = np.array([[bl.dx], [bl.dy], [bl.dz]])

            if bl.from_station in name_to_idx:
                col_f = name_to_idx[bl.from_station]
                B[row_start:row_end, 3*col_f:3*(col_f+1)] = -np.eye(3)
            if bl.to_station in name_to_idx:
                col_t = name_to_idx[bl.to_station]
                B[row_start:row_end, 3*col_t:3*(col_t+1)] = np.eye(3)

            l_comp = np.zeros((3, 1))
            for role, sign in [('from', -1), ('to', 1)]:
                st_name = getattr(bl, f'{role}_station')
                if st_name not in name_to_idx:
                    for st in self.known_stations:
                        if st.name == st_name:
                            coords = np.array([[st.x], [st.y], [st.z]])
                            l_comp += sign * coords
                            break
            l[row_start:row_end] = obs - l_comp
            P[row_start:row_end, row_start:row_end] = bl.weight_matrix

        return B, P, l


def simulate_gnss_network(n_stations=8, n_baselines=15, sigma_baseline=0.005,
                          outlier_ratio=0.0, seed=42):
    """生成模拟GNSS控制网"""
    rng = np.random.default_rng(seed)
    total = n_stations

    angles = np.sort(rng.uniform(0, 2*np.pi, total))
    radii = rng.uniform(500, 5000, total)
    all_names = [chr(65+i) for i in range(total)]
    all_coords = np.column_stack([
        radii * np.cos(angles),
        radii * np.sin(angles),
        rng.uniform(-50, 50, total),
    ])

    stations = [Station(all_names[0], *all_coords[0], fixed=True)]
    for i in range(1, total):
        stations.append(Station(all_names[i], *all_coords[i], fixed=False))

    baselines = []
    connected = {all_names[0]}

    for i in range(1, total):
        name = all_names[i]
        partner = rng.choice(list(connected))
        _add_bl(baselines, stations, partner, name, rng, sigma_baseline, outlier_ratio)
        connected.add(name)

    while len(baselines) < n_baselines:
        i, j = rng.choice(total, size=2, replace=False)
        existing = {frozenset([bl.from_station, bl.to_station]) for bl in baselines}
        if frozenset([all_names[i], all_names[j]]) in existing:
            continue
        _add_bl(baselines, stations, all_names[i], all_names[j], rng, sigma_baseline, outlier_ratio)

    network = GNSSNetwork(stations, baselines)
    true_coords = np.array([[s.x, s.y, s.z] for s in stations[1:]])
    return network, true_coords


def _add_bl(baselines, stations, from_name, to_name, rng, sigma, outlier_ratio):
    sf = next(s for s in stations if s.name == from_name)
    st = next(s for s in stations if s.name == to_name)
    true = [st.x - sf.x, st.y - sf.y, st.z - sf.z]
    length = np.sqrt(sum(v**2 for v in true))
    sigma_comp = sigma + 1e-6 * length
    is_outlier = rng.random() < outlier_ratio
    scale = rng.uniform(5, 20) * sigma_comp if is_outlier else 1.0
    cov_diag = (sigma_comp * scale) ** 2
    corr = rng.uniform(-0.3, 0.3)

    baselines.append(Baseline(
        from_station=from_name, to_station=to_name,
        dx=true[0] + rng.normal(0, sigma_comp * scale),
        dy=true[1] + rng.normal(0, sigma_comp * scale),
        dz=true[2] + rng.normal(0, sigma_comp * scale),
        cov_xx=cov_diag, cov_yy=cov_diag * rng.uniform(0.8, 1.2),
        cov_zz=cov_diag * rng.uniform(0.8, 1.2),
        cov_xy=corr * cov_diag * 0.3, cov_xz=corr * cov_diag * 0.2,
        cov_yz=corr * cov_diag * 0.25,
    ))


# ================================================================
# 从上传CSV构建GNSS网形
# ================================================================

def build_network_from_csv(filepath: str, fixed_station: str = None):
    """从CSV上传的基线观测数据构建GNSS网形

    CSV列: from_station, to_station, dx, dy, dz [, std_dx, std_dy, std_dz]
    自动检测列名（也支持 from/to/dx/dy/dz/std 简写）。
    固定站默认用第一列第一个出现的站名。
    """
    df = pd.read_csv(filepath)
    cols = [c.strip().lower() for c in df.columns]

    # 自动检测列映射
    col_map = _detect_gnss_columns(cols)

    rows = []
    for _, row in df.iterrows():
        from_st = str(row[col_map['from']])
        to_st = str(row[col_map['to']])
        dx = float(row[col_map['dx']])
        dy = float(row[col_map['dy']])
        dz = float(row[col_map['dz']])
        std_dx = float(row[col_map['std_dx']]) if col_map['std_dx'] is not None else 0.005
        std_dy = float(row[col_map['std_dy']]) if col_map['std_dy'] is not None else 0.005
        std_dz = float(row[col_map['std_dz']]) if col_map['std_dz'] is not None else 0.005
        rows.append((from_st, to_st, dx, dy, dz, std_dx, std_dy, std_dz))

    # 识别所有站点
    all_stations = set()
    for r in rows:
        all_stations.add(r[0])
        all_stations.add(r[1])

    station_order = list(all_stations)
    # 固定站
    if fixed_station and fixed_station in all_stations:
        ref_name = fixed_station
    else:
        ref_name = rows[0][0]  # 第一个基线的 from 站作为固定站

    # 用第一遍平差计算参考坐标
    # 先给近似坐标
    approx = {ref_name: np.array([0.0, 0.0, 0.0])}
    # 传播：BFS 从固定站通过基线传播坐标
    graph = {}
    for r in rows:
        graph.setdefault(r[0], []).append((r[1], np.array([r[2], r[3], r[4]])))
        graph.setdefault(r[1], []).append((r[0], -np.array([r[2], r[3], r[4]])))

    visited = {ref_name}
    queue = [ref_name]
    while queue:
        cur = queue.pop(0)
        for nbr, vec in graph.get(cur, []):
            if nbr not in visited:
                visited.add(nbr)
                approx[nbr] = approx[cur] + vec
                queue.append(nbr)

    # 创建 Station 对象
    stations = []
    for name in station_order:
        coord = approx.get(name, np.array([0.0, 0.0, 0.0]))
        stations.append(Station(name=name, x=coord[0], y=coord[1], z=coord[2],
                                fixed=(name == ref_name)))

    # 创建 Baseline 对象
    baselines = []
    for r in rows:
        baselines.append(Baseline(
            from_station=r[0], to_station=r[1],
            dx=r[2], dy=r[3], dz=r[4],
            cov_xx=r[5]**2, cov_yy=r[6]**2, cov_zz=r[7]**2,
        ))

    network = GNSSNetwork(stations, baselines)

    # 用经典平差计算参考坐标
    obs_vec = np.array([[bl.dx, bl.dy, bl.dz] for bl in baselines])
    cov_vec = np.array([
        ([bl.cov_xx, bl.cov_yy, bl.cov_zz]
         if hasattr(bl, 'cov_xx') else [0.005**2, 0.005**2, 0.005**2])
        for bl in baselines
    ])
    ref_coords = _classical_adjust(obs_vec, cov_vec, network)

    return network, ref_coords, rows


def _detect_gnss_columns(cols: list) -> dict:
    """自动检测GNSS CSV列名"""
    result = {}
    # from station
    for candidate in ['from_station', 'from', 'from_st', 'station_from', 'station_a', '站1', '起点']:
        if candidate in cols:
            result['from'] = cols.index(candidate)
            break
    # to station
    for candidate in ['to_station', 'to', 'to_st', 'station_to', 'station_b', '站2', '终点']:
        if candidate in cols:
            result['to'] = cols.index(candidate)
            break
    # dx, dy, dz
    for key, candidates in [
        ('dx', ['dx', 'deltax', 'delta_x', 'dx_m', '△X']),
        ('dy', ['dy', 'deltay', 'delta_y', 'dy_m', '△Y']),
        ('dz', ['dz', 'deltaz', 'delta_z', 'dz_m', '△Z']),
    ]:
        for c in candidates:
            if c in cols:
                result[key] = cols.index(c)
                break
    # std columns (optional)
    for key, candidates in [
        ('std_dx', ['std_dx', 'stdx', 'std_x', 'sigma_dx', 'σx']),
        ('std_dy', ['std_dy', 'stdy', 'std_y', 'sigma_dy', 'σy']),
        ('std_dz', ['std_dz', 'stdz', 'std_z', 'sigma_dz', 'σz']),
    ]:
        result[key] = None
        for c in candidates:
            if c in cols:
                result[key] = cols.index(c)
                break

    for required in ['from', 'to', 'dx', 'dy', 'dz']:
        if required not in result:
            raise ValueError(f"CSV缺少必要列: {required}。需要的列: from/to/dx/dy/dz")

    return result


# ================================================================
# Pipeline 实现
# ================================================================

class GNSSNetworkPipeline(Pipeline):
    """GNSS基线网平差 —— 经典 vs ML智能定权"""

    @property
    def case_id(self) -> str:
        return "gnss"

    @property
    def case_name(self) -> str:
        return "GNSS基线网平差"

    @property
    def description(self) -> str:
        return (
            "蒙特卡洛模拟GNSS基线向量网。对比经典等权/协方差定权/抗差估计 "
            "与ML注意力机制智能定权。ML从基线几何特征和残差模式中学习每条基线的"
            "可靠性权重，自动识别粗差和天线相位中心偏差。"
        )

    def config_schema(self):
        return {
            "type": "object",
            "title": "GNSS基线网实验配置",
            "properties": {
                "n_stations": {
                    "type": "integer", "title": "测站数",
                    "default": 8, "minimum": 4, "maximum": 20,
                    "description": "GNSS网形中的总测站数（含1个已知点）",
                },
                "n_baselines": {
                    "type": "integer", "title": "基线数",
                    "default": 15, "minimum": 5, "maximum": 30,
                    "description": "独立基线向量总数",
                },
                "sigma_baseline": {
                    "type": "number", "title": "基线中误差 (m)",
                    "default": 0.005, "minimum": 0.001, "maximum": 0.05,
                    "description": "基线观测的标称精度",
                },
                "outlier_ratio": {
                    "type": "number", "title": "粗差比例",
                    "default": 0.35, "minimum": 0.0, "maximum": 0.7,
                    "description": "每组观测中粗差基线的大致比例",
                },
                "antenna_bias_prob": {
                    "type": "number", "title": "天线偏差概率",
                    "default": 0.30, "minimum": 0.0, "maximum": 1.0,
                    "description": "随机天线相位中心偏差的发生概率",
                },
                "n_train_groups": {
                    "type": "integer", "title": "训练组数",
                    "default": 160, "minimum": 50, "maximum": 500,
                    "description": "蒙特卡洛采样数，用于训练ML模型",
                },
                "n_test_groups": {
                    "type": "integer", "title": "测试组数",
                    "default": 40, "minimum": 10, "maximum": 200,
                    "description": "独立测试组数，对比四种方案",
                },
                "ml_hidden_dim": {
                    "type": "integer", "title": "ML隐藏层维度",
                    "default": 64, "minimum": 32, "maximum": 256,
                },
                "ml_epochs": {
                    "type": "integer", "title": "训练轮数",
                    "default": 1000, "minimum": 200, "maximum": 3000,
                },
                "ml_learning_rate": {
                    "type": "number", "title": "学习率",
                    "default": 0.001, "minimum": 0.0001, "maximum": 0.01,
                },
            },
        }

    def run(
        self,
        data_source: DataSource,
        config: AdjustConfig,
        progress_callback: Optional[Callable] = None,
    ) -> PipelineResult:
        result = PipelineResult(case_id=self.case_id)
        job_dir = self._make_job_dir()

        def log(msg, step="info"):
            print(f"[GNSS] {msg}")
            if progress_callback:
                progress_callback({"step": step, "message": msg})

        p = config.params

        # ========================================================
        # Step 1: 生成/加载GNSS网形
        # ========================================================
        use_uploaded = (data_source is not None and data_source.source_type.value != 'null')
        csv_rows = None  # 上传模式时存储原始CSV数据

        if use_uploaded:
            log("加载上传的基线数据...", "setup")
            try:
                csv_path = str(getattr(data_source, 'filepath', ''))
                if not csv_path or not os.path.exists(csv_path):
                    raise ValueError(f"文件不存在: {csv_path}")
                base_network, true_coords, csv_rows = build_network_from_csv(
                    csv_path,
                    fixed_station=p.get('fixed_station'),
                )
                log(f"  从上传数据构建网形: {len(base_network.baselines)}条基线, "
                    f"{len(base_network.stations)}个站点")
            except Exception as e:
                result.summary = f"上传数据解析失败: {e}"
                result.steps.append(StepResult(name="数据加载", status="failed", error=str(e)))
                return result
        else:
            log("生成GNSS网形...", "setup")
            base_network, true_coords = simulate_gnss_network(
                n_stations=p.get('n_stations', 8),
                n_baselines=p.get('n_baselines', 15),
                sigma_baseline=p.get('sigma_baseline', 0.005),
                outlier_ratio=0.0,
                seed=42,
            )

        # ========================================================
        # Step 2: 计算基线特征 & 采样
        # ========================================================
        n_bl = len(base_network.baselines)
        n_unknown = len(base_network.unknown_stations)
        n_known = len(base_network.known_stations)

        true_bl_vectors = np.zeros((n_bl, 3))
        if use_uploaded:
            # 用平差后的参考坐标回填到Station，再反算几何一致的基线向量
            unknown_stations = [s for s in base_network.stations if not s.fixed]
            for idx, s in enumerate(unknown_stations):
                s.x = true_coords[3 * idx]
                s.y = true_coords[3 * idx + 1]
                s.z = true_coords[3 * idx + 2]
        for i, bl in enumerate(base_network.baselines):
            sf = next(s for s in base_network.stations if s.name == bl.from_station)
            st = next(s for s in base_network.stations if s.name == bl.to_station)
            true_bl_vectors[i] = [st.x - sf.x, st.y - sf.y, st.z - sf.z]

        bl_lengths = np.sqrt(np.sum(true_bl_vectors**2, axis=1))
        bl_sigma = 0.005 + 1e-6 * bl_lengths

        station_names = [s.name for s in base_network.stations]
        log(f"  网形: {n_bl}条基线, {n_known}个已知点 + {n_unknown}个待定点")
        log(f"  基线长度: {bl_lengths.min():.0f}~{bl_lengths.max():.0f}m")

        result.steps.append(StepResult(
            name="网形生成", status="done",
            metrics={
                "基线数": n_bl, "已知点": n_known, "待定点": n_unknown,
                "基线长度(m)": f"{bl_lengths.min():.0f}~{bl_lengths.max():.0f}",
                "测站": ", ".join(station_names),
            },
        ))

        # ========================================================
        # Step 2: 蒙特卡洛采样
        # ========================================================
        log("蒙特卡洛采样...", "sampling")
        n_train = p.get('n_train_groups', 160)
        n_test = p.get('n_test_groups', 40)
        outlier_ratio = p.get('outlier_ratio', 0.35)
        antenna_prob = p.get('antenna_bias_prob', 0.30)

        train_rng = np.random.default_rng(100)
        test_rng = np.random.default_rng(200)

        # ---- 采样函数（从原 example 提炼）----
        def generate_one(rng):
            obs = np.zeros((n_bl, 3))
            cov_diag = np.zeros((n_bl, 3))
            optimal_weight = np.ones(n_bl)
            problem_station = None

            if rng.random() < antenna_prob:
                unknown_names = [s.name for s in base_network.unknown_stations]
                problem_station = rng.choice(unknown_names)
                ant_bias = rng.uniform(0.015, 0.04)

            for i, bl in enumerate(base_network.baselines):
                sigma_i = bl_sigma[i]
                noise = rng.normal(0, sigma_i, 3)
                is_outlier = rng.random() < outlier_ratio
                if is_outlier:
                    signs = rng.choice([-1, 1], 3)
                    noise += signs * rng.uniform(5, 15) * sigma_i
                    optimal_weight[i] = 0.05
                has_ant_bias = (problem_station is not None and
                                bl.from_station == problem_station)
                if has_ant_bias:
                    noise[2] += ant_bias
                    optimal_weight[i] = 0.3
                obs[i] = true_bl_vectors[i] + noise
                cov_diag[i] = sigma_i ** 2

            return obs, cov_diag, optimal_weight

        # ---- 特征提取函数 ----
        def extract_features(obs, cov_diag, network):
            B, _, _ = network.build_design_matrix()
            n_bl_loc = len(network.baselines)
            n_unknown_loc = len(network.unknown_stations)
            # 等权初解
            x_init = _classical_adjust(obs, np.ones_like(cov_diag), network)
            l_vec = np.zeros((n_bl_loc * 3, 1))
            for i, bl in enumerate(network.baselines):
                l_vec[3*i:3*i+3, 0] = obs[i]
                unknowns = network.unknown_stations
                name_to_idx = {s.name: j for j, s in enumerate(unknowns)}
                for role, sign in [('from', -1), ('to', 1)]:
                    st_name = getattr(bl, f'{role}_station')
                    if st_name not in name_to_idx:
                        for s in network.known_stations:
                            if s.name == st_name:
                                coords = np.array([s.x, s.y, s.z])
                                l_vec[3*i:3*i+3, 0] -= sign * coords
            V_init = B @ x_init.reshape(-1, 1) - l_vec

            unknown_names = [s.name for s in network.unknown_stations]
            st_z_res = {name: [] for name in unknown_names}
            for i, bl in enumerate(network.baselines):
                vz = V_init[3*i+2, 0]
                if bl.from_station in st_z_res:
                    st_z_res[bl.from_station].append(vz)
                if bl.to_station in st_z_res:
                    st_z_res[bl.to_station].append(-vz)

            features = np.zeros((n_bl_loc, 14))
            for i, bl in enumerate(network.baselines):
                v = V_init[3*i:3*i+3, 0]
                features[i, 0] = bl_lengths[i] / 1000
                features[i, 1] = np.sqrt(cov_diag[i].mean()) * 1000
                features[i, 2] = np.linalg.norm(v) * 1000
                features[i, 3] = abs(v[0]) * 1000
                features[i, 4] = abs(v[1]) * 1000
                features[i, 5] = abs(v[2]) * 1000
                features[i, 6] = abs(obs[i, 0]) / 1000
                features[i, 7] = abs(obs[i, 1]) / 1000
                features[i, 8] = abs(obs[i, 2]) / 1000
                features[i, 9] = np.linalg.norm(v) / max(np.sqrt(cov_diag[i].mean()), 1e-12)
                from_z = np.mean(st_z_res.get(bl.from_station, [0])) * 1000
                to_z = np.mean(st_z_res.get(bl.to_station, [0])) * 1000
                features[i, 10] = from_z if bl.from_station in st_z_res else 0
                features[i, 11] = to_z if bl.to_station in st_z_res else 0
                global_z_mean = np.mean([np.mean(vv) for vv in st_z_res.values() if vv]) * 1000
                features[i, 12] = features[i, 10] - global_z_mean
                features[i, 13] = features[i, 11] - global_z_mean

            return features

        # 采样训练集
        X_train, y_train = [], []
        for _ in range(n_train):
            obs, cov, opt_w = generate_one(train_rng)
            feat = extract_features(obs, cov, base_network)
            X_train.append(feat)
            y_train.append(opt_w)
        X_train = np.array(X_train)
        y_train = np.array(y_train)

        # 采样测试集
        X_test, y_test, test_obs, test_cov = [], [], [], []
        for _ in range(n_test):
            obs, cov, opt_w = generate_one(test_rng)
            feat = extract_features(obs, cov, base_network)
            X_test.append(feat)
            y_test.append(opt_w)
            test_obs.append(obs)
            test_cov.append(cov)
        X_test = np.array(X_test)
        y_test = np.array(y_test)

        log(f"  训练: {n_train}组  测试: {n_test}组")
        log(f"  每组: {n_bl}条基线 × 14特征 → 1权重")

        result.steps.append(StepResult(
            name="蒙特卡洛采样", status="done",
            metrics={"训练组": n_train, "测试组": n_test, "粗差比例": round(outlier_ratio, 2)},
        ))

        # ========================================================
        # Step 3: 训练 ML
        # ========================================================
        log("训练 ML 智能定权器...", "ml")

        if not _ensure_torch():
            log("  [跳过] PyTorch 未安装", "ml")
            result.final_metrics = {"error": "PyTorch 未安装"}
            result.summary = "需要安装 PyTorch: py -m pip install torch"
            return result

        hidden_dim = p.get('ml_hidden_dim', 64)
        epochs = p.get('ml_epochs', 1000)
        lr = p.get('ml_learning_rate', 0.001)

        class WeightPredictor(nn.Module):
            def __init__(self, input_dim=14, hidden=64):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(input_dim, hidden), nn.ReLU(),
                    nn.Linear(hidden, hidden // 2), nn.ReLU(),
                    nn.Linear(hidden // 2, 1), nn.Sigmoid(),
                )

            def forward(self, x):
                batch, n_b, _ = x.shape
                return self.net(x.reshape(-1, x.shape[-1])).reshape(batch, n_b)

        X_tr = torch.as_tensor(X_train, dtype=torch.float32)
        Y_tr = torch.as_tensor(y_train, dtype=torch.float32)
        X_te = torch.as_tensor(X_test, dtype=torch.float32)

        model_w = WeightPredictor(input_dim=14, hidden=hidden_dim)
        optimizer = torch.optim.Adam(model_w.parameters(), lr=lr)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=50, min_lr=1e-5)

        for ep in range(epochs):
            model_w.train()
            pred = model_w(X_tr)
            loss = nn.MSELoss()(pred, Y_tr)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            scheduler.step(loss.item())

        model_w.eval()
        with torch.no_grad():
            ml_weights_all = model_w(X_te).numpy()

        log(f"  ML 训练完成 ({epochs} 轮)")

        result.steps.append(StepResult(
            name="ML训练", status="done",
            metrics={
                "隐藏层": f"{hidden_dim}→{hidden_dim//2}",
                "训练轮数": epochs,
                "学习率": lr,
            },
        ))

        # ========================================================
        # Step 4: 测试四种方案
        # ========================================================
        log("测试对比四种方案...", "evaluation")

        results = {'等权': [], '协方差定权': [], '抗差估计': [], 'ML智能定权': []}
        true_flat = true_coords.flatten()

        for k in range(n_test):
            obs_k = test_obs[k]
            cov_k = test_cov[k]

            x_eq = _classical_adjust(obs_k, np.ones_like(cov_k), base_network)
            results['等权'].append(np.sqrt(np.mean((x_eq - true_flat)**2)))

            x_cov = _classical_adjust(obs_k, cov_k, base_network)
            results['协方差定权'].append(np.sqrt(np.mean((x_cov - true_flat)**2)))

            x_robust = _robust_estimate(obs_k, cov_k, base_network)
            results['抗差估计'].append(np.sqrt(np.mean((x_robust - true_flat)**2)))

            ml_w = ml_weights_all[k]
            x_ml = _ml_weighted_adjust(obs_k, cov_k, base_network, ml_w)
            results['ML智能定权'].append(np.sqrt(np.mean((x_ml - true_flat)**2)))

        names = list(results.keys())
        summary_lines = [f"{'方法':<12s} {'平均RMSE':>10s}  {'中位数RMSE':>10s}"]
        for name in names:
            arr = np.array(results[name])
            summary_lines.append(
                f"  {name:<12s} {arr.mean()*1000:>8.2f} mm  {np.median(arr)*1000:>8.2f} mm")
        log("\n".join(summary_lines))

        # 最佳方案
        best_name = min(names, key=lambda n: np.mean(results[n]))
        best_val = np.mean(results[best_name]) * 1000
        ml_val = np.mean(results['ML智能定权']) * 1000
        equal_val = np.mean(results['等权']) * 1000
        log(f"  最佳: {best_name} ({best_val:.2f} mm)")

        # 胜率
        win_counts = {}
        for name in names:
            win_counts[name] = sum(
                1 for k in range(n_test)
                if results[name][k] <= min(results[n][k] for n in names)
            )

        result.final_metrics = {}
        for name in names:
            arr = np.array(results[name])
            result.final_metrics[name] = {
                "平均RMSE_mm": round(arr.mean() * 1000, 2),
                "中位数RMSE_mm": round(np.median(arr) * 1000, 2),
                "最优RMSE_mm": round(arr.min() * 1000, 2),
                "最差RMSE_mm": round(arr.max() * 1000, 2),
                "胜出次数": f"{win_counts[name]}/{n_test}",
            }

        imp = (equal_val - ml_val) / equal_val * 100
        result.summary = (
            f"GNSS基线网平差对比完成。\n"
            f"  等权:         {equal_val:.2f} mm\n"
            f"  ML智能定权:   {ml_val:.2f} mm\n"
            f"  ML提升:       {imp:.1f}%\n"
            f"  ML胜出:       {win_counts['ML智能定权']}/{n_test} 组\n"
            f"  测试组数:     {n_test}"
        )

        result.steps.append(StepResult(
            name="方案对比", status="done",
            metrics=result.final_metrics,
        ))

        # ========================================================
        # Step 5: 图表
        # ========================================================
        log("生成图表...", "charts")
        self._generate_charts(job_dir, results, names, n_test)
        charts = self._find_charts(job_dir)
        result.charts = charts
        result.steps.append(StepResult(
            name="图表生成", status="done", artifacts=charts,
        ))

        log("完成!", "done")
        return result

    def _make_job_dir(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = RESULT_DIR / f"gnss_{ts}"
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def _find_charts(self, job_dir):
        charts = {}
        for f in sorted(job_dir.glob("GNSS_*.png")):
            name = f.stem.replace("GNSS_", "") + ".png"
            charts[name] = str(f)
        return charts

    def _generate_charts(self, job_dir, results, names, n_test):
        colors = ['#4472C4', '#ED7D31', '#A5A5A5', '#70AD47']
        arr_data = {name: np.array(errs) * 1000 for name, errs in results.items()}

        # 图1: 平均RMSE柱状图
        fig, ax = plt.subplots(figsize=(8, 5))
        means = [arr_data[n].mean() for n in names]
        bars = ax.bar(names, means, color=colors, edgecolor='white', linewidth=0.8)
        for bar, val in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f'{val:.1f} mm', ha='center', fontsize=11, fontweight='bold')
        best_idx = means.index(min(means))
        bars[best_idx].set_edgecolor('#C00000')
        bars[best_idx].set_linewidth(2.5)
        ax.set_ylabel('平均RMSE (mm)', fontsize=12)
        ax.set_title('GNSS基线网平差 —— 四种方案精度对比', fontsize=13, fontweight='bold')
        ax.set_ylim(0, max(means) * 1.2)
        ax.grid(axis='y', alpha=0.3)
        fig.tight_layout()
        fig.savefig(str(job_dir / "GNSS_平均RMSE对比.png"), dpi=150, bbox_inches='tight')
        plt.close(fig)

        # 图2: 箱线图
        fig, ax = plt.subplots(figsize=(8, 5))
        box_data = [arr_data[n] for n in names]
        bp = ax.boxplot(box_data, labels=names, patch_artist=True, widths=0.5)
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color); patch.set_alpha(0.7)
        for i, data in enumerate(box_data):
            jitter = np.random.default_rng(42).normal(0, 0.04, len(data))
            ax.scatter(np.ones(len(data)) * (i+1) + jitter, data,
                       alpha=0.5, s=30, color=colors[i], edgecolor='white', linewidth=0.5)
        ax.set_ylabel('RMSE (mm)', fontsize=12)
        ax.set_title('GNSS基线网平差 —— RMSE分布', fontsize=13, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        fig.tight_layout()
        fig.savefig(str(job_dir / "GNSS_RMSE箱线图.png"), dpi=150, bbox_inches='tight')
        plt.close(fig)

        # 图3: 胜率 + ML vs 抗差散点
        fig, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(14, 5.5))
        wins = [sum(1 for k in range(n_test)
                    if results[name][k] <= min(results[n][k] for n in names))
                for name in names]
        bars_w = ax3a.bar(names, wins, color=colors, edgecolor='white', linewidth=0.8)
        for bar, w in zip(bars_w, wins):
            ax3a.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                      f'{w}/{n_test}', ha='center', fontsize=11, fontweight='bold')
        ax3a.set_ylabel('胜出次数', fontsize=12)
        ax3a.set_title(f'{n_test}组测试中胜出次数', fontsize=12, fontweight='bold')
        ax3a.set_ylim(0, n_test + 5)
        ax3a.grid(axis='y', alpha=0.3)

        ml_errs = arr_data['ML智能定权']
        robust_errs = arr_data['抗差估计']
        max_val = max(ml_errs.max(), robust_errs.max()) * 1.1
        ax3b.scatter(robust_errs, ml_errs,
                     c=np.where(ml_errs < robust_errs, '#70AD47', '#C00000'),
                     s=60, alpha=0.7, edgecolor='white', linewidth=0.5)
        ax3b.plot([0, max_val], [0, max_val], 'k--', alpha=0.4, linewidth=1)
        ax3b.set_xlabel('抗差估计 RMSE (mm)', fontsize=12)
        ax3b.set_ylabel('ML智能定权 RMSE (mm)', fontsize=12)
        ax3b.set_title('ML vs 抗差估计', fontsize=12, fontweight='bold')
        ax3b.grid(alpha=0.3)
        ml_wins = sum(1 for k in range(n_test) if ml_errs[k] < robust_errs[k])
        ax3b.text(0.05, 0.95, f'ML胜 {ml_wins}/{n_test} 组',
                  transform=ax3b.transAxes, fontsize=11, fontweight='bold',
                  verticalalignment='top',
                  bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        fig.tight_layout()
        fig.savefig(str(job_dir / "GNSS_胜率与对比散点.png"), dpi=150, bbox_inches='tight')
        plt.close(fig)

        # 图4: 累积分布
        fig, ax = plt.subplots(figsize=(8, 5))
        for name, color in zip(names, colors):
            sorted_errs = np.sort(arr_data[name])
            cum = np.arange(1, len(sorted_errs)+1) / len(sorted_errs)
            ax.plot(sorted_errs, cum, color=color, linewidth=2, label=name)
        ax.set_xlabel('RMSE (mm)', fontsize=12)
        ax.set_ylabel('累积比例', fontsize=12)
        ax.set_title('RMSE累积分布曲线', fontsize=13, fontweight='bold')
        ax.legend(loc='lower right', fontsize=10)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(str(job_dir / "GNSS_误差累积分布.png"), dpi=150, bbox_inches='tight')
        plt.close(fig)


# ================================================================
# 经典平差工具函数
# ================================================================

def _classical_adjust(obs, cov_diag, network):
    """经典间接平差，返回未知点坐标 (3*n_unknown,)"""
    n_bl = len(network.baselines)
    n_unknown = len(network.unknown_stations)
    B, _, _ = network.build_design_matrix()

    l = np.zeros((n_bl * 3, 1))
    for i, bl in enumerate(network.baselines):
        l[3*i:3*i+3, 0] = obs[i]
        unknowns = network.unknown_stations
        name_to_idx = {s.name: j for j, s in enumerate(unknowns)}
        for role, sign in [('from', -1), ('to', 1)]:
            st_name = getattr(bl, f'{role}_station')
            if st_name not in name_to_idx:
                for s in network.known_stations:
                    if s.name == st_name:
                        coords = np.array([s.x, s.y, s.z])
                        l[3*i:3*i+3, 0] -= sign * coords

    P_vec = 1.0 / np.maximum(cov_diag.flatten(), 1e-12)
    P = np.diag(P_vec)
    N = B.T @ P @ B
    W = B.T @ P @ l
    x = np.linalg.solve(N, W)
    return x.flatten()


def _robust_estimate(obs, cov_diag, network):
    """抗差估计（IGGIII 等价权）"""
    n_bl = len(network.baselines)
    B, _, _ = network.build_design_matrix()
    unknowns = network.unknown_stations
    name_to_idx = {s.name: j for j, s in enumerate(unknowns)}

    l = np.zeros((n_bl * 3, 1))
    for i, bl in enumerate(network.baselines):
        l[3*i:3*i+3, 0] = obs[i]
        for role, sign in [('from', -1), ('to', 1)]:
            st_name = getattr(bl, f'{role}_station')
            if st_name not in name_to_idx:
                for s in network.known_stations:
                    if s.name == st_name:
                        coords = np.array([s.x, s.y, s.z])
                        l[3*i:3*i+3, 0] -= sign * coords

    P = np.diag(1.0 / np.maximum(cov_diag.flatten(), 1e-12))
    for _ in range(5):
        N = B.T @ P @ B
        x = np.linalg.solve(N, B.T @ P @ l)
        V = B @ x - l
        N_inv = np.linalg.inv(N)
        Q_VV = np.linalg.inv(P) - B @ N_inv @ B.T
        sigma_v = np.sqrt(np.maximum(np.diag(Q_VV), 1e-12))
        for i in range(len(V)):
            std_r = abs(V[i, 0]) / max(sigma_v[i], 1e-10)
            if std_r > 3.0:
                P[i, i] = max(P[i, i] * 0.01, 1e-6)
            elif std_r > 1.5:
                P[i, i] *= (1.5 / std_r)
    return np.linalg.solve(B.T @ P @ B, B.T @ P @ l).flatten()


def _ml_weighted_adjust(obs, cov_diag, network, ml_weights):
    """用 ML 预测的权重做平差"""
    n_bl = len(network.baselines)
    B, _, _ = network.build_design_matrix()
    unknowns = network.unknown_stations
    name_to_idx = {s.name: j for j, s in enumerate(unknowns)}

    l = np.zeros((n_bl * 3, 1))
    for i, bl in enumerate(network.baselines):
        l[3*i:3*i+3, 0] = obs[i]
        for role, sign in [('from', -1), ('to', 1)]:
            st_name = getattr(bl, f'{role}_station')
            if st_name not in name_to_idx:
                for s in network.known_stations:
                    if s.name == st_name:
                        coords = np.array([s.x, s.y, s.z])
                        l[3*i:3*i+3, 0] -= sign * coords

    P_ml_vec = np.zeros(n_bl * 3)
    for i in range(n_bl):
        base_w = 1.0 / max(cov_diag[i].mean(), 1e-12)
        w = base_w * max(ml_weights[i], 0.01)
        for j in range(3):
            P_ml_vec[3*i + j] = w * base_w
    P_ml = np.diag(P_ml_vec)
    return np.linalg.solve(B.T @ P_ml @ B, B.T @ P_ml @ l).flatten()
