"""数据管理 API —— 上传、IGS数据源"""

import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from ..config import UPLOAD_DIR
from ..datasources.igs import IGSTroposphereSource
from ..datasources.upload import UploadedTroposphereSource, UploadedCSVSource
from ..core.base import DataProfile

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/upload/troposphere")
async def upload_troposphere(
    tro_files: list[UploadFile] = File(...),
    met_files: list[UploadFile] = File(default=[]),
):
    """上传对流层 TRO + 可选气象文件"""
    session_id = uuid.uuid4().hex[:8]
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    tro_paths = []
    for f in tro_files:
        path = session_dir / f.filename
        with open(path, "wb") as out:
            content = await f.read()
            out.write(content)
        tro_paths.append(str(path))

    met_paths = []
    for f in met_files:
        path = session_dir / f.filename
        with open(path, "wb") as out:
            content = await f.read()
            out.write(content)
        met_paths.append(str(path))

    # 验证数据
    try:
        source = UploadedTroposphereSource(tro_paths, met_paths)
        X, y, meta = source.load()
        profile = source.describe()
        return {
            "session_id": session_id,
            "type": "troposphere",
            "tro_files": [f.filename for f in tro_files],
            "met_files": [f.filename for f in met_files],
            "profile": {
                "n_samples": profile.n_samples,
                "feature_dim": profile.feature_dim,
                "stations": meta.get("stations", []),
            },
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/upload/generic")
async def upload_generic(
    file: UploadFile = File(...),
):
    """通用文件上传（IONEX、CSV等），返回文件路径"""
    session_id = uuid.uuid4().hex[:8]
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    path = session_dir / file.filename
    with open(path, "wb") as out:
        content = await file.read()
        out.write(content)

    return {
        "session_id": session_id,
        "filename": file.filename,
        "filepath": str(path),
    }


@router.post("/upload/csv")
async def upload_csv(
    file: UploadFile = File(...),
    x_cols: str = Form(default=""),
    y_col: str = Form(default=""),
):
    """上传通用 CSV 数据"""
    session_id = uuid.uuid4().hex[:8]
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    path = session_dir / file.filename
    with open(path, "wb") as out:
        content = await file.read()
        out.write(content)

    x_cols_list = [c.strip() for c in x_cols.split(",") if c.strip()] if x_cols else None
    y_col_val = y_col.strip() if y_col.strip() else None

    try:
        source = UploadedCSVSource(str(path), x_cols_list, y_col_val)
        X, y, meta = source.load()
        profile = source.describe()
        return {
            "session_id": session_id,
            "type": "csv",
            "file": file.filename,
            "filepath": str(path),
            "profile": {
                "n_samples": profile.n_samples,
                "feature_dim": profile.feature_dim,
                "feature_names": profile.feature_names,
                "elevation_range": round(profile.elevation_range, 4) if profile.elevation_range else 0,
            },
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/igs/troposphere")
async def fetch_igs_troposphere(data: dict):
    """使用 IGS CDDIS 数据（从本地缓存加载）"""
    stations = data.get("stations", ["BJFS", "SHAO", "CHAN", "WUHN", "URUM", "TWTF"])
    days = data.get("days", [1, 91, 181, 271, 361])
    year = data.get("year", 2025)

    try:
        source = IGSTroposphereSource(stations=stations, days=days, year=year)
        X, y, meta = source.load()
        profile = source.describe()
        return {
            "type": "igs_troposphere",
            "stations": stations,
            "days": days,
            "year": year,
            "profile": {
                "n_samples": profile.n_samples,
                "feature_dim": profile.feature_dim,
                "stations": meta.get("stations", []),
            },
            "meta": {
                "stations": meta.get("stations", []),
                "n_total": meta.get("n_total", 0),
            },
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/igs/stations")
async def get_igs_stations():
    """获取可用 IGS 站点列表"""
    return {"stations": IGSTroposphereSource.get_available_stations()}
