"""后端启动测试 —— 验证所有模块可以正确导入和运行"""

import sys
sys.path.insert(0, ".")

print("=" * 60)
print("AI平差平台 - 后端测试")
print("=" * 60)

# 1. 测试基础导入
print("\n[1] 基础模块导入...")
from app.core.base import Pipeline, DataSource, AdjustConfig, PipelineResult, StepResult
from app.core.registry import register, get, list_all, case_summaries
print("  ✓ core 模块")

# 2. 测试数据源
print("\n[2] 数据源模块...")
from app.datasources.igs import IGSTroposphereSource
from app.datasources.upload import UploadedTroposphereSource, UploadedCSVSource
from app.datasources.igs_utils import (
    parse_tro_file, parse_rinex_met, gpt3_pressure_temp, saastamoinen_ztd,
    load_troposphere_dataset,
)
print("  ✓ 数据源和工具函数")

# 3. 测试 Pipeline
print("\n[3] Pipeline 模块...")
from app.pipelines.troposphere import TropospherePipeline
pipeline = TropospherePipeline()
print(f"  ✓ {pipeline.case_name} (id={pipeline.case_id})")
print(f"  配置项: {list(pipeline.config_schema()['properties'].keys())}")

# 4. 测试注册
print("\n[4] 注册中心...")
register(pipeline)
summaries = case_summaries()
print(f"  已注册案例: {len(summaries)} 个")
for s in summaries:
    print(f"    - {s['id']}: {s['name']}")

# 5. 测试 IGS 数据加载 (如果 legacy data 存在)
print("\n[5] IGS 数据加载测试...")
import os
legacy_data = r"E:\OH-WorkPlace\package_前端交付\package_前端交付\data"
if os.path.isdir(legacy_data):
    import glob
    tro_files = glob.glob(os.path.join(legacy_data, "*.TRO*"))
    met_files = glob.glob(os.path.join(legacy_data, "*.25m*"))
    print(f"  TRO 文件: {len(tro_files)} 个")
    print(f"  气象文件: {len(met_files)} 个")

    if tro_files:
        try:
            X, y, meta = load_troposphere_dataset(tro_files[:2], met_files[:2] if met_files else None)
            print(f"  ✓ 成功加载: {len(y)} 条记录, {meta['stations']}")
            print(f"  特征维度: {X.shape}, ZTD范围: [{y.min():.2f}, {y.max():.2f}]")
        except Exception as e:
            print(f"  ✗ 加载失败: {e}")
    else:
        print("  (无 TRO 文件)")
else:
    print(f"  (legacy data 目录不存在: {legacy_data})")

# 6. 测试 FastAPI 应用
print("\n[6] FastAPI 应用...")
from app.main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
print(f"  ✓ 应用创建成功, {len(routes)} 条路由")
for r in routes[:15]:
    print(f"    {r}")

print("\n" + "=" * 60)
print("所有模块加载成功! 运行方式:")
print("  cd backend && uvicorn app.main:app --reload --port 8000")
print("=" * 60)
