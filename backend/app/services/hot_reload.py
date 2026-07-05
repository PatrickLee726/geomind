"""Pipeline 热加载服务 —— 监控 pipelines 目录，自动注册新文件"""

import os
import importlib.util
import threading
import time
from pathlib import Path
from typing import Set
import logging

logger = logging.getLogger("hot_reload")

PIPELINES_DIR = Path(__file__).resolve().parent.parent / "pipelines"
KNOWN_FILES: Set[str] = set()
_lock = threading.Lock()
_watcher_running = False


def _import_pipeline(filepath: Path):
    """从 .py 文件动态导入 Pipeline 类"""
    module_name = f"dynamic_{filepath.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 查找文件中继承 Pipeline 的类
        from ..core.base import Pipeline
        from ..core.registry import register

        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if (
                isinstance(obj, type)
                and issubclass(obj, Pipeline)
                and obj is not Pipeline
            ):
                instance = obj()
                register(instance)
                logger.info(f"热加载 Pipeline: {instance.case_id} ({instance.case_name}) from {filepath.name}")
                return instance
    except Exception as e:
        logger.warning(f"热加载失败 {filepath.name}: {e}")
    return None


def _scan_and_load():
    """扫描 pipelines 目录，加载新文件"""
    global KNOWN_FILES
    if not PIPELINES_DIR.exists():
        return

    current_files = set()
    for f in PIPELINES_DIR.iterdir():
        if f.suffix == ".py" and not f.name.startswith("_"):
            current_files.add(f.name)
            if f.name not in KNOWN_FILES:
                _import_pipeline(f)

    with _lock:
        KNOWN_FILES = current_files


def start_watcher(interval: float = 3.0):
    """启动后台热加载线程"""
    global _watcher_running
    if _watcher_running:
        return

    # 首次全量扫描
    _scan_and_load()
    _watcher_running = True

    def _loop():
        while _watcher_running:
            time.sleep(interval)
            try:
                _scan_and_load()
            except Exception as e:
                logger.error(f"热加载扫描异常: {e}")

    t = threading.Thread(target=_loop, daemon=True, name="pipeline-hot-reload")
    t.start()
    logger.info(f"Pipeline 热加载已启动，监控目录: {PIPELINES_DIR}")


def stop_watcher():
    global _watcher_running
    _watcher_running = False


def get_loaded_pipelines() -> list:
    from ..core.registry import case_summaries
    return case_summaries()
