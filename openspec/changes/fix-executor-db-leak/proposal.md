# Change Proposal: 修复 Executor 在真实与模拟模式下由于数据库连接未关闭导致的卡死假死问题

## 1. 背景与动机（为什么做）
当前用户在界面上运行多次 Multi-Agent 分析任务时，发现任务执行到 Executor 阶段总是无限卡在 `RUNNING` 状态，并且后台控制台没有任何显式的崩溃或 traceback 报错输出。
经过排查诊断，这是由于 `backend/app/db.py` 中管理 SQLite 数据库连接存在的**资源泄漏 (Resource Leak)**：
目前的操作封装如 `fetch_one`, `fetch_all`, `execute` 虽然使用了 `with get_connection() as connection:`（Context Manager），但在 Python `sqlite3` 的标准实现中，此语法糖仅仅自动处理事务的 commit 和 rollback，**并不会自动关闭连接 (Connection Close)**。
结合前端每 1.5 秒轮询一次 `/api/runs/{run_id}` 来持续获得最新状态，后端每次查询都在隐式地产生新的幽灵连接，随着时间推移极易突破操作系统对单进程允许的最大打开文件描述符（FD limit）。当这个枯竭临界点爆发时，后台试图再拉起 `subprocess` 跑 Python executor 或打开文件时就会直接由于 `[Errno 24] Too many open files` 在深层抛出异常，而异常流也被外部吞没，导致线程静默死亡，形成了永久卡死。

## 2. 目标与范围（做什么）
- 修改 `backend/app/db.py` 中的关键数据库操作函数（`fetch_one`, `fetch_all`, `execute`, `execute_many`），确保查询或写入后底层连接被**确切、正确地关闭**。
- 保证前后端通讯无论经历多久的轮询请求都能极低内存和句柄占用稳定运行。
- 由于是基础通用函数的修正，这不仅能解决当前 mock 模式下观察到的 executor 卡顿，更会修复之后运行 real mode 时的关联风险。

## 3. 非目标（明确这次不做什么）
- 暂不引入其他的 ORM（如 SQLAlchemy、SQLModel）或者是异步（aiosqlite）。针对本项目的极简化目标，我们维持原生 sqlite3 + connection 方案即可。
- 不对前台的轮询机制频率（从 1.5 秒）做更改（只要连接不泄漏即可支撑此量级的访问）。

## 4. 与现有系统的关系
- 唯一影响的模块：`backend/app/db.py` 内部基础操作的封装方式。由于这是数据访问底座，改动会使所有经过它读取、写入状态的上游业务即刻受益。

## 5. 主要方案
使用标准库的 `contextlib.closing` 包裹 `sqlite3.connect`，或者显式定义 `try...finally: connection.close()`，确保无论是正常结束还是抛出异常脱离函数，底层的数据库连接一定会被释放销毁。
例如：
```python
from contextlib import closing

def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with closing(get_connection()) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]
```

## 6. 风险清单与缓解措施
- **风险**：可能存在的 Cursor 死锁或因为游标依赖连接导致返回了未消费的数据。
- **缓解措施**：`fetchall()` 会将全部行即时加载到内存列表中处理，因此 `return [dict(row) for row in rows]` 时不需要与数据库保持绑定，此时再关闭连接是完全安全的。

---
## 澄清问题清单 (Clarification Checklist)

本次修复属于阻断级（Blocked），不修复此问题完全无法跑通任何进一步的 real / mock 分析任务流。
**[阻断级问题]**
- 暂时没有。方案极度清晰。

**[非阻断级问题]**
- **默认决策**：我们将选用 `contextlib.closing` 的最优雅方式，使代码的变更行数最小且最为安全，且不用添加额外的 `try...finally` boilerplate。
