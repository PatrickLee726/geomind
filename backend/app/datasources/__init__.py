"""数据源层

支持三种数据来源:
- 文件上传 (UploadedTroposphereSource / UploadedCSVSource)
- IGS CDDIS 自动获取 (IGSTroposphereSource)
- 模拟数据生成 (预留)
"""
from .upload import UploadedTroposphereSource, UploadedCSVSource
from .igs import IGSTroposphereSource
