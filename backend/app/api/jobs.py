"""任务提交和状态查询 API"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..services.job_manager import job_manager
from ..core.registry import get as get_pipeline
from ..core.base import AdjustConfig
from ..datasources.upload import UploadedTroposphereSource, UploadedCSVSource
from ..datasources.igs import IGSTroposphereSource
from ..config import UPLOAD_DIR
from ..core.base import DataSource, DataSourceType, DataProfile


class _IonexFileSource(DataSource):
    """IONEX文件数据源包装"""
    def __init__(self, filepaths: list):
        self.filepaths = filepaths
    @property
    def source_type(self):
        return DataSourceType.UPLOAD
    def load(self):
        return None, None, {"filepaths": self.filepaths}
    def describe(self):
        return DataProfile(n_samples=0, feature_dim=0)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("")
async def submit_job(data: dict):
    """提交计算任务

    请求体:
    {
        "case_id": "troposphere",
        "data_source": {
            "type": "igs_troposphere",
            "stations": ["BJFS", "SHAO", ...],
            "days": [1, 91, 181, 271, 361],
            "year": 2025
        },
        "config": {
            "test_ratio": 0.2,
            "ml_hidden_dims": "128,256,128,64",
            ...
        }
    }
    """
    case_id = data.get("case_id")
    ds_config = data.get("data_source", {})
    config_data = data.get("config", {})

    job = job_manager.create(case_id)

    try:
        pipeline = get_pipeline(case_id)
    except KeyError:
        job_manager.update(job.id, status="failed", error=f"未知案例: {case_id}")
        return JSONResponse({"error": f"未知案例: {case_id}"}, status_code=404)

    # 数据源：纯模拟案例（如 GNSS）不需要
    source = None
    if ds_config and ds_config.get("type"):
        try:
            source = _build_data_source(ds_config)
        except Exception as e:
            job_manager.update(job.id, status="failed", error=f"数据源错误: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    # 配置：把所有参数原样传入 params
    adjust_config = AdjustConfig(
        params=config_data,
    )

    # 提交异步执行
    job_manager.run_async(
        job,
        pipeline.run,
        (source, adjust_config, job_manager.progress_callback(job.id)),
    )

    return {
        "job_id": job.id,
        "case_id": case_id,
        "status": "pending",
        "message": "任务已提交",
    }


@router.get("/{job_id}")
async def get_job(job_id: str):
    """查询任务状态和结果"""
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    response = {
        "job_id": job.id,
        "case_id": job.case_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "created_at": job.created_at,
        "error": job.error,
    }

    if job.status == "done" and job.result:
        result = job.result
        response["result"] = {
            "summary": result.summary,
            "final_metrics": result.final_metrics,
            "charts": result.charts,
        }

    return response


@router.get("")
async def list_jobs():
    """列出所有任务"""
    return {"jobs": job_manager.list_all()}


def _build_data_source(ds_config: dict):
    """根据配置构建数据源"""
    ds_type = ds_config.get("type", "")

    if ds_type == "igs_troposphere":
        return IGSTroposphereSource(
            stations=ds_config.get("stations", ["BJFS", "SHAO", "CHAN", "WUHN", "URUM", "TWTF"]),
            days=ds_config.get("days", [1, 91, 181, 271, 361]),
            year=ds_config.get("year", 2025),
        )

    elif ds_type == "uploaded_troposphere":
        session_id = ds_config.get("session_id")
        if not session_id:
            raise ValueError("缺少 session_id")
        session_dir = UPLOAD_DIR / session_id
        import glob
        tro_files = glob.glob(str(session_dir / "*.TRO*"))
        met_files = glob.glob(str(session_dir / "*.25m*"))
        return UploadedTroposphereSource(tro_files, met_files)

    elif ds_type == "uploaded_csv":
        filepath = ds_config.get("filepath")
        x_cols = ds_config.get("x_cols")
        y_col = ds_config.get("y_col")
        return UploadedCSVSource(filepath, x_cols=x_cols, y_col=y_col)

    elif ds_type == "uploaded_ionex":
        filepaths = ds_config.get("filepaths", [])
        # 简单包装，把文件路径暴露给 pipeline
        return _IonexFileSource(filepaths)

    else:
        raise ValueError(f"不支持的数据源类型: {ds_type}")
