# Implementation Tasks: Removal of Mock Mode

## 1. 核心配置文件与后端清理
- **任务目标**：修改 `backend/app/config.py`，向默认的大模型选择列表中加入当下最新的多规格 OpenAI 型号 `gpt-4o-mini`, `gpt-4o`, `gpto1-mini`, `o3-mini`, `gpt-4-turbo`；并从 `backend/app/main.py` 注销对 `simulate_failure` 与 `mode` 两参数的处理及报错。
- **影响范围**：`config.py`，`main.py`
- **实施要点**：
  1. 重写 `_RAW_MODEL_OPTIONS` 的默认空坠处理（当没有设置 `OPENAI_MODEL_OPTIONS` 环境变量时提供上面说好的固定五款模型选择）。
  2. 收紧 `create_run` 路由的方法体：拿掉所有包含 `mode` 为 `'mock'` 或者异常判定拦截（如上传 CSV 就报错说得切 real）的逻辑。默认全部皆以 Real LLM 执行。
- **验收标准**：调用 `/api/debug/llm-config` 会在 `models` 返回包含完整的备选项；`/api/runs` 在直接丢传任意文件时均能畅通进行任务。
- **验证方法**：启动服务后检查 http://127.0.0.1:8000/api/debug/llm-config 返回的 JSON 是否符合。

## 2. Agent 内部强制转为真实推理流
- **任务目标**：卸载 `orchestrator.py` 与 `agents.py` 内部为 Demo 提供的 Mock 硬写入逻辑（即之前因 `mode` 检测触发的空执行），将接口与参数缩减为纯 Real 状态运作模式。
- **影响范围**：`backend/app/agents.py`, `backend/app/orchestrator.py`
- **实施要点**：
  1. `agents.py` 内部所有函数形参中摘取掉 `mode` （从传参定义里删去）；并在内部删去 `if mode == 'real':` 的条件判断、将之前的 fallback 伪数据完全剥除。
  2. `orchestrator.py` 中撤销传递 `run["mode"]` 的实参变量，撤销为了肉眼可控的卡顿故意预留的 `_maybe_sleep` 人工假延迟。
- **验收标准**：通过接口或界面发起的跑流，均直接调用 `OpenAICompatibleClient` 后下发实时流，而不涉及 `mode` 的判定。
- **验证方法**：测试任意流程时不再抛出关于 “mode 实参过多” 的 Type Error 即可证实清扫干净。

## 3. 前端 UI 的清算与视图更新
- **任务目标**：彻底抹除一切 `mode` 为 `'mock'` 的状态栏/勾选框/下拉菜单。并在 README 中展示最新成品图。
- **影响范围**：`frontend/src/App.jsx`, `README.md`
- **实施要点**：
  1. 删去状态 `mode`, `setMode` 和引出的 `simulateFailure` 状态钩子。
  2. 重构页面 HTML 表单布局，如上文截图批注要求一样销毁 `Agent Mode` 组件以及被标记成黄色的“只有 Real Mode 才能上传覆盖”警告 `DIV`。并将 `Real Mode Model` 直接提升位置对齐到上方，更名为 `Model Selection`。
  3. 修改提交给后端的 `FormData` 组包，剔除不要再被后端接受的这些键。
  4. 利用 markdown 图片语法插入对 UI 展示截图的引入到根目录 `README.md` 中。
- **验收标准**：前台无白屏、渲染清爽且模型下拉菜单选项变多。
- **验证方法**：查看本地 5173 页面，表单仅有 `Question`, `Model Selection`, `Local Dataset` 和 `Upload Custom CSV`，干净顺畅。
- **回滚方式**：Git Revert 当前变动或者重塑先前的 JSX 状态组件代码回去。
