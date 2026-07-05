"""IGS CDDIS 数据源 —— 自动下载或使用本地缓存"""

import os
import glob
import shutil
import numpy as np
from pathlib import Path
from typing import Optional, List
from ..core.base import DataSource, DataSourceType, DataProfile
from ..config import LEGACY_DATA, UPLOAD_DIR
from .igs_utils import load_troposphere_dataset, IGS_CHINA_STATIONS


class IGSTroposphereSource(DataSource):
    """从 IGS CDDIS 获取对流层数据

    优先使用本地缓存（原项目 data/ 目录），
    如指定 auto_download=True 则尝试从 CDDIS FTP 拉取。
    """

    def __init__(self, stations: List[str], days: List[int],
                 auto_download: bool = False, year: int = 2025):
        """
        Parameters:
            stations: 站点列表，如 ['BJFS', 'SHAO', 'CHAN']
            days: DOY 列表，如 [1, 91, 181, 271, 361]
            auto_download: 是否尝试从 CDDIS FTP 下载
            year: 年份
        """
        self.stations = stations
        self.days = days
        self.auto_download = auto_download
        self.year = year
        self._X: Optional[np.ndarray] = None
        self._y: Optional[np.ndarray] = None
        self._meta: dict = {}
        self._profile: Optional[DataProfile] = None

    @property
    def source_type(self) -> DataSourceType:
        return DataSourceType.IGS_CDDIS

    def load(self) -> tuple:
        tro_files = []
        met_files = []

        for doy in self.days:
            doy_str = f"{doy:03d}0"
            for st in self.stations:
                # 1. 尝试从 legacy data 目录找
                pattern = f"*{self.year % 100:02d}{doy_str[:3]}*{st}*TRO*"
                matches = glob.glob(os.path.join(str(LEGACY_DATA), pattern))
                if matches:
                    tro_files.extend(matches)

                # 气象文件
                met_pattern = f"{st.lower()}{doy_str[:3]}*.25m*"
                met_matches = glob.glob(os.path.join(str(LEGACY_DATA), met_pattern))
                if met_matches:
                    met_files.extend(met_matches)

        if not tro_files:
            raise ValueError(
                f"未找到本地对流层数据。请上传文件，"
                f"或确保 legacy data 目录包含所需数据。\n"
                f"  站点: {self.stations}\n"
                f"  DOY: {self.days}\n"
                f"  数据目录: {LEGACY_DATA}"
            )

        print(f"[IGS] 找到 {len(tro_files)} 个 TRO 文件, {len(met_files)} 个气象文件")
        self._X, self._y, self._meta = load_troposphere_dataset(
            tro_files, met_files
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

    @staticmethod
    def get_available_stations() -> List[dict]:
        """返回可用站点列表"""
        return IGS_CHINA_STATIONS
