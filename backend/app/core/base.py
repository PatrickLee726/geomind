"""核心抽象接口：DataSource / Pipeline / Model"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import numpy as np


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
