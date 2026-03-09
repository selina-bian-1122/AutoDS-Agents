# Change Tasks: 修复 Executor 在真实与模拟模式下由于数据库连接未关闭导致的卡死假死问题

### 任务 1：重构 `backend/app/db.py` 确保连接生命周期的安全释放
- **任务目标**：修改所有数据库访问的公共接口（`fetch_one`, `fetch_all`, `execute`, `execute_many`），使得底层产生的 `sqlite3.Connection` 在每次调用结束后被正确且毫无遗漏地 `close()`。
- **影响范围**：`backend/app/db.py`。
- **实施要点**：
  1. 引入标准库 `from contextlib import closing`。
  2. 在 `fetch_all` 中包裹 `get_connection()`:
     ```python
     with closing(get_connection()) as connection:
         rows = connection.execute(query, params).fetchall()
     return [dict(row) for row in rows]
     ```
  3. 分别针对 `fetch_one`，`execute` 和 `execute_many` 做等效的 `closing` 包装。
- **验收标准**：
  - 前端以 1.5 秒频率连续轮询后，后端的 sqlite 连接不再产生幽灵泄漏。
  - Mock 或 Real Mode 调度至 Executor 生成子脚本时，能够成功分配文件描述符资源进行 Python 代码执行并毫无阻塞地写入 `stdout.txt` 和 `result.json`。
  - UI 上的状态能顺理成章地抵达 `COMPLETED`。
- **验证方法**：
  - 代码变更后，重新启动 `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`。
  - 在前台 UI 发起一个新的 Multi-Agent Task（包括 Mock 或者上传自定义 CSV 进入 Real 模式）。
  - 全程监视 Run Overview 面板直至它成功结束显示 Reporter 的字样以及 Final Report 内容被渲染。
- **回滚方式**：
  - 移出 `closing` wrapper 并退回仅依赖 `with get_connection() as connection:` 的原生语法糖。
