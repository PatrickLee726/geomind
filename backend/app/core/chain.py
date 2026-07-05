"""跨案例 Pipeline 链式调用

允许将一个 Pipeline 的输出作为另一个 Pipeline 的输入，形成数据处理链路。
例如：对流层 ZTD 校正 → GNSS 基线网平差（使用校正后的观测值）。
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import threading


@dataclass
class ChainStep:
    """链式调用中的每一步"""
    case_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: Optional[int] = None  # 依赖上一步的索引（None = 依赖前一步）


class PipelineChain:
    """Pipeline 链式执行器"""

    def __init__(self, steps: List[ChainStep], progress_callback: Callable = None):
        self.steps = steps
        self.progress_callback = progress_callback
        self.results: List[Any] = []
        self._lock = threading.Lock()

    def run(self) -> List[Any]:
        """顺序执行 Pipeline 链，每步的输出传递给下一步"""
        from ..core.registry import list_all

        registry = list_all()
        prev_data = None

        for i, step in enumerate(self.steps):
            pipeline = registry.get(step.case_id)
            if pipeline is None:
                raise ValueError(f"案例 '{step.case_id}' 未注册")

            if self.progress_callback:
                self.progress_callback(i / len(self.steps),
                                       f"链式执行 {i+1}/{len(self.steps)}: {pipeline.case_name}")

            from ..core.base import AdjustConfig

            # 如果有上游数据，注入到 config
            config = AdjustConfig(params=dict(step.config))
            if prev_data is not None:
                config.params["_chain_input"] = prev_data

            result = pipeline.run(None, config)  # 数据源由 Pipeline 内部处理
            with self._lock:
                self.results.append(result)
            prev_data = result

        return self.results

    def summary(self) -> Dict[str, Any]:
        """返回链式调用的汇总信息"""
        return {
            "total_steps": len(self.steps),
            "completed": len(self.results),
            "steps": [
                {
                    "case_id": r.case_id,
                    "summary": r.summary[:200],
                    "metrics": r.final_metrics,
                }
                for r in self.results
            ],
        }
