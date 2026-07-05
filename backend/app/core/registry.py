"""案例注册中心"""

from typing import Dict, Type
from .base import Pipeline

_registry: Dict[str, Pipeline] = {}


def register(pipeline: Pipeline) -> Pipeline:
    """注册一个案例 Pipeline"""
    _registry[pipeline.case_id] = pipeline
    return pipeline


def get(case_id: str) -> Pipeline:
    """获取案例 Pipeline"""
    if case_id not in _registry:
        raise KeyError(f"案例 '{case_id}' 未注册。可用: {list(_registry.keys())}")
    return _registry[case_id]


def list_all() -> Dict[str, Pipeline]:
    """列出所有已注册案例"""
    return dict(_registry)


def case_summaries() -> list:
    """获取所有案例的摘要信息（供前端首页展示）"""
    return [
        {
            "id": p.case_id,
            "name": p.case_name,
            "description": p.description,
        }
        for p in _registry.values()
    ]
