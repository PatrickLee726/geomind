"""AI平差平台 —— FastAPI 应用入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import cases, data, jobs, results, benchmark, sweep
from .core.registry import register
from .pipelines.troposphere import TropospherePipeline
from .pipelines.gnss_network import GNSSNetworkPipeline
from .pipelines.ionosphere import IonospherePipeline
from .pipelines.elevation import ElevationPipeline
from .config import RESULT_DIR, UPLOAD_DIR

# 注册案例
register(GNSSNetworkPipeline())
register(TropospherePipeline())
register(IonospherePipeline())
register(ElevationPipeline())

app = FastAPI(
    title="测智云 GeoMind",
    description="开源可分叉的 AI 平差计算引擎",
    version="0.1.0",
)

# CORS（允许前端开发时跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(cases.router)
app.include_router(data.router)
app.include_router(jobs.router)
app.include_router(results.router)
app.include_router(benchmark.router)
app.include_router(sweep.router)


@app.get("/api/health")
async def health():
    from .core.registry import case_summaries
    return {
        "status": "ok",
        "cases": len(case_summaries()),
        "version": "0.1.0",
    }


# 静态文件：图表输出
if RESULT_DIR.exists():
    app.mount("/output", StaticFiles(directory=str(RESULT_DIR)), name="output")
