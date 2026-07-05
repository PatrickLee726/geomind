"""对流层 ZTD 建模 Pipeline

对比四条路线:
  Saastamoinen+GPT3  →  经典公式 + 估算气象 (基线 ~14cm)
  Saastamoinen+可用气象 → 经典公式 + 实测优先/GPT3回退
  ML+GPT3特征        →  神经网络从时空+GPT3气象学习 ZTD
  ML+实测气象特征     →  神经网络从时空+实测气象学习 ZTD
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

def _ensure_torch():
    """延迟导入 PyTorch，允许在无 torch 环境下运行经典模式"""
    global torch, nn
    try:
        import torch
        import torch.nn as nn
        return True
    except ImportError:
        return False

from ..core.base import (
    Pipeline, DataSource, AdjustConfig,
    PipelineResult, StepResult,
)
from ..config import RESULT_DIR
from ..datasources.igs_utils import (
    saastamoinen_ztd, gpt3_pressure_temp,
)

# 中文字体
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class TropospherePipeline(Pipeline):
    """对流层天顶延迟建模 Pipeline"""

    @property
    def case_id(self) -> str:
        return "troposphere"

    @property
    def case_name(self) -> str:
        return "对流层天顶延迟 (ZTD) 建模"

    @property
    def description(self) -> str:
        return (
            "对比经典 Saastamoinen 公式与机器学习在对流层天顶延迟预测中的表现。"
            "使用真实 IGS 精密对流层数据，评估不同气象输入源（GPT3 估算 vs 实测气象）"
            "下的预测精度。"
        )

    def config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "test_ratio": {
                    "type": "number", "title": "测试集比例",
                    "default": 0.2, "minimum": 0.1, "maximum": 0.5,
                },
                "ml_hidden_dims": {
                    "type": "string", "title": "ML隐藏层结构",
                    "default": "128,256,128,64",
                    "description": "逗号分隔，如 128,256,128,64",
                },
                "ml_epochs": {
                    "type": "integer", "title": "ML训练轮数",
                    "default": 2000, "minimum": 100, "maximum": 10000,
                },
                "ml_learning_rate": {
                    "type": "number", "title": "学习率",
                    "default": 0.001, "minimum": 0.0001, "maximum": 0.1,
                },
                "mode": {
                    "type": "string", "title": "运行模式",
                    "enum": ["compare", "classical_only", "ml_only"],
                    "default": "compare",
                },
            },
        }

    def run(
        self,
        data_source: DataSource,
        config: AdjustConfig,
        progress_callback: Optional[Callable] = None,
    ) -> PipelineResult:
        result = PipelineResult()
        job_dir = self._make_job_dir()

        def log(msg, step="info"):
            print(f"[对流层] {msg}")
            if progress_callback:
                progress_callback({"step": step, "message": msg})

        # ============================
        # Step 1: 加载数据
        # ============================
        log("加载数据...", "load")
        X, y, meta = data_source.load()
        all_records = meta.get('all_records', [])
        n_total = len(y)
        result.steps.append(StepResult(
            name="数据加载", status="done",
            metrics={"总记录数": n_total, "站点数": len(meta.get('stations', []))},
        ))

        # ============================
        # Step 2: 划分训练/测试集（按站划分）
        # ============================
        log("划分训练/测试集...", "split")
        stations = list(set(r['station'] for r in all_records))
        rng = np.random.default_rng(config.random_seed)
        n_test_stations = max(1, int(len(stations) * config.params.get('test_ratio', config.test_ratio)))
        test_stations = set(rng.choice(stations, n_test_stations, replace=False))
        train_stations = [s for s in stations if s not in test_stations]

        station_arr = np.array([r['station'] for r in all_records])
        test_mask = np.array([s in test_stations for s in station_arr])
        train_mask = ~test_mask

        log(f"  训练站: {train_stations} ({train_mask.sum()}条)")
        log(f"  测试站: {sorted(test_stations)} ({test_mask.sum()}条)")

        X_train, y_train = X[train_mask], y[train_mask]
        X_test, y_test = X[test_mask], y[test_mask]

        # 提取各列
        lat_arr = X[:, 0]; H_arr = X[:, 1]
        doy_arr = np.array([r['doy'] for r in all_records])
        hour_arr = np.array([r['hour'] for r in all_records])
        P_arr = X[:, 6]; T_arr = X[:, 7]; e_arr = X[:, 8]

        result.steps.append(StepResult(
            name="数据划分", status="done",
            metrics={
                "训练样本": int(train_mask.sum()),
                "测试样本": int(test_mask.sum()),
                "训练站数": len(train_stations),
            },
        ))

        # ============================
        # Step 3: 计算经典方法
        # ============================
        log("计算经典方法...", "classical")

        # Saastamoinen + 可用气象 (实测优先/GPT3回退)
        ztd_saas_real = np.array([
            saastamoinen_ztd(P_arr[i], T_arr[i], e_arr[i], lat_arr[i], H_arr[i])
            for i in range(n_total)
        ])

        # Saastamoinen + 纯 GPT3
        P_gpt3 = np.zeros(n_total); T_gpt3 = np.zeros(n_total); e_gpt3_arr = np.zeros(n_total)
        for i in range(n_total):
            P_gpt3[i], T_gpt3[i], e_gpt3_arr[i] = gpt3_pressure_temp(
                lat_arr[i], 110, H_arr[i], doy_arr[i])
        ztd_saas_gpt3 = np.array([
            saastamoinen_ztd(P_gpt3[i], T_gpt3[i], e_gpt3_arr[i], lat_arr[i], H_arr[i])
            for i in range(n_total)
        ])

        saas_real_rmse = np.sqrt(np.mean((ztd_saas_real[test_mask] - y_test)**2)) * 100
        saas_gpt3_rmse = np.sqrt(np.mean((ztd_saas_gpt3[test_mask] - y_test)**2)) * 100

        log(f"  Saastamoinen+GPT3  RMSE = {saas_gpt3_rmse:.2f} cm")
        log(f"  Saastamoinen+可用气象 RMSE = {saas_real_rmse:.2f} cm")

        result.steps.append(StepResult(
            name="经典方法", status="done",
            metrics={
                "Saastamoinen+GPT3_RMSE_cm": round(saas_gpt3_rmse, 2),
                "Saastamoinen+可用气象_RMSE_cm": round(saas_real_rmse, 2),
            },
        ))

        if config.params.get('mode', config.mode) == "classical_only":
            # 仅经典模式：直接生成图表后返回
            self._generate_charts(
                job_dir, y_test, test_mask, all_records,
                ztd_saas_gpt3[test_mask], ztd_saas_real[test_mask],
                None, None,
                train_stations, test_stations,
            )
            result.final_metrics = {
                "classical": {
                    "Saastamoinen+GPT3_RMSE_cm": round(saas_gpt3_rmse, 2),
                    "Saastamoinen+可用气象_RMSE_cm": round(saas_real_rmse, 2),
                }
            }
            charts = self._find_charts(job_dir)
            result.charts = charts
            result.steps.append(StepResult(name="图表生成", status="done"))
            result.summary = f"经典方法：Saastamoinen+GPT3 RMSE={saas_gpt3_rmse:.2f}cm"
            return result

        # ============================
        # Step 4: 训练 ML 模型
        # ============================
        log("训练 ML 模型...", "ml")

        if not _ensure_torch():
            log("  [跳过] PyTorch 未安装，仅运行经典方法。安装: py -m pip install torch", "ml")
            pred_ml_gpt3 = None
            pred_ml_full = None
            ml_gpt3_rmse = float('nan')
            ml_full_rmse = float('nan')
            result.steps.append(StepResult(
                name="ML训练", status="done",
                metrics={"提示": "PyTorch 未安装，仅显示经典方法结果"},
            ))
        else:
            # 构建 GPT3-only 特征
            X_gpt3 = np.column_stack([
                lat_arr, H_arr,
                np.sin(2*np.pi*(doy_arr-1)/365.25), np.cos(2*np.pi*(doy_arr-1)/365.25),
                np.sin(2*np.pi*hour_arr/24.0), np.cos(2*np.pi*hour_arr/24.0),
                P_gpt3, T_gpt3, e_gpt3_arr,
            ])
            # 完整特征（实测优先）
            X_full = X.copy()

            def train_ml(X_feat, y_tr, y_te, test_idx, name, hidden_str, epochs, lr):
                hidden_dims = [int(x.strip()) for x in hidden_str.split(',')]
                input_dim = X_feat.shape[1]
                X_mean = X_feat[train_mask].mean(axis=0)
                X_std = X_feat[train_mask].std(axis=0) + 1e-8
                y_mean = y_tr.mean(); y_std = y_tr.std() + 1e-8
                X_tr_t = torch.as_tensor((X_feat[train_mask] - X_mean) / X_std, dtype=torch.float32)
                X_te_t = torch.as_tensor((X_feat[test_mask] - X_mean) / X_std, dtype=torch.float32)
                Y_tr_t = torch.as_tensor(((y_tr - y_mean) / y_std).reshape(-1, 1), dtype=torch.float32)
                layers = []
                prev = input_dim
                for h in hidden_dims:
                    layers.append(nn.Linear(prev, h)); layers.append(nn.GELU())
                    layers.append(nn.Dropout(0.1)); prev = h
                layers.append(nn.Linear(prev, 1))
                model = nn.Sequential(*layers)
                opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
                sch = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode='min', factor=0.5, patience=150, min_lr=1e-5)
                best_loss, best_state = float('inf'), None
                for ep in range(epochs):
                    model.train()
                    pred = model(X_tr_t); loss = nn.MSELoss()(pred, Y_tr_t)
                    opt.zero_grad(); loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                    opt.step()
                    sch.step(loss.item())
                    if loss.item() < best_loss:
                        best_loss = loss.item()
                        best_state = {k: v.clone() for k, v in model.state_dict().items()}
                model.load_state_dict(best_state)
                model.eval()
                with torch.no_grad():
                    return model(X_te_t).numpy().flatten() * y_std + y_mean

            pred_ml_gpt3 = train_ml(X_gpt3, y_train, y_test, test_mask,
                "ML+GPT3", config.params.get('ml_hidden_dims', config.ml_params.get('hidden_dims', '128,256,128,64')),
                config.params.get('ml_epochs', config.ml_params.get('epochs', 2000)),
                config.params.get('ml_learning_rate', config.ml_params.get('learning_rate', 0.001)))
            ml_gpt3_rmse = np.sqrt(np.mean((pred_ml_gpt3 - y_test)**2)) * 100
            log(f"  ML+GPT3      RMSE = {ml_gpt3_rmse:.2f} cm")

            pred_ml_full = train_ml(X_full, y_train, y_test, test_mask,
                "ML+实测", config.params.get('ml_hidden_dims', config.ml_params.get('hidden_dims', '128,256,128,64')),
                config.params.get('ml_epochs', config.ml_params.get('epochs', 2000)),
                config.params.get('ml_learning_rate', config.ml_params.get('learning_rate', 0.001)))
            ml_full_rmse = np.sqrt(np.mean((pred_ml_full - y_test)**2)) * 100
            log(f"  ML+实测气象  RMSE = {ml_full_rmse:.2f} cm")

            result.steps.append(StepResult(
                name="ML训练", status="done",
                metrics={"ML+GPT3_RMSE_cm": round(ml_gpt3_rmse, 2), "ML+实测气象_RMSE_cm": round(ml_full_rmse, 2)},
            ))
            improvement = (saas_gpt3_rmse - ml_gpt3_rmse) / saas_gpt3_rmse * 100
            log(f"  ML 相比 Saastamoinen+GPT3 提升: {improvement:.1f}%")

        # ============================
        # Step 5: 生成图表
        # ============================
        log("生成图表...", "charts")
        self._generate_charts(
            job_dir, y_test, test_mask, all_records,
            ztd_saas_gpt3[test_mask] if test_mask.sum() == len(pred_ml_gpt3) else ztd_saas_gpt3[test_mask],
            ztd_saas_real[test_mask] if test_mask.sum() == len(pred_ml_gpt3) else ztd_saas_real[test_mask],
            pred_ml_gpt3, pred_ml_full,
            train_stations, test_stations,
        )

        charts = self._find_charts(job_dir)
        result.charts = charts
        result.steps.append(StepResult(
            name="图表生成", status="done",
            artifacts=charts,
        ))

        # ============================
        # 汇总
        # ============================
        result.final_metrics = {
            "classical": {
                "Saastamoinen+GPT3_RMSE_cm": round(saas_gpt3_rmse, 2),
                "Saastamoinen+可用气象_RMSE_cm": round(saas_real_rmse, 2),
            },
        }
        if pred_ml_gpt3 is not None:
            result.final_metrics["ml"] = {
                "ML+GPT3_RMSE_cm": round(ml_gpt3_rmse, 2),
                "ML+实测气象_RMSE_cm": round(ml_full_rmse, 2),
            }

        lines = [
            f"对流层ZTD建模完成。",
            f"  经典: Saastamoinen+GPT3 = {saas_gpt3_rmse:.2f} cm",
        ]
        if pred_ml_gpt3 is not None and not np.isnan(ml_gpt3_rmse):
            imp = (saas_gpt3_rmse - ml_gpt3_rmse) / saas_gpt3_rmse * 100
            lines.append(f"  ML:   ML+GPT3 = {ml_gpt3_rmse:.2f} cm (提升 {imp:.1f}%)")
        else:
            lines.append(f"  ML:   未安装 PyTorch，安装后可用: py -m pip install torch")
        lines.append(f"  测试站: {', '.join(sorted(test_stations))}")
        result.summary = "\n".join(lines)
        log("完成!", "done")
        return result

    def _make_job_dir(self) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = RESULT_DIR / f"trop_{ts}"
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def _generate_charts(self, job_dir, y_test, test_mask, all_records,
                         saas_gpt3, saas_real, ml_gpt3, ml_full,
                         train_stations, test_stations):
        """生成所有可视化图表"""
        test_st_list = sorted(test_stations)

        # --- 图1: 预测 vs 真值 ---
        if ml_gpt3 is not None:
            fig1, (ax1a, ax1b) = plt.subplots(1, 2, figsize=(14, 6))
            for ax, pred, label, color in [
                (ax1a, saas_gpt3, 'Saastamoinen + GPT3', '#ED7D31'),
                (ax1b, ml_gpt3, 'ML + GPT3', '#70AD47'),
            ]:
                rmse_val = np.sqrt(np.mean((pred - y_test)**2)) * 100
                ax.scatter(y_test, pred, alpha=0.35, s=12, c=color, edgecolor='none')
                minv = min(y_test.min(), pred.min())
                maxv = max(y_test.max(), pred.max())
                ax.plot([minv, maxv], [minv, maxv], 'k--', alpha=0.4, linewidth=1)
                ax.set_xlabel('IGS 实测 ZTD (m)', fontsize=12)
                ax.set_ylabel('模型预测 ZTD (m)', fontsize=12)
                ax.set_title(f'{label}\nRMSE = {rmse_val:.2f} cm', fontsize=13, fontweight='bold')
                ax.grid(alpha=0.3)
            fig1.suptitle(
                f'对流层ZTD：预测 vs 真值\n测试站 {", ".join(test_st_list)} '
                f'({len(y_test)} epoch, 未参与训练)',
                fontsize=13, fontweight='bold')
            fig1.tight_layout()
            fig1.savefig(job_dir / "预测vs真值.png", dpi=150, bbox_inches='tight')
            plt.close(fig1)

        # --- 图2: RMSE 柱状图 ---
        methods = []; rmses = []; colors = []
        if saas_gpt3 is not None:
            methods.append('Saastamoinen\n+ GPT3'); rmses.append(np.sqrt(np.mean((saas_gpt3 - y_test)**2))*100); colors.append('#ED7D31')
        if saas_real is not None:
            methods.append('Saastamoinen\n+ 可用气象'); rmses.append(np.sqrt(np.mean((saas_real - y_test)**2))*100); colors.append('#FFC000')
        if ml_gpt3 is not None:
            methods.append('ML\n+ GPT3'); rmses.append(np.sqrt(np.mean((ml_gpt3 - y_test)**2))*100); colors.append('#5B9BD5')
        if ml_full is not None:
            methods.append('ML\n+ 实测气象'); rmses.append(np.sqrt(np.mean((ml_full - y_test)**2))*100); colors.append('#70AD47')

        if methods:
            fig2, ax2 = plt.subplots(figsize=(9, 5.5))
            bars = ax2.bar(range(len(methods)), rmses, color=colors, edgecolor='white', linewidth=1)
            for bar, v in zip(bars, rmses):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.4,
                         f'{v:.1f} cm', ha='center', fontsize=12, fontweight='bold')
            best_idx = rmses.index(min(rmses))
            bars[best_idx].set_edgecolor('#C00000')
            bars[best_idx].set_linewidth(2.5)
            ax2.set_xticks(range(len(methods)))
            ax2.set_xticklabels(methods, fontsize=10)
            ax2.set_ylabel('RMSE (cm)', fontsize=13)
            ax2.set_title(
                f'对流层ZTD预测精度对比\n'
                f'(训练{len(train_stations)}站 → 测试{len(test_st_list)}站)',
                fontsize=13, fontweight='bold')
            ax2.set_ylim(0, max(rmses) * 1.25)
            ax2.grid(axis='y', alpha=0.3)
            fig2.tight_layout()
            fig2.savefig(job_dir / "RMSE对比.png", dpi=150, bbox_inches='tight')
            plt.close(fig2)

    def _find_charts(self, job_dir: Path) -> dict:
        charts = {}
        for png in job_dir.glob("*.png"):
            name = png.stem
            charts[name] = str(png.relative_to(RESULT_DIR.parent))
        return charts
