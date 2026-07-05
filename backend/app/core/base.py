"""核心抽象接口：DataSource / Pipeline / Model"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import numpy as np
import hashlib
import json
import pickle
from pathlib import Path


class DataSourceType(str, Enum):
    UPLOAD = "upload"
    IGS_CDDIS = "igs_cddis"
    SIMULATED = "simulated"


@dataclass
class DataProfile:
    """数据画像"""
    n_samples: int
    feature_dim: int
    feature_names: List[str] = field(default_factory=list)
    spatial_extent_km: Optional[float] = None
    terrain_complexity: str = "unknown"
    elevation_range: Optional[float] = None


class DataSource(ABC):
    """统一的数据源接口"""

    @abstractmethod
    def load(self) -> tuple:
        """返回 (X, y, meta) 其中 meta 是字典包含额外信息"""
        ...

    @abstractmethod
    def describe(self) -> DataProfile:
        ...

    @property
    @abstractmethod
    def source_type(self) -> DataSourceType:
        ...


@dataclass
class AdjustConfig:
    """平差/训练配置"""
    # 通用
    test_ratio: float = 0.2
    random_seed: int = 42
    mode: str = "compare"
    # Pipeline 特定参数
    params: Dict[str, Any] = field(default_factory=dict)
    # 兼容旧格式（对流层 ML 参数）
    ml_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """Pipeline 单步结果"""
    name: str
    status: str  # pending / running / done / failed
    metrics: Dict[str, float] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)  # name → path
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Pipeline 完整结果"""
    case_id: str = ""
    steps: List[StepResult] = field(default_factory=list)
    final_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    charts: Dict[str, str] = field(default_factory=dict)   # name → path
    summary: str = ""
    feature_importance: Dict[str, float] = field(default_factory=dict)


