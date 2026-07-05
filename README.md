# 测智云 GeoMind —— 开源可分叉的 AI 平差计算引擎

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org/)
[![Vue 3](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)

**让每一条观测都获得 AI 的最优权重。**

GeoMind 是一个将机器学习引入测绘平差领域的开源计算引擎。它不替代经典大地测量模型，而是在经典框架内部嵌入数据驱动的智能：自动学习每条基线的最优权重、自动捕捉非线性地形特征、自动填补经验公式在复杂场景下的精度缺口。

---

## 为什么 GeoMind？

经典测绘平差软件（科傻 COSA、中海达 HGO）都是闭源黑箱。用户输入数据、得到结果，但不清楚内部定权逻辑，也无法针对自有数据调整模型。GeoMind 的核心差异：

| | 经典商业软件 | GeoMind |
|---|---|---|
| **代码透明性** | 闭源，黑箱 | 开源 MIT，每一行可审计 |
| **定权策略** | 固定规则，人工预设 | AI 从 14 维基线特征自学习 |
| **非线性建模** | 多项式基函数，容量有限 | 神经网络，自动适配复杂场景 |
| **可扩展性** | 不可修改 | Fork → 加新 Pipeline → PR 回归 |
| **适用场景** | 标准化外业平差 | 标准化 + 异常/复杂/突变场景 |

---

## 四大场景，四条 ML 路线

| 场景 | 经典方法痛点 | ML 方案 | 精度提升 |
|------|-------------|---------|---------|
| **对流层 ZTD** | GPT3 气象估算引入 14 cm 偏差 | 神经网络从时空特征学习残差映射 | **62%** |
| **电离层 VTEC** | 谐波模型无法捕捉赤道异常突变 | 球面编码 + 四层全连接网络 | ~13% |
| **GNSS 基线网** | 等权/经验定权，粗差不鲁棒 | 14 维特征 → 自适应权值预测 | ~13% |
| **高程异常** | 多项式无法表达陡坎与凹陷 | ReLU 激活天然适配分段线性地形 | **65.2%** |

所有分割均为按站点或按 DOY 空间外推，检验泛化能力而非内插。

## 🏆 基准跑分

| 指标 | 数值 |
|------|------|
| 验证场景 | **4** 个 GNSS 核心问题 |
| 最高精度提升 | **65.2%**（高程异常） |
| 平均精度提升 | **38.4%**（四场景综合） |
| 正向提升率 | **4/4**，全部优于经典方法 |
| 外推策略 | 按站点 / 按 DOY / 独立模拟组 / 随机划分 |

启动平台后访问 `/benchmark` 查看完整精度仪表盘。

---

## 快速开始

**前提：** Windows / Linux / macOS，Python 3.9+，Node.js 24+。

```bash
# 1. 克隆仓库
git clone https://github.com/PatrickLee726/geomind.git
cd geomind

# 2. 安装后端依赖
cd backend && pip install -r requirements.txt

# 3. 安装前端依赖
cd ../frontend && npm install

# 4. 一键启动（Windows）
双击 启动平台.bat

# 或手动启动
cd backend && uvicorn app.main:app --port 8000   # 终端1
cd frontend && npm run dev                        # 终端2

# 浏览器打开 http://localhost:5173
```

后端 API 文档自动生成：http://localhost:8000/docs

---

## 可分叉架构

GeoMind 的 Pipeline 框架天然支持 Fork & Extend：

```
你 Fork 仓库
    │
    ├── 改参数：调整 Pipeline 中的网络结构、学习率
    ├── 加数据：接入自有 CORS 站或 NTRIP 实时流
    ├── 加场景：新建 Pipeline（PPP、轨道拟合、多系统融合...）
    │
    └── PR 回归：通用性强的贡献，合并回主线
```

每个 Pipeline 只需实现五个接口：`case_id`、`case_name`、`config_schema()`、`run()`、`description`。前端表单由 JSON Schema 自动驱动渲染，新增案例无需改一行前端代码。

详见 [贡献指南](CONTRIBUTING.md)。

---

## 项目结构

```
geomind/
├── backend/
│   ├── app/
│   │   ├── core/           # Pipeline 基类 + 注册中心（可分叉的接口合约）
│   │   ├── pipelines/      # 4 个内置 Pipeline，可作为新案例模板
│   │   ├── datasources/    # DataSource 抽象（IGS CDDIS、文件上传、模拟生成）
│   │   ├── api/            # FastAPI REST 路由
│   │   └── services/       # 异步任务管理
│   └── requirements.txt
├── frontend/               # Vue 3 + ECharts，Schema 驱动动态表单
├── legacy_data/            # 本地缓存样例数据（离线可用）
├── .gitignore
├── LICENSE                 # MIT
├── CONTRIBUTING.md
└── README.md
```

---

## 技术栈

| 层 | 技术 | 用途 |
|---|------|------|
| 数值计算 | NumPy | 最小二乘、矩阵求逆 |
| 深度学习 | PyTorch 2.x | 所有 ML 管线（CPU 可用） |
| 后端 | FastAPI | REST API + 自动文档 |
| 前端 | Vue 3 + Vite | 动态表单 + ECharts 可视化 |
| 数据 | IGS CDDIS | 全球 GNSS 精密产品 |

---

## 开源许可

MIT License · 详见 [LICENSE](LICENSE)

你可以自由使用、修改、分发，包括用于商业场景。我们只要求保留版权声明。

---

## 路线图

- [x] 四大场景经典 vs ML 对比
- [x] Pipeline 插件化框架
- [x] 本地一键启动
- [x] 开源 Git 仓库 + MIT 许可
- [ ] 更多案例（PPP、轨道拟合、多系统融合）
- [ ] NTRIP 实时流数据源适配
- [ ] Docker 一键部署
- [ ] 模型可解释性分析（SHAP）
