"""案例 API"""

from fastapi import APIRouter
from ..core.registry import list_all, case_summaries

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
async def get_cases():
    """获取所有案例列表"""
    return {
        "cases": case_summaries(),
    }


@router.get("/{case_id}")
async def get_case(case_id: str):
    """获取案例详情和配置 Schema"""
    pipeline = list_all().get(case_id)
    if pipeline is None:
        return {"error": f"案例 '{case_id}' 不存在", "available": [c["id"] for c in case_summaries()]}, 404

    return {
        "id": pipeline.case_id,
        "name": pipeline.case_name,
        "description": pipeline.description,
        "schema": pipeline.config_schema(),
    }


@router.get("/{case_id}/schema")
async def get_case_schema(case_id: str):
    """获取案例配置 JSON Schema（前端动态表单）"""
    pipeline = list_all().get(case_id)
    if pipeline is None:
        return {"error": f"案例 '{case_id}' 不存在"}, 404
    return pipeline.config_schema()