class Pipeline(ABC):
    """平差案例 Pipeline 基类"""

    @property
    @abstractmethod
    def case_id(self) -> str:
        ...

    @property
    @abstractmethod
    def case_name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def config_schema(self) -> dict:
        """返回 JSON Schema，前端据此渲染配置表单"""
        ...

    @abstractmethod
    def run(self, data_source: DataSource, config: AdjustConfig,
            progress_callback=None) -> PipelineResult:
        """执行 Pipeline"""
        ...

    # ───── 模型缓存 ─────
    _MODEL_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "model_cache"

    def _cache_key(self, data_source: DataSource, config: AdjustConfig) -> str:
        """基于 Pipeline ID + 数据特征 + 配置参数生成唯一缓存键"""
        profile = data_source.describe()
        payload = {
            "pipeline": self.case_id,
            "n_samples": profile.n_samples,
            "feature_dim": profile.feature_dim,
            "params": config.params,
            "ml_params": config.ml_params,
        }
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _save_model(self, cache_key: str, model: Any) -> str:
        """保存模型到缓存目录"""
        self._MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = self._MODEL_CACHE_DIR / f"{self.case_id}_{cache_key}.pkl"
        try:
            with open(path, "wb") as f:
                pickle.dump(model, f)
            return str(path)
        except Exception:
            # PyTorch 模型用 state_dict 保存
            import torch
            pt_path = self._MODEL_CACHE_DIR / f"{self.case_id}_{cache_key}.pt"
            torch.save(model.state_dict() if hasattr(model, 'state_dict') else model, pt_path)
            return str(pt_path)

    def _load_model(self, cache_key: str, model_factory: callable = None) -> Optional[Any]:
        """从缓存加载模型，不存在返回 None"""
        pt_path = self._MODEL_CACHE_DIR / f"{self.case_id}_{cache_key}.pt"
        pkl_path = self._MODEL_CACHE_DIR / f"{self.case_id}_{cache_key}.pkl"
        try:
            if pt_path.exists() and model_factory:
                import torch
                model = model_factory()
                model.load_state_dict(torch.load(pt_path, map_location="cpu", weights_only=True))
                model.eval()
                return model
            if pkl_path.exists():
                with open(pkl_path, "rb") as f:
                    return pickle.load(f)
        except Exception:
            pass
        return None

    def _clear_model_cache(self):
        """清空当前 Pipeline 的所有缓存"""
        if not self._MODEL_CACHE_DIR.exists():
            return
        for f in self._MODEL_CACHE_DIR.glob(f"{self.case_id}_*"):
            f.unlink(missing_ok=True)

    def grid_search(self, data_source: "DataSource", param_grid: Dict[str, list],
                    base_config: "AdjustConfig" = None, progress_callback=None,
                    metric_key: str = "RMSE", method_key: str = "ml") -> List[Dict]:
        """
        参数网格搜索：自动遍历所有参数组合，找到最优配置。
        返回排序后的结果列表，第一项为最优。
        """
        import itertools
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        if not keys:
            return []

        results = []
        total = 1
        for v in values:
            total *= len(v)

        for idx, combo in enumerate(itertools.product(*values)):
            config = AdjustConfig() if base_config is None else AdjustConfig(
                test_ratio=base_config.test_ratio,
                random_seed=base_config.random_seed,
                params=dict(base_config.params),
                ml_params=dict(base_config.ml_params),
            )
            for k, v in zip(keys, combo):
                config.params[k] = v

            if progress_callback:
                progress_callback(idx / total, f"扫描 {idx+1}/{total}: {dict(zip(keys, combo))}")

            try:
                result = self.run(data_source, config)
                rmse = result.final_metrics.get(method_key, {}).get(metric_key, float("inf"))
                results.append({
                    "params": dict(zip(keys, combo)),
                    metric_key: round(rmse, 5),
                    "summary": result.summary[:200],
                })
            except Exception as e:
                results.append({
                    "params": dict(zip(keys, combo)),
                    metric_key: None,
                    "error": str(e)[:200],
                })

        results.sort(key=lambda r: r.get(metric_key, float("inf")) if r.get(metric_key) is not None else float("inf"))
        if progress_callback:
            progress_callback(1.0, f"扫描完成，最优参数: {results[0]['params'] if results else 'N/A'}")
        return results

    @staticmethod
    def compute_feature_importance(model, X: np.ndarray, y: np.ndarray,
                                     feature_names: List[str] = None,
                                     metric_fn=None, n_repeats: int = 5) -> Dict[str, float]:
        """
        Permutation-based 特征重要性分析。
        对每个特征进行随机打乱，测量模型预测误差的上升幅度。
        适用于任何模型（PyTorch / sklearn / NumPy）。
        """
        if metric_fn is None:
            def metric_fn(y_true, y_pred):
                return np.sqrt(np.mean((y_true - y_pred) ** 2))

        # Baseline prediction
        try:
            if hasattr(model, 'predict'):
                y_pred_base = model.predict(X)
            elif hasattr(model, '__call__'):
                import torch
                model.eval()
                with torch.no_grad():
                    X_t = torch.tensor(X, dtype=torch.float32)
                    y_pred_base = model(X_t).cpu().numpy().flatten()
            else:
                return {}
        except Exception:
            return {}

        baseline = metric_fn(y, y_pred_base)
        n_features = X.shape[1]
        if feature_names is None:
            feature_names = [f"f{i}" for i in range(n_features)]

        importances = {}
        for fi in range(n_features):
            scores = []
            for _ in range(n_repeats):
                X_perm = X.copy()
                np.random.shuffle(X_perm[:, fi])
                try:
                    if hasattr(model, 'predict'):
                        y_pred = model.predict(X_perm)
                    else:
                        import torch
                        with torch.no_grad():
                            X_t = torch.tensor(X_perm, dtype=torch.float32)
                            y_pred = model(X_t).cpu().numpy().flatten()
                    scores.append(metric_fn(y, y_pred))
                except Exception:
                    continue
            if scores:
                # 重要性 = 打乱后 RMSE 均值 - 基线 RMSE
                importances[feature_names[fi]] = round(np.mean(scores) - baseline, 6)

        # 归一化到 0-1
        if importances:
            max_v = max(importances.values())
            if max_v > 0:
                importances = {k: round(v / max_v, 4) for k, v in importances.items()}

        return dict(sorted(importances.items(), key=lambda x: -x[1]))
