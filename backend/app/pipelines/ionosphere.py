"""电离层 VTEC 建模 Pipeline

谐波模型(27参数) vs 神经网络，使用真实 IGS IONEX 全球电离层地图数据。
"""

import os
import re
import gzip
import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Callable, Optional, List

from ..core.base import Pipeline, AdjustConfig, PipelineResult, StepResult, DataSource
from ..config import RESULT_DIR

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
# IONEX 解析
# ================================================================

def parse_ionex_fast(filepath: str) -> List[tuple]:
    """快速解析 IONEX，返回 (lat, lon, doy, hour, vtec) 列表"""
    opener = gzip.open if filepath.endswith('.gz') else open
    with opener(filepath, 'rt', encoding='utf-8', errors='replace') as f:
        content = f.read()

    lat1, lat2, dlat = 87.5, -87.5, -2.5
    lon1, lon2, dlon = -180.0, 180.0, 5.0
    exponent = -1
    for line in content.split('\n'):
        if 'LAT1 / LAT2 / DLAT' in line:
            p = line.split(); lat1 = float(p[0]); lat2 = float(p[1]); dlat = float(p[2])
        elif 'LON1 / LON2 / DLON' in line:
            p = line.split(); lon1 = float(p[0]); lon2 = float(p[1]); dlon = float(p[2])
        elif 'EXPONENT' in line:
            exponent = int(line.split()[0])

    nlat = int(round((lat1 - lat2) / abs(dlat))) + 1
    nlon = int(round((lon2 - lon1) / dlon)) + 1
    nlines_per_lat = int(np.ceil(nlon / 16))

    maps = re.split(r'START OF TEC MAP', content)[1:]
    records = []
    for m in maps:
        lines = m.strip().split('\n')
        ep_parts = lines[0].split()
        yr, mo, day, hh = int(ep_parts[0]), int(ep_parts[1]), int(ep_parts[2]), int(ep_parts[3])
        doy = datetime.date(yr, mo, day).timetuple().tm_yday
        li = 2
        for ilat in range(nlat):
            vals = []
            for _ in range(nlines_per_lat):
                vals.extend([float(v) for v in lines[li].strip().split()])
                li += 1
            tec_row = np.array(vals[:nlon]) * (10 ** exponent)
            lat_val = lat1 + ilat * dlat
            for ilon, lon_val in enumerate(np.linspace(lon1, lon2 - dlon, nlon)):
                if tec_row[ilon] < 999.0:
                    records.append((lat_val, lon_val, doy, float(hh), tec_row[ilon]))
            if ilat < nlat - 1:
                li += 1
    return records


def load_ionex_dataset(filepaths: List[str], sample_size: int = 60000, seed: int = 42):
    """加载多个 IONEX 文件并降采样"""
    all_data = []
    for fp in filepaths:
        all_data.extend(parse_ionex_fast(fp))

    rng = np.random.default_rng(seed)
    n_sample = min(sample_size, len(all_data))
    idx = rng.choice(len(all_data), n_sample, replace=False)

    lat = np.array([all_data[i][0] for i in idx])
    lon = np.array([all_data[i][1] for i in idx])
    doy = np.array([all_data[i][2] for i in idx])
    hour = np.array([all_data[i][3] for i in idx])
    vtec = np.array([all_data[i][4] for i in idx])

    return lat, lon, doy, hour, vtec, all_data


# ================================================================
# Pipeline
# ================================================================

