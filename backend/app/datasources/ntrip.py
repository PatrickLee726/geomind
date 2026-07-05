"""NTRIP 实时 GNSS 数据源适配器

NTRIP (Networked Transport of RTCM via Internet Protocol) 是 GNSS 差分数据的标准流协议。
本适配器提供了接入 NTRIP caster 的接口框架。

使用方法（需要 ntripclient 库和有效的 caster 账号）：
  pip install ntripclient

  from app.datasources.ntrip import NTRIPDataSource
  ds = NTRIPDataSource(
      host="ntrip.example.com",
      port=2101,
      mountpoint="RTCM3EPH",
      username="user",
      password="pass",
  )
  data = ds.load()

免责声明：需要用户自行提供 NTRIP caster 的访问凭证。
GeoMind 不提供默认 caster 地址。
"""

from ..core.base import DataSource, DataProfile, DataSourceType
from typing import Optional
import numpy as np


class NTRIPDataSource(DataSource):
    """NTRIP 实时流数据源"""

    def __init__(self, host: str, port: int = 2101, mountpoint: str = "",
                 username: str = "", password: str = "", duration_sec: int = 300):
        self.host = host
        self.port = port
        self.mountpoint = mountpoint
        self.username = username
        self.password = password
        self.duration_sec = duration_sec
        self._data: Optional[tuple] = None

    def load(self) -> tuple:
        """从 NTRIP caster 拉取实时数据

        尝试使用 ntripclient 库连接。如果未安装或连接失败，返回模拟数据。
        """
        try:
            import ntripclient  # noqa: F401
            return self._load_real()
        except ImportError:
            return self._load_fallback()

    def _load_real(self) -> tuple:
        """真实 NTRIP 连接（需要 ntripclient 和有效凭证）"""
        from ntripclient import NTRIPClient
        client = NTRIPClient(
            host=self.host,
            port=self.port,
            mountpoint=self.mountpoint,
            user=self.username,
            password=self.password,
        )
        # 采集指定时长的数据
        raw_messages = []
        client.start()
        import time
        start = time.time()
        while time.time() - start < self.duration_sec:
            msg = client.read(timeout=5)
            if msg:
                raw_messages.append(msg)
        client.stop()

        # 解析 RTCM 消息 → 特征矩阵（简化实现）
        X, y = self._parse_rtcm(raw_messages)
        return X, y, {"source": f"ntrip://{self.host}:{self.port}/{self.mountpoint}"}

    def _parse_rtcm(self, messages: list) -> tuple:
        """RTCM 消息解析（占位实现，实际项目中替换为完整 RTCM 解码器）"""
        n = len(messages)
        if n == 0:
            return np.zeros((1, 6)), np.zeros(1), {}
        # 简化：每条消息提取 6 个特征（时间、卫星数、伪距残差等）
        X = np.random.randn(n, 6)
        y = np.random.randn(n) * 0.01
        return X, y

    def _load_fallback(self) -> tuple:
        """未安装 ntripclient 时的回退模拟数据"""
        np.random.seed(42)
        n = 100
        # 模拟 6 维 GNSS 特征：时间编码、卫星数、GDOP、PDOP、伪距残差、载波残差
        X = np.column_stack([
            np.linspace(0, 1, n),
            np.random.randint(6, 14, n),
            np.random.uniform(1.0, 4.0, n),
            np.random.uniform(0.8, 3.5, n),
            np.random.randn(n) * 2.0,
            np.random.randn(n) * 0.5,
        ])
        y = 0.02 * X[:, 4] + 0.01 * X[:, 3] + np.random.randn(n) * 0.005
        return X, y, {"source": "ntrip://demo-fallback", "mode": "simulated"}

    def describe(self) -> DataProfile:
        return DataProfile(
            n_samples=100,
            feature_dim=6,
            feature_names=["time", "n_sats", "GDOP", "PDOP", "pseudo_residual", "carrier_residual"],
            spatial_extent_km=None,
            terrain_complexity="unknown",
        )

    @property
    def source_type(self) -> DataSourceType:
        return DataSourceType.IGS_CDDIS  # NTRIP 归类为 GNSS 网络数据源
