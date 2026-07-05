"""平台配置"""

import os
from pathlib import Path

# BASE_DIR: 项目根目录。本地开发时自动推断，Docker 内通过 BASE_DIR 环境变量指定
BASE_DIR = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent.parent.parent))
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"
MODEL_DIR = DATA_DIR / "models"
DB_PATH = DATA_DIR / "platform.db"

for d in [UPLOAD_DIR, RESULT_DIR, MODEL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# IGS CDDIS FTP 配置
CDDIS_BASE = "ftp://gdc.cddis.eosdis.nasa.gov/gnss/products"
TROPO_PATH = f"{CDDIS_BASE}/troposphere/zpd"
IONEX_PATH = f"{CDDIS_BASE}/ionex"

LEGACY_DATA = Path(os.environ.get("LEGACY_DATA_DIR", BASE_DIR / "legacy_data"))
