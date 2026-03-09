# 项目基础设定与边界约定

由于系统之前缺失 `openspec/project.md` 级目标，我在此作为本次变更的一部分为您起草补充，作为今后协作的事实标准：

## 1. 项目目标与边界
**Local Multi-Agent Workbench** 致力于构建一个运行于本地的轻量级多 Agent 测试床。
主要架构为前端 (React + Vite) 和后端 (FastAPI + Python + SQLite)。
包含四个固定的 Agent 环节协作机制：Planner -> Coder -> Executor -> Reporter。

## 2. 技术栈与主要依赖版本
- **后端**：Python (>=3.8)、FastAPI、Uvicorn。
- **持久化**：原生 `sqlite3` 本地文件数据库。
- **前端**：React、Vite 构建，使用纯 CSS 样式（玻璃态设计风格、Inter 字体）。

## 3. 架构分层与模块边界
- `app/main.py`: 路由控制层，对接前端的 API 请求。
- `app/orchestrator.py`: 多代理核心流转模块，负责状态打点调度，与具体 Agent 能力层解耦。
- `app/agents.py`: 大模型调用和各类具体 Agent prompt 构建器。
- `app/db.py`: 数据持久层，封装对 SQLite 全局库的读写操作（需具备可靠安全的资源管理约束）。

## 4. 编码风格与持续集成规范
- PEP-8 兼容书写，适当的地方可使用 `ruff` 或 `flake8` 辅助标准检查。
- 类型提示（Type Hint）视为必须。前段与后端的通讯必须保证 JSON 格式不被非预期中断。

## 5. 部署环境约束
- 后端需在受限的本地环境也能无缝工作，必须具备强壮异常捕捉（Graceful Degradation），例如：系统文件句柄、内存、端口耗尽时不应当造成静默线程死亡，即使发生必须体现在日志输出或状态流转中。
