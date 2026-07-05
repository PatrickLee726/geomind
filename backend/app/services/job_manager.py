"""异步任务管理器 —— 使用 FastAPI BackgroundTasks"""

import uuid
import threading
from typing import Dict, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from ..core.base import PipelineResult


@dataclass
class Job:
    """任务记录"""
    id: str
    case_id: str
    status: str = "pending"  # pending / running / done / failed
    progress: float = 0.0
    message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    result: Optional[PipelineResult] = None
    error: Optional[str] = None


class JobManager:
    """内存中的任务管理器（单用户本地部署，无需数据库）"""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, case_id: str) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, case_id=case_id)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def update(self, job_id: str, **kwargs):
        with self._lock:
            if job_id in self._jobs:
                for k, v in kwargs.items():
                    setattr(self._jobs[job_id], k, v)

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_all(self) -> list:
        with self._lock:
            return [
                {
                    "id": j.id,
                    "case_id": j.case_id,
                    "status": j.status,
                    "progress": j.progress,
                    "message": j.message,
                    "created_at": j.created_at,
                    "error": j.error,
                }
                for j in self._jobs.values()
            ]

    def run_async(self, job: Job, target: Callable, args: tuple = ()):
        """在后台线程中执行任务"""
        def _run():
            self.update(job.id, status="running", message="任务执行中...")
            try:
                result = target(*args)
                self.update(job.id, status="done", progress=1.0,
                           message="完成", result=result)
            except Exception as e:
                self.update(job.id, status="failed", error=str(e),
                           message=f"失败: {str(e)}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def progress_callback(self, job_id: str):
        """返回一个可用于 Pipeline 的进度回调"""
        def cb(info: dict):
            self.update(
                job_id,
                message=info.get("message", ""),
                progress=min(0.95, self._jobs[job_id].progress + 0.1),
            )
        return cb


# 全局单例
job_manager = JobManager()