class IonospherePipeline(Pipeline):
    @property
    def case_id(self) -> str:
        return "ionosphere"

    @property
    def case_name(self) -> str:
        return "电离层VTEC建模"

    @property
    def description(self) -> str:
        return (
            "使用真实 IGS IONEX 全球电离层地图数据，对比 27参数谐波模型 "
            "与神经网络在 VTEC 预测中的表现。包含全球 TEC 地图可视化、"
            "分纬度带/时段精度分析。"
        )

    def config_schema(self) -> dict:
        return {
            "type": "object",
            "title": "电离层实验配置",
            "properties": {
                "sample_size": {
                    "type": "integer", "title": "采样点数",
                    "default": 60000, "minimum": 10000, "maximum": 200000,
                    "description": "从IONEX全量数据中随机采样的点数",
                },
                "test_split_by": {
                    "type": "string", "title": "测试划分方式",
                    "enum": ["doy", "random"], "default": "doy",
                    "description": "doy=按年积日时间外验证, random=随机划分",
                },
                "test_ratio": {
                    "type": "number", "title": "测试比例(随机划分时)",
                    "default": 0.3, "minimum": 0.1, "maximum": 0.5,
                },
                "ml_hidden_dims": {
                    "type": "string", "title": "ML隐藏层",
                    "default": "256,512,256,128",
                    "description": "逗号分隔",
                },
                "ml_epochs": {
                    "type": "integer", "title": "训练轮数",
                    "default": 1500, "minimum": 200, "maximum": 3000,
                },
                "ml_learning_rate": {
                    "type": "number", "title": "学习率",
                    "default": 0.001, "minimum": 0.0001, "maximum": 0.01,
                },
                "map_doy": {
                    "type": "integer", "title": "地图展示DOY",
                    "default": 271, "minimum": 1, "maximum": 366,
                    "description": "全球TEC地图展示的示例日期",
                },
                "map_hour": {
                    "type": "number", "title": "地图展示小时",
                    "default": 12.0, "minimum": 0.0, "maximum": 24.0,
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
            print(f"[电离层] {msg}")
            if progress_callback:
                progress_callback({"step": step, "message": msg})

        p = config.params

        # ========================================================
        # Step 1: 加载 IONEX 数据
        # ========================================================
        log("加载 IONEX 数据...", "load")

        # 优先用上传的文件，否则从 legacy data 加载
        ionex_files = []
        if data_source is not None and data_source.source_type.value != 'null':
            log("使用上传的 IONEX 文件...", "load")
            try:
                _, _, meta = data_source.load()
                ionex_files = meta.get("filepaths", [])
            except Exception:
                ionex_files = getattr(data_source, 'filepaths', [])
            if not ionex_files:
                result.summary = "上传的 IONEX 文件无效"
                result.steps.append(StepResult(name="数据加载", status="failed", error="文件无效"))
                return result

        if not ionex_files:
            import glob
            from ..config import LEGACY_DATA
            ionex_files = sorted(glob.glob(os.path.join(str(LEGACY_DATA), "ionex_*.INX*")))

        if not ionex_files:
            result.summary = "未找到 IONEX 数据文件。请上传 .INX.gz 文件或确认 legacy data 目录存在。"
            result.steps.append(StepResult(name="数据加载", status="failed", error="无IONEX文件"))
            return result

        sample_size = p.get('sample_size', 60000)
        lat, lon, doy, hour, vtec, all_data = load_ionex_dataset(
            ionex_files, sample_size=sample_size, seed=42)
        n_total = len(vtec)
        unique_doy = sorted(set(doy))

        log(f"  文件: {len(ionex_files)}个, 采样{n_total}条, DOY范围:{unique_doy[0]}-{unique_doy[-1]}")
        log(f"  VTEC: {vtec.min():.1f}~{vtec.max():.1f} TECU")

        result.steps.append(StepResult(
            name="数据加载", status="done",
            metrics={"采样数": n_total, "文件数": len(ionex_files), "DOY数": len(unique_doy)},
        ))

        # ========================================================
        # Step 2: 训练/测试划分
        # ========================================================
        split_by = p.get('test_split_by', 'doy')
        if split_by == 'doy':
            mid = len(unique_doy) // 2
            train_idx = np.array([d in set(unique_doy[:mid]) for d in doy])
        else:
            test_ratio = p.get('test_ratio', 0.3)
            rng = np.random.default_rng(42)
            train_idx = rng.random(n_total) > test_ratio
        test_idx = ~train_idx

        log(f"  训练: {train_idx.sum()}条  测试: {test_idx.sum()}条 (划分方式: {split_by})")
        result.steps.append(StepResult(
            name="数据划分", status="done",
            metrics={"训练": int(train_idx.sum()), "测试": int(test_idx.sum())},
        ))

        # ========================================================
        # Step 3: 谐波模型 (经典)
        # ========================================================
        log("拟合谐波模型 (27参数)...", "classical")

        lat_n = lat / 90.0
        lon_rad = np.radians(lon)
        doy_rad = 2 * np.pi * (doy - 1) / 365.25
        hour_rad = 2 * np.pi * hour / 24.0

        B_harm = np.column_stack([
            np.ones(n_total),
            lat_n, lat_n**2, lat_n**3,
            np.cos(hour_rad), np.sin(hour_rad),
            np.cos(2*hour_rad), np.sin(2*hour_rad),
            np.cos(doy_rad), np.sin(doy_rad),
            np.cos(lon_rad), np.sin(lon_rad),
            lat_n*np.cos(hour_rad), lat_n*np.sin(hour_rad),
            lat_n*np.cos(doy_rad), lat_n*np.sin(doy_rad),
            lat_n*np.cos(lon_rad), lat_n*np.sin(lon_rad),
            lat_n**2*np.cos(hour_rad), lat_n**2*np.sin(hour_rad),
            np.abs(lat_n)*np.cos(hour_rad), np.abs(lat_n)*np.sin(hour_rad),
            np.cos(lon_rad)*np.cos(hour_rad), np.sin(lon_rad)*np.sin(hour_rad),
            lat_n*np.cos(doy_rad)*np.cos(hour_rad),
            lat_n*np.sin(doy_rad)*np.sin(hour_rad),
            np.cos(3*hour_rad),
        ])

        N = B_harm[train_idx].T @ B_harm[train_idx]
        W = B_harm[train_idx].T @ vtec[train_idx]
        coeffs = np.linalg.solve(N + np.eye(27) * 1e-6, W)
        harm_pred = B_harm @ coeffs

        result.steps.append(StepResult(name="谐波模型", status="done"))

        # ========================================================
        # Step 4: ML 训练
        # ========================================================
        log("训练 ML 模型...", "ml")

        if not _ensure_torch():
            log("  [跳过] PyTorch 未安装", "ml")
            result.final_metrics = {"error": "PyTorch 未安装"}
            result.summary = "需要安装 PyTorch: py -m pip install torch"
            return result

        X_ml = np.column_stack([
            np.sin(np.radians(lat)), np.cos(np.radians(lat)),
            np.sin(np.radians(lon)), np.cos(np.radians(lon)),
            np.sin(doy_rad), np.cos(doy_rad),
            np.sin(hour_rad), np.cos(hour_rad),
            np.sin(2*hour_rad), np.cos(2*hour_rad),
        ])

        Xm = X_ml[train_idx].mean(0)
        Xs = X_ml[train_idx].std(0) + 1e-8
        ym = vtec[train_idx].mean()
        ys = vtec[train_idx].std()

        X_tr = torch.as_tensor((X_ml[train_idx] - Xm) / Xs, dtype=torch.float32)
        Y_tr = torch.as_tensor(((vtec[train_idx] - ym) / ys).reshape(-1, 1), dtype=torch.float32)
        X_te_t = torch.as_tensor((X_ml[test_idx] - Xm) / Xs, dtype=torch.float32)

        hidden = [int(x.strip()) for x in p.get('ml_hidden_dims', '256,512,256,128').split(',')]
        layers = []
        prev = 10
        for i, h in enumerate(hidden):
            layers.append(nn.Linear(prev, h))
            layers.append(nn.GELU())
            if i < len(hidden) - 1:
                layers.append(nn.Dropout(0.15))
            prev = h
        layers.append(nn.Linear(prev, 1))
        model = nn.Sequential(*layers)

        epochs = p.get('ml_epochs', 1500)
        lr = p.get('ml_learning_rate', 0.001)
        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
        sch = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, mode='min', factor=0.5, patience=100, min_lr=1e-5)

        best_loss, best_state = float('inf'), None
        for ep in range(epochs):
            model.train()
            pred = model(X_tr)
            loss = nn.MSELoss()(pred, Y_tr)
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            sch.step(loss.item())
            if loss.item() < best_loss:
                best_loss = loss.item()
                best_state = {k: v.clone() for k, v in model.state_dict().items()}

        model.load_state_dict(best_state)
        model.eval()
        with torch.no_grad():
            ml_pred = model(torch.as_tensor((X_ml - Xm) / Xs, dtype=torch.float32)).numpy().flatten() * ys + ym

        log(f"  ML 训练完成 ({epochs} 轮)")
        result.steps.append(StepResult(name="ML训练", status="done"))

        # ========================================================
        # Step 5: 评估
        # ========================================================
        log("评估...", "evaluation")
        y_t = vtec[test_idx]
        h_t = harm_pred[test_idx]
        m_t = ml_pred[test_idx]

        rh = np.sqrt(np.mean((h_t - y_t)**2))
        rm = np.sqrt(np.mean((m_t - y_t)**2))
        mh = np.mean(np.abs(h_t - y_t))
        mm = np.mean(np.abs(m_t - y_t))
        improvement = (rh - rm) / rh * 100

        log(f"  谐波模型 RMSE={rh:.2f} MAE={mh:.2f} TECU")
        log(f"  ML神经网络 RMSE={rm:.2f} MAE={mm:.2f} TECU")
        log(f"  ML提升: {improvement:+.1f}%")

        # 分区域评估
        region_metrics = {}
        for name, mask in [
            ('赤道±30°', abs(lat[test_idx]) < 30),
            ('中纬30-60°', (abs(lat[test_idx]) >= 30) & (abs(lat[test_idx]) < 60)),
            ('高纬>60°', abs(lat[test_idx]) >= 60),
            ('白天8-16h', (hour[test_idx] >= 8) & (hour[test_idx] <= 16)),
            ('夜间20-4h', (hour[test_idx] >= 20) | (hour[test_idx] <= 4)),
        ]:
            if mask.sum() < 100:
                continue
            rsh = np.sqrt(np.mean((h_t[mask] - y_t[mask])**2))
            rsm = np.sqrt(np.mean((m_t[mask] - y_t[mask])**2))
            region_metrics[name] = {
                "谐波_RMSE": round(rsh, 2),
                "ML_RMSE": round(rsm, 2),
                "提升": f"{(rsh - rsm) / rsh * 100:+.1f}%",
                "样本数": int(mask.sum()),
            }

        result.final_metrics = {
            "harmonic": {
                "RMSE_TECU": round(rh, 2),
                "MAE_TECU": round(mh, 2),
            },
            "ml": {
                "RMSE_TECU": round(rm, 2),
                "MAE_TECU": round(mm, 2),
            },
            "regions": region_metrics,
        }

        result.summary = (
            f"电离层VTEC建模完成。\n"
            f"  谐波模型(27参): RMSE={rh:.2f} MAE={mh:.2f} TECU\n"
            f"  ML神经网络:     RMSE={rm:.2f} MAE={mm:.2f} TECU\n"
            f"  ML提升:         {improvement:+.1f}%\n"
            f"  训练/测试:      {train_idx.sum()}/{test_idx.sum()} 条\n"
            f"  划分方式:       {'按DOY时间外验证' if split_by=='doy' else '随机划分'}"
        )

        result.steps.append(StepResult(
            name="精度评估", status="done",
            metrics={"谐波RMSE": round(rh, 2), "ML_RMSE": round(rm, 2), "提升": f"{improvement:.1f}%"},
        ))

        # ========================================================
        # Step 6: 图表
        # ========================================================
        log("生成图表...", "charts")
        self._generate_charts(
            job_dir, y_t, h_t, m_t, lat, lon, doy, hour, vtec,
            all_data, coeffs, Xm, Xs, ym, ys, model, unique_doy,
            p.get('map_doy', 271), p.get('map_hour', 12.0),
        )
        charts = self._find_charts(job_dir)
        result.charts = charts
        result.steps.append(StepResult(name="图表生成", status="done", artifacts=charts))

        log("完成!", "done")
        return result

    def _make_job_dir(self):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = RESULT_DIR / f"iono_{ts}"
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def _find_charts(self, job_dir):
        charts = {}
        for f in sorted(job_dir.glob("Iono_*.png")):
            name = f.stem.replace("Iono_", "") + ".png"
            charts[name] = str(f)
        return charts

    def _generate_charts(self, job_dir, y_t, h_t, m_t, lat, lon, doy, hour, vtec,
                         all_data, coeffs, Xm, Xs, ym, ys, model, unique_doy,
                         map_doy, map_hour):
        # 图1: 预测vs真值
        fig1, (a, b) = plt.subplots(1, 2, figsize=(14, 6))
        for ax, pred, label, c in [(a, h_t, '谐波模型(27参数)', '#ED7D31'),
                                      (b, m_t, 'ML神经网络', '#70AD47')]:
            rv = np.sqrt(np.mean((pred - y_t)**2))
            ax.scatter(y_t, pred, alpha=0.12, s=8, c=c, edgecolor='none')
            mv = max(y_t.max(), pred.max())
            ax.plot([0, mv], [0, mv], 'k--', alpha=0.4, lw=1)
            ax.set_xlabel('IGS VTEC (TECU)', fontsize=12)
            ax.set_ylabel('预测 (TECU)', fontsize=12)
            ax.set_title(f'{label}\nRMSE={rv:.2f} TECU', fontsize=13, fontweight='bold')
            ax.grid(alpha=0.3)

        mid = len(unique_doy) // 2
        tl = f'训练{len(unique_doy[:mid])}天 → 测试{len(unique_doy[mid:])}天'
        fig1.suptitle(f'电离层 VTEC 预测 vs 真值\n{tl}', fontsize=13, fontweight='bold')
        fig1.tight_layout()
        fig1.savefig(str(job_dir / "Iono_预测vs真值.png"), dpi=150, bbox_inches='tight')
        plt.close(fig1)

        # 图2: 残差分布
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        hr, mr = h_t - y_t, m_t - y_t
        rng_v = max(abs(hr).max(), abs(mr).max()) * 1.1
        bins = np.linspace(-rng_v, rng_v, 50)
        ax2.hist(hr, bins=bins, alpha=0.5, color='#ED7D31',
                 label=f'谐波(std={hr.std():.2f})', edgecolor='white')
        ax2.hist(mr, bins=bins, alpha=0.5, color='#70AD47',
                 label=f'ML(std={mr.std():.2f})', edgecolor='white')
        ax2.axvline(0, color='black', lw=0.8)
        ax2.set_xlabel('残差 (TECU)', fontsize=13)
        ax2.set_ylabel('频次', fontsize=13)
        ax2.set_title('VTEC 残差分布', fontsize=13, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(axis='y', alpha=0.3)
        fig2.tight_layout()
        fig2.savefig(str(job_dir / "Iono_残差分布.png"), dpi=150, bbox_inches='tight')
        plt.close(fig2)

        # 图3: 全球TEC地图
        full_arr = np.array(all_data, dtype=object)
        full_lat = full_arr[:, 0].astype(float)
        full_lon = full_arr[:, 1].astype(float)
        full_doy = full_arr[:, 2].astype(int)
        full_hour = full_arr[:, 3].astype(float)
        full_vtec = full_arr[:, 4].astype(float)

        sm_f = (full_doy == map_doy) & (np.abs(full_hour - map_hour) < 0.5)
        n_map = sm_f.sum()
        if n_map > 100:
            fl = full_lat[sm_f]
            fn = fl / 90.0
            fo = full_lon[sm_f]
            fr = np.radians(fo)
            fd = full_doy[sm_f]
            dr = 2 * np.pi * (fd - 1) / 365.25
            fh = full_hour[sm_f]
            hr_ = 2 * np.pi * fh / 24.0

            ch = np.cos(hr_); sh = np.sin(hr_)
            c2h = np.cos(2*hr_); s2h = np.sin(2*hr_)
            cd = np.cos(dr); sd = np.sin(dr)
            clo = np.cos(fr); slo = np.sin(fr)
            c3h = np.cos(3*hr_)

            B_map = np.column_stack([
                np.ones(n_map), fn, fn**2, fn**3,
                ch, sh, c2h, s2h, cd, sd, clo, slo,
                fn*ch, fn*sh, fn*cd, fn*sd, fn*clo, fn*slo,
                fn**2*ch, fn**2*sh, np.abs(fn)*ch, np.abs(fn)*sh,
                clo*ch, slo*sh, fn*cd*ch, fn*sd*sh, c3h,
            ])
            map_harm = B_map @ coeffs

            X_map = np.column_stack([
                np.sin(np.radians(fl)), np.cos(np.radians(fl)),
                np.sin(np.radians(fo)), np.cos(np.radians(fo)),
                np.sin(dr), np.cos(dr), np.sin(hr_), np.cos(hr_),
                np.sin(2*hr_), np.cos(2*hr_),
            ])
            X_map_norm = (X_map - Xm) / Xs
            bs = 5000
            ml_vals = []
            model.eval()
            with torch.no_grad():
                for b in range(0, n_map, bs):
                    xb = torch.as_tensor(X_map_norm[b:b+bs], dtype=torch.float32)
                    ml_vals.append(model(xb).numpy().flatten())
            map_ml = np.concatenate(ml_vals) * ys + ym

            uq_lat_f = sorted(set(fl))
            uq_lon_f = sorted(set(fo))
            lat2row = {v: i for i, v in enumerate(uq_lat_f)}
            lon2col = {v: i for i, v in enumerate(uq_lon_f)}
            nla_f, nlo_f = len(uq_lat_f), len(uq_lon_f)
            m_igs = np.full((nla_f, nlo_f), np.nan)
            m_hrm = np.full((nla_f, nlo_f), np.nan)
            m_mlm = np.full((nla_f, nlo_f), np.nan)
            fv = full_vtec[sm_f]
            for i in range(n_map):
                r, c = lat2row[fl[i]], lon2col[fo[i]]
                m_igs[r, c] = fv[i]
                m_hrm[r, c] = map_harm[i]
                m_mlm[r, c] = map_ml[i]

            vmax_v = min(60, np.nanmax(m_igs) * 0.9)
            fig3, (a3a, a3b, a3c) = plt.subplots(1, 3, figsize=(18, 5.5))
            for ax, m, t in [(a3a, m_igs, f'IGS实测 VTEC\nDOY{map_doy} {map_hour:.0f}h'),
                              (a3b, m_hrm, f'谐波模型'),
                              (a3c, m_mlm, f'ML神经网络')]:
                im = ax.imshow(m, extent=[-180, 180, -87.5, 87.5], aspect='auto',
                               cmap='jet', origin='upper', vmin=0, vmax=vmax_v)
                ax.set_title(t, fontsize=12, fontweight='bold')
                ax.set_xlabel('经度')
                ax.set_ylabel('纬度')
                ax.axhline(0, color='white', lw=0.5, alpha=0.5)
                ax.axhline(30, color='w', lw=0.3, alpha=0.3, linestyle='--')
                ax.axhline(-30, color='w', lw=0.3, alpha=0.3, linestyle='--')
            plt.colorbar(im, ax=[a3a, a3b, a3c], label='VTEC (TECU)', shrink=0.85)
            fig3.suptitle(f'全球 VTEC 地图 (测试日 DOY{map_doy}, {map_hour:.0f}:00 UTC)',
                          fontsize=14, fontweight='bold')
            fig3.tight_layout()
            fig3.savefig(str(job_dir / "Iono_全球TEC地图.png"), dpi=150, bbox_inches='tight')
            plt.close(fig3)
