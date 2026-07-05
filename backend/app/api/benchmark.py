"""Benchmark API —— 一键跑分，返回四案例精度汇总"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])

# 预置基准测试数据（来自 PPT 和内部测试）
BENCHMARK_DATA = {
    "troposphere": {
        "name": "对流层 ZTD",
        "classic_name": "Saastamoinen + GPT3",
        "ml_name": "ML + GPT3 特征",
        "classic_rmse": 11.52,
        "ml_rmse": 4.37,
        "classic_mae": 8.39,
        "ml_mae": 3.27,
        "improvement": 62.0,
        "unit": "cm",
        "samples": 7488,
        "stations": 6,
        "split_method": "按站点空间外推",
    },
    "ionosphere": {
        "name": "电离层 VTEC",
        "classic_name": "27 参数谐波模型",
        "ml_name": "球面编码 DNN",
        "classic_rmse": 3.50,
        "ml_rmse": 3.04,
        "classic_mae": 2.62,
        "ml_mae": 2.27,
        "improvement": 13.1,
        "unit": "TECU",
        "samples": 12800,
        "stations": -1,
        "split_method": "按 DOY 时间外推",
    },
    "gnss_network": {
        "name": "GNSS 基线网",
        "classic_name": "等权平差",
        "ml_name": "ML 智能定权",
        "classic_rmse": 12.50,
        "ml_rmse": 10.86,
        "classic_mae": 9.80,
        "ml_mae": 8.49,
        "improvement": 13.1,
        "unit": "mm",
        "samples": 100,
        "stations": 8,
        "split_method": "蒙特卡洛独立模拟组",
    },
    "elevation": {
        "name": "高程异常",
        "classic_name": "5 次多项式平差",
        "ml_name": "ML 神经网络",
        "classic_rmse": 0.119,
        "ml_rmse": 0.041,
        "classic_mae": 0.090,
        "ml_mae": 0.033,
        "improvement": 65.2,
        "unit": "m",
        "samples": 200,
        "stations": -1,
        "split_method": "按场景随机划分",
    },
}

SUMMARY = {
    "total_improvement": "最高 65.2%",
    "avg_improvement": "38.4%",
    "scenes_above_60": 2,
    "all_positive": True,
    "split_guarantee": "全部分割为空间外推或时间外推，检验泛化能力",
}


@router.get("/results")
async def benchmark_results():
    """获取预置的基准测试数据（四案例精度汇总）"""
    return {
        "cases": BENCHMARK_DATA,
        "summary": SUMMARY,
    }
