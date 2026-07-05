"""参数扫描 API —— 网格搜索最优超参数"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import threading

from ..core.registry import list_all
from ..core.base import AdjustConfig

router = APIRouter(prefix="/api/sweep", tags=["sweep"])

# 内存存储扫描结果
sweep_store: Dict[str, dict] = {}
sweep_counter = 0
sweep_lock = threading.Lock()


class SweepRequest(BaseModel):
    case_id: str
    param_grid: Dict[str, list]
    base_params: Dict[str, object] = {}


@router.post("/start")
async def start_sweep(req: SweepRequest):
    """启动参数扫描任务"""
    global sweep_counter

    pipeline = list_all().get(req.case_id)
    if pipeline is None:
        raise HTTPException(404, f"案例 '{req.case_id}' 不存在")

    with sweep_lock:
        sweep_counter += 1
        sid = f"sweep_{sweep_counter}"
        sweep_store[sid] = {"status": "running", "progress": 0, "results": None, "error": None}

    # 用默认数据源启动
    try:
        ds = _get_demo_source(req.case_id)
    except Exception as e:
        sweep_store[sid] = {"status": "failed", "error": f"无法加载默认数据: {e}"}
        return {"sweep_id": sid, "status": "failed"}

    base_config = AdjustConfig(params=req.base_params)

    def _run():
        try:
            grid = req.param_grid
            # Filter to valid keys present in pipeline config
            schema = pipeline.config_schema()
            valid_keys = set(schema.get("properties", {}).keys())
            filtered_grid = {k: v for k, v in grid.items() if k in valid_keys}
            if not filtered_grid:
                sweep_store[sid] = {"status": "done", "results": [], "message": "没有有效参数可扫描"}
                return

            results = pipeline.grid_search(
                data_source=ds,
                param_grid=filtered_grid,
                base_config=base_config,
                progress_callback=lambda p, msg: _update(sid, p, msg),
            )
            sweep_store[sid] = {"status": "done", "results": results, "progress": 1.0}
        except Exception as e:
            sweep_store[sid] = {"status": "failed", "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return {"sweep_id": sid, "status": "running"}


@router.get("/status/{sweep_id}")
async def sweep_status(sweep_id: str):
    """查询扫描任务状态"""
    if sweep_id not in sweep_store:
        raise HTTPException(404, "扫描任务不存在")
    return sweep_store[sweep_id]


def _update(sid: str, progress: float, message: str):
    if sid in sweep_store:
        sweep_store[sid]["progress"] = progress


def _get_demo_source(case_id: str):
    """为参数扫描提供默认数据源"""
    from ..core.base import DataSourceType

    class DemoSource:
        def __init__(self, cid):
            self.cid = cid

        def load(self):
            if self.cid == "troposphere":
                import importlib.util
                spec = importlib.util.spec_from_file_location("igs", __file__)
                # Fallback: generate simple synthetic data
                import numpy as np
                np.random.seed(42)
                X = np.random.randn(200, 8)
                y = np.random.randn(200) * 0.1 + 2.3
                return X, y, {"stations": ["DEMO"]}
            elif self.cid == "ionosphere":
                import numpy as np
                np.random.seed(42)
                X = np.random.randn(500, 10)
                y = np.random.randn(500) * 5 + 20
                return X, y, {}
            elif self.cid == "gnss":
                import numpy as np
                np.random.seed(42)
                X = np.random.randn(150, 14)
                y = np.random.randn(150) * 0.005 + 0.01
                return X, y, {}
            elif self.cid == "elevation":
                import numpy as np
                np.random.seed(42)
                X = np.random.randn(200, 2)
                # Nonlinear terrain
                y = 0.1 * np.sin(X[:, 0] * 3) + 0.05 * (X[:, 1] ** 2) + np.random.randn(200) * 0.01
                return X, y, {}
            return np.random.randn(100, 5), np.random.randn(100), {}

        def describe(self):
            from ..core.base import DataProfile
            return DataProfile(n_samples=200, feature_dim=8, feature_names=[f"f{i}" for i in range(8)])

        @property
        def source_type(self):
            return DataSourceType.SIMULATED

    return DemoSource(case_id)
