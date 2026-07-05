"""高程异常建模 Pipeline

三种场景对比：经典多项式间接平差 vs 神经网络
- 场景A: 8点平坦水库（课件数据）
- 场景B: 200点复杂构造（陡坎+凹陷+波动）
- 场景C: 50点中等复杂地形
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

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
# 数据生成（从 utils/io.py 提炼）
# ================================================================

def _make_example_data():
    """课件8点水库数据"""
    data = [
        (100.0, 200.0, 25.682),
        (150.0, 180.0, 25.671),
        (200.0, 220.0, 25.695),
        (180.0, 250.0, 25.698),
        (120.0, 280.0, 25.695),
        (80.0,  230.0, 25.678),
        (60.0,  190.0, 25.675),
        (140.0, 150.0, 25.675),
    ]
    arr = np.array(data)
    return arr[:, :2], arr[:, 2]


def _make_nonlinear_data(n_points=100, noise=0.02, random_state=42):
    """强非线性高程异常数据"""
    rng = np.random.default_rng(random_state)
    X = rng.uniform(0, 100, (n_points, 2))
    y = 25.68 + 0.02 * X[:, 0] - 0.01 * X[:, 1]
    step = 0.8 * (1 / (1 + np.exp(-0.5 * (X[:, 0] - 50))))
    dist_to_sink = np.sqrt((X[:, 0] - 70)**2 + (X[:, 1] - 50)**2)
    sink = -0.5 * np.exp(-dist_to_sink**2 / 80)
    ripple = 0.15 * np.sin(X[:, 0] / 8) * np.cos(X[:, 1] / 6)
    y = y + step + sink + ripple + noise * rng.standard_normal(n_points)
    return X, y


# ================================================================
# 经典多项式平差
# ================================================================

def _build_polynomial_features(X, degree):
    """构建多项式特征矩阵"""
    x, y = X[:, 0], X[:, 1]
    cols = [np.ones(len(x))]
    for d in range(1, degree + 1):
        for i in range(d + 1):
            cols.append((x ** (d - i)) * (y ** i))
    return np.column_stack(cols)


def _polynomial_fit(X, y, degree):
    """最小二乘多项式拟合"""
    B = _build_polynomial_features(X, degree)
    coeffs = np.linalg.lstsq(B, y, rcond=None)[0]
    pred = B @ coeffs
    rmse = np.sqrt(np.mean((pred - y)**2))
    mae = np.mean(np.abs(pred - y))
    return coeffs, pred, rmse, mae


# ================================================================
# Pipeline
# ================================================================

class ElevationPipeline(Pipeline):
    @property
    def case_id(self) -> str:
        return "elevation"

    @property
    def case_name(self) -> str:
        return "高程异常建模"

    @property
    def description(self) -> str:
        return (
            "高程异常建模 —— 经典多项式间接平差 vs 神经网络。"
            "三种场景：平坦水库(8点)、复杂构造(200点)、中等复杂(50点)。"
            "ML通过非线性激活函数自动学习陡坎、凹陷等地质特征。"
        )

    def config_schema(self) -> dict:
        return {
            "type": "object",
            "title": "高程异常实验配置",
            "properties": {
                "scenario": {
                    "type": "string", "title": "场景",
                    "enum": ["A", "B", "C"], "default": "B",
                    "description": "A=平坦水库(8点) B=复杂构造(200点) C=中等复杂(50点)",
                },
                "polynomial_degree": {
                    "type": "integer", "title": "多项式次数",
                    "default": 5, "minimum": 2, "maximum": 5,
                    "description": "经典方法的多项式次数",
                },
                "ml_hidden_dims": {
                    "type": "string", "title": "ML隐藏层",
                    "default": "64,128,64",
                    "description": "场景A建议[4], B建议[64,128,64], C建议[32,64,32]",
                },
                "ml_epochs": {
                    "type": "integer", "title": "训练轮数",
                    "default": 3000, "minimum": 500, "maximum": 5000,
                },
                "ml_learning_rate": {
                    "type": "number", "title": "学习率",
                    "default": 0.01, "minimum": 0.001, "maximum": 0.1,
                },
                "noise_level": {
                    "type": "number", "title": "噪声水平(场景B/C)",
                    "default": 0.02, "minimum": 0.005, "maximum": 0.05,
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
            print(f"[高程异常] {msg}")
            if progress_callback:
                progress_callback({"step": step, "message": msg})

        p = config.params

        # ========================================================
        # Step 1: 获取数据（上传优先，否则模拟）
        # ========================================================
        scenario = p.get('scenario', 'B')
        poly_deg = p.get('polynomial_degree', 5)

        # 检查是否有上传的CSV数据
        if data_source is not None and data_source.source_type.value != 'null':
            log("加载上传的CSV数据...", "setup")
            X, y, meta = data_source.load()
            scenario_name = f"上传数据({len(y)}点)"
            scenario = 'upload'
            log(f"  {scenario_name}, zeta范围=[{y.min():.3f}, {y.max():.3f}]m")
        elif scenario == 'A':
            log(f"生成场景A数据...", "setup")
            X, y = _make_example_data()
            scenario_name = "平坦水库(8点)"
        elif scenario == 'B':
            X, y = _make_nonlinear_data(n_points=200, noise=p.get('noise_level', 0.02), random_state=42)
            scenario_name = "复杂构造(200点)"
        else:
            X, y = _make_nonlinear_data(n_points=50, noise=p.get('noise_level', 0.02), random_state=123)
            scenario_name = "中等复杂(50点)"

        n = len(y)
        log(f"  {scenario_name}: {n}点, zeta范围=[{y.min():.3f}, {y.max():.3f}]m")

        result.steps.append(StepResult(
            name="数据生成", status="done",
            metrics={"场景": scenario_name, "点数": n, "zeta范围(m)": f"{y.min():.3f}~{y.max():.3f}"},
        ))

        # ========================================================
        # Step 2: 经典多项式平差
        # ========================================================
        log(f"经典{poly_deg}次多项式平差...", "classical")

        # 场景A自动尝试2/3/5次选最优
        if scenario == 'A' and p.get('auto_select_degree', True):
            best_deg, best_rmse_c = None, float('inf')
            for deg in [2, 3, 5]:
                _, _, rmse, _ = _polynomial_fit(X, y, deg)
                if rmse < best_rmse_c:
                    best_deg, best_rmse_c = deg, rmse
            poly_deg = best_deg
            log(f"  自动选择最优次数: {poly_deg}次")

        coeffs_c, pred_c, rmse_c, mae_c = _polynomial_fit(X, y, poly_deg)
        log(f"  RMSE={rmse_c:.4f}m MAE={mae_c:.4f}m 参数数={len(coeffs_c)}")

        result.steps.append(StepResult(
            name="经典平差", status="done",
            metrics={"多项式次数": poly_deg, "RMSE_m": round(rmse_c, 4), "MAE_m": round(mae_c, 4)},
        ))

        # ========================================================
        # Step 3: ML训练
        # ========================================================
        log("训练ML神经网络...", "ml")

        if not _ensure_torch():
            log("  [跳过] PyTorch 未安装", "ml")
            result.final_metrics = {"error": "PyTorch 未安装"}
            result.summary = "需要安装 PyTorch: py -m pip install torch"
            return result

        hidden = [int(x.strip()) for x in p.get('ml_hidden_dims', '64,128,64').split(',')]
        epochs = p.get('ml_epochs', 3000)
        lr = p.get('ml_learning_rate', 0.01)

        # 数据标准化
        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0) + 1e-8
        y_mean = y.mean()
        y_std = y.std() + 1e-8

        X_norm = (X - X_mean) / X_std
        y_norm = (y - y_mean) / y_std

        X_tr = torch.as_tensor(X_norm, dtype=torch.float32)
        Y_tr = torch.as_tensor(y_norm.reshape(-1, 1), dtype=torch.float32)

        # 网络
        layers = []
        prev = 2
        for i, h in enumerate(hidden):
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            if i < len(hidden) - 1:
                layers.append(nn.Dropout(0.1))
            prev = h
        layers.append(nn.Linear(prev, 1))
        model = nn.Sequential(*layers)

        opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
        sch = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, mode='min', factor=0.5, patience=200, min_lr=1e-5)

        best_loss, best_state = float('inf'), None
        for ep in range(epochs):
            model.train()
            pred = model(X_tr)
            loss = nn.MSELoss()(pred, Y_tr)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sch.step(loss.item())
            if loss.item() < best_loss:
                best_loss = loss.item()
                best_state = {k: v.clone() for k, v in model.state_dict().items()}

        model.load_state_dict(best_state)
        model.eval()
        with torch.no_grad():
            pred_ml_norm = model(X_tr).numpy().flatten()
        pred_ml = pred_ml_norm * y_std + y_mean

        rmse_ml = np.sqrt(np.mean((pred_ml - y)**2))
        mae_ml = np.mean(np.abs(pred_ml - y))
        log(f"  RMSE={rmse_ml:.4f}m MAE={mae_ml:.4f}m ({epochs}轮)")

        result.steps.append(StepResult(
            name="ML训练", status="done",
            metrics={"RMSE_m": round(rmse_ml, 4), "MAE_m": round(mae_ml, 4), "轮数": epochs},
        ))

        # ========================================================
        # Step 4: 评估与汇总
        # ========================================================
        improvement = (rmse_c - rmse_ml) / rmse_c * 100
        winner = "ML" if rmse_ml < rmse_c else "经典"
        log(f"  >> {winner}胜! ML{'降低' if rmse_ml < rmse_c else '差距'} {abs(improvement):.1f}% <<")

        result.final_metrics = {
            "classical": {
                "多项式次数": poly_deg,
                "RMSE_m": round(rmse_c, 4),
                "MAE_m": round(mae_c, 4),
                "参数数": len(coeffs_c),
            },
            "ml": {
                "隐藏层": str(hidden),
                "RMSE_m": round(rmse_ml, 4),
                "MAE_m": round(mae_ml, 4),
            },
        }

        result.summary = (
            f"高程异常建模完成 —— 场景{scenario} ({scenario_name})\n"
            f"  经典{poly_deg}次多项式: RMSE={rmse_c:.4f}m MAE={mae_c:.4f}m\n"
            f"  ML神经网络{hidden}:      RMSE={rmse_ml:.4f}m MAE={mae_ml:.4f}m\n"
            f"  胜出: {winner} ({abs(improvement):.1f}% {'降低' if rmse_ml < rmse_c else '差距'})\n"
            f"  点数: {n}"
        )

        # ========================================================
        # Step 5: 图表
        # ========================================================
        log("生成图表...", "charts")
        self._generate_charts(job_dir, X, y, pred_c, pred_ml, scenario, scenario_name, poly_deg, hidden)
        charts = self._find_charts(job_dir)
        result.charts = charts
        result.steps.append(StepResult(name="图表生成", status="done", artifacts=charts))

        log("完成!", "done")
        return result

    def _make_job_dir(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = RESULT_DIR / f"elev_{ts}"
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def _find_charts(self, job_dir):
        charts = {}
        for f in sorted(job_dir.glob("Elev_*.png")):
            name = f.stem.replace("Elev_", "") + ".png"
            charts[name] = str(f)
        return charts

    def _generate_charts(self, job_dir, X, y, pred_c, pred_ml, scenario, scenario_name, poly_deg, hidden):
        # 图1: 预测vs真值
        fig1, (a, b) = plt.subplots(1, 2, figsize=(14, 6))
        for ax, pred, label, c in [(a, pred_c, f'经典{poly_deg}次多项式', '#ED7D31'),
                                      (b, pred_ml, f'ML{hidden}', '#70AD47')]:
            rv = np.sqrt(np.mean((pred - y)**2))
            ax.scatter(y, pred, alpha=0.5 if len(y) > 20 else 0.8,
                       s=20 if len(y) > 20 else 80, c=c, edgecolor='white', linewidth=0.5)
            mv = max(y.max(), pred.max())
            mn = min(y.min(), pred.min())
            ax.plot([mn, mv], [mn, mv], 'k--', alpha=0.4, lw=1)
            ax.set_xlabel('真实值 (m)', fontsize=12)
            ax.set_ylabel('预测值 (m)', fontsize=12)
            ax.set_title(f'{label}\nRMSE={rv:.4f}m', fontsize=13, fontweight='bold')
            ax.grid(alpha=0.3)
        fig1.suptitle(f'高程异常预测 vs 真值 —— {scenario_name}', fontsize=14, fontweight='bold')
        fig1.tight_layout()
        fig1.savefig(str(job_dir / "Elev_预测vs真值.png"), dpi=150, bbox_inches='tight')
        plt.close(fig1)

        # 图2: 残差分布
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        rc, rml = pred_c - y, pred_ml - y
        rng_v = max(abs(rc).max(), abs(rml).max()) * 1.2
        bins = np.linspace(-rng_v, rng_v, 40)
        ax2.hist(rc, bins=bins, alpha=0.5, color='#ED7D31',
                 label=f'经典(std={rc.std():.4f})', edgecolor='white')
        ax2.hist(rml, bins=bins, alpha=0.5, color='#70AD47',
                 label=f'ML(std={rml.std():.4f})', edgecolor='white')
        ax2.axvline(0, color='black', lw=0.8)
        ax2.set_xlabel('残差 (m)', fontsize=13)
        ax2.set_ylabel('频次', fontsize=13)
        ax2.set_title('高程异常残差分布', fontsize=13, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(axis='y', alpha=0.3)
        fig2.tight_layout()
        fig2.savefig(str(job_dir / "Elev_残差分布.png"), dpi=150, bbox_inches='tight')
        plt.close(fig2)

        # 图3: 空间分布（散点图）
        if len(y) >= 20:
            fig3, (a3, b3, c3) = plt.subplots(1, 3, figsize=(18, 5.5))
            vmax = max(abs(y - y.min()).max(), 0.5)
            for ax, val, title, cmap in [
                (a3, y, '真实高程异常', 'terrain'),
                (b3, pred_c, f'经典{poly_deg}次预测', 'terrain'),
                (c3, pred_ml, 'ML预测', 'terrain'),
            ]:
                sc = ax.scatter(X[:, 0], X[:, 1], c=val, cmap=cmap,
                                s=30, edgecolor='none', vmin=y.min(), vmax=y.max())
                ax.set_title(title, fontsize=12, fontweight='bold')
                ax.set_xlabel('X (m)')
                ax.set_ylabel('Y (m)')
                plt.colorbar(sc, ax=ax, label='ζ (m)', shrink=0.8)
            fig3.suptitle(f'高程异常空间分布 —— {scenario_name}', fontsize=14, fontweight='bold')
            fig3.tight_layout()
            fig3.savefig(str(job_dir / "Elev_空间分布.png"), dpi=150, bbox_inches='tight')
            plt.close(fig3)
