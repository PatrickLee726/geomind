# 贡献指南 · Contributing to GeoMind

GeoMind 是开源可分叉的 AI 平差计算引擎。你可以在三种层面参与贡献。

## 一、Fork 与二次开发（最轻量）

1. Fork 本仓库到你自己的 GitHub 账号
2. 修改 `backend/app/pipelines/` 中的任一 Pipeline 参数（网络结构、学习率等），适配你的数据场景
3. 或者你有一套完全不同的平差场景（比如 GNSS PPP、卫星轨道拟合），直接新建一个 Pipeline 文件

**Fork 的典型场景：**
- 你所在的实验室有自有观测数据，想替换数据源
- 你想尝试不同的 ML 模型架构（LSTM、Transformer、Random Forest）
- 你想把引擎集成到自己的 Web 应用中

## 二、添加新 Pipeline（贡献上游）

如果你写的 Pipeline 具有通用价值，欢迎 PR 回来：

1. 在 `backend/app/pipelines/` 下新建 `.py` 文件
2. 继承 `app.core.base.Pipeline`，实现 `case_id`、`case_name`、`config_schema()`、`run()` 四个方法
3. 在 `backend/app/pipelines/__init__.py` 中注册
4. 提交 PR，描述你的新案例以及预期精度提升

**Pipeline 开发规范：**
- 训练/测试划分方式必须在 `run()` 文档中显式声明（按站、按 DOY 等）
- 经典方法与 ML 方法必须使用同一套划分，对比结果才有效
- 数据源优先使用 `DataSource` 抽象接口，保持可扩展性

## 三、贡献数据源适配器

如果你有新的 GNSS 数据来源（如 NTRIP 实时流、北斗 CORS 站、特定卫星的广播星历），可以在 `backend/app/datasources/` 下新建适配器，实现 `DataSource` 接口即可。

## 代码风格

- Python: PEP 8
- 前端: Vue 3 Composition API + ESLint

## 行为准则

本仓库遵守 [Contributor Covenant](https://www.contributor-covenant.org/)。参与即表示你同意遵守其条款。

## 提问与讨论

- Bug 报告和功能建议：提交 GitHub Issue
- 技术讨论：欢迎在 Issue 中使用「Discussion」标签
