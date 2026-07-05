"""结果查询 API"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from ..services.job_manager import job_manager
from ..config import RESULT_DIR

router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("/{job_id}")
async def get_result(job_id: str):
    """获取任务完整结果"""
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status != "done":
        raise HTTPException(status_code=400, detail=f"任务未完成，当前状态: {job.status}")
    if job.result is None:
        raise HTTPException(status_code=404, detail="结果不可用")

    return {
        "job_id": job.id,
        "case_id": job.case_id,
        "summary": job.result.summary,
        "final_metrics": job.result.final_metrics,
        "charts": job.result.charts,
        "steps": [
            {
                "name": s.name,
                "status": s.status,
                "metrics": s.metrics,
                "artifacts": s.artifacts,
                "error": s.error,
            }
            for s in job.result.steps
        ],
    }


@router.get("/{job_id}/chart/{name}")
async def get_chart(job_id: str, name: str):
    """获取图表文件"""
    job = job_manager.get(job_id)
    if job is None or job.result is None:
        raise HTTPException(status_code=404, detail="任务或结果不存在")

    charts = job.result.charts
    if name not in charts:
        # 尝试模糊匹配
        for k in charts:
            if name in k:
                name = k
                break
        else:
            raise HTTPException(status_code=404, detail=f"图表 '{name}' 不存在")

    rel_path = charts[name]
    abs_path = RESULT_DIR.parent / rel_path
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail=f"图表文件不存在: {abs_path}")

    return FileResponse(abs_path, media_type="image/png")
