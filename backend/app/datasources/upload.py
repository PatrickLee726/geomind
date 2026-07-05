"""文件上传数据源"""

import os
import glob
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, List
from ..core.base import DataSource, DataSourceType, DataProfile
from .igs_utils import load_troposphere_dataset, parse_tro_file


class UploadedTroposphereSource(DataSource):
    """对流程案例专用：上传 TRO + 可选气象文件"""

    def __init__(self, tro_paths: List[str], met_paths: Optional[List[str]] = None):
        self.tro_paths = tro_paths
        self.met_paths = met_paths or []
        self._X: Optional[np.ndarray] = None
        self._y: Optional[np.ndarray] = None
        self._meta: dict = {}
        self._profile: Optional[DataProfile] = None

    @property
    def source_type(self) -> DataSourceType:
        return DataSourceType.UPLOAD

    def load(self) -> tuple:
        self._X, self._y, self._meta = load_troposphere_dataset(
            self.tro_paths, self.met_paths
        )
        return self._X, self._y, self._meta

    def describe(self) -> DataProfile:
        if self._profile is None:
            self.load()
        self._profile = DataProfile(
            n_samples=self._X.shape[0],
            feature_dim=self._X.shape[1],
            feature_names=self._meta.get('feature_names', []),
            elevation_range=float(self._y.max() - self._y.min()),
        )
        return self._profile


class UploadedCSVSource(DataSource):
    """通用 CSV 数据源"""

    def __init__(self, filepath: str, x_cols: Optional[List[str]] = None,
                 y_col: Optional[str] = None):
        self.filepath = Path(filepath)
        self._x_cols = x_cols
        self._y_col = y_col
        self._X: Optional[np.ndarray] = None
        self._y: Optional[np.ndarray] = None
        self._meta: dict = {}
        self._profile: Optional[DataProfile] = None

        if not self.filepath.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")

    @property
    def source_type(self) -> DataSourceType:
        return DataSourceType.UPLOAD

    def load(self) -> tuple:
        df = pd.read_csv(self.filepath)
        if self._y_col is None:
            self._y_col = df.columns[-1]
        if self._x_cols is None:
            self._x_cols = [c for c in df.columns if c != self._y_col]
        self._X = df[self._x_cols].values.astype(np.float64)
        self._y = df[self._y_col].values.astype(np.float64)
        self._meta = {"feature_names": self._x_cols, "target_name": self._y_col}
        self._profile = DataProfile(
            n_samples=len(self._X),
            feature_dim=self._X.shape[1],
            feature_names=list(self._x_cols),
            elevation_range=float(self._y.max() - self._y.min()),
        )
        return self._X, self._y, self._meta

    def describe(self) -> DataProfile:
        if self._profile is None:
            self.load()
        return self._profile
