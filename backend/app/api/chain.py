"""Pipeline 链式调用 API"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import threading

from ..core.chain import PipelineChain, ChainStep

router = APIRouter(prefix="/api/chain", tags=["chain"])

chain_store: Dict[str, dict] = {}
chain_counter = 0
chain_lock = threading.Lock()


class ChainRequest(BaseModel):
    steps: List[dict]  # [{case_id, config, depends_on}]


@router.post("/start")
async def start_chain(req: ChainRequest):
    global chain_counter
    try:
        steps = [ChainStep(**s) for s in req.steps]
    except Exception as e:
        raise HTTPException(400, f"无效的链式步骤: {e}")

    with chain_lock:
        chain_counter += 1
        cid = f"chain_{chain_counter}"
        chain_store[cid] = {"status": "running", "results": None, "error": None}

    def _run():
        try:
            chain = PipelineChain(steps)
            chain.run()
            chain_store[cid] = {"status": "done", "results": chain.summary()}
        except Exception as e:
            chain_store[cid] = {"status": "failed", "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return {"chain_id": cid, "status": "running"}


@router.get("/status/{chain_id}")
async def chain_status(chain_id: str):
    if chain_id not in chain_store:
        raise HTTPException(404, "链式任务不存在")
    return chain_store[chain_id]
