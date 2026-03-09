# Proposal: Complete Removal of Mock Mode & Enforcing Real LLM Inference

## 背景与动机
用户在实际使用中发现 `mock` 模式并不稳定，缺乏顺畅的体验体验，并且常常产生不平滑的错觉。为了保证终端呈现的质量，并精简心智模型，用户要求直接剔除整个 Mock Mode 功能，仅保留 Real LLM Inference 模式。同时，提供更多的 OpenAI 官方大模型选项，优化前端排版使其更清晰。

## 目标与范围
- **前端界面的清理与重排**：删去 `Agent Mode` 的下拉选择框；删去由于选择 `mock` 模式产生的那段关于“要求必须处于 Real Mode 才能上传文件”的黄色警告提示；将原有的 `Real Mode Model` 提升至最上方并更名为纯粹的 `Model Selection`。
- **丰富的默认大模型支持**：若环境变量未填，后端默认向前端推送的可用列表里至少包含 `gpt-4o-mini`, `gpt-4o`, `o1-mini`, `o3-mini`, `gpt-4-turbo`。
- **后端参数的移除**：完全移除在 API 层和 Agent 内部因区分 `mock` 和 `real` 而留存的分支代码（如不再检查 `if mode == 'real':`，不再抛硬编码好的答案），默认所有流程皆为对接前置设定好的真实 LLM API。
- **全局生效**：本提交涵盖前后端所有与模式判断相关的硬逻辑，确保完全转向真实的协同运作。

## 非目标
- 不变更现存 Executor 沙盒的安全防范机制（如 timeout、防止死锁等）。
- 不更换底层大模型服务供应商环境架构（依旧兼容 OpenAI 协议）。

## 目标系统的影响范围
- `openspec/project.md`：项目中不再提及 Mock 方案。
- `frontend/src/App.jsx`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/agents.py`
- `backend/app/orchestrator.py`

## 主要方案
1. 后端：`config.py` 中的 `_RAW_MODEL_OPTIONS` 的 fallback 备选列表替换为多规格模型。
2. 后端：`orchestrator.py` 不再检测 `run["mode"]` 字段执行模拟延迟 `_maybe_sleep`，且向 `agents` 下发时不再附带 `mode` 参数。
3. 后端：在 `agents.py` 中彻底删除原先作为 fallback 用的 mock mock-data 拼接逻辑。
4. 前端：从 `App.jsx` 中的 `useState` 删掉 `mode`，清理表单中的 `<select>` 与警告框，整理布局。

## 澄清问题记录（Decisions）
无阻断级问题。
- **默认决策 + 理由**：对于旧的不完整的 mock 数据流直接硬删除，因为不再会被任何调用路由到了。对于默认下拉模型选择了最新的一批 OpenAI 代表。

## 风险清单与缓解措施
- **风险**：旧任务历史记录中存在 `mode: "mock"`，后端重构后可能会导致界面上回显遇到未能对齐的文字。
- **缓解措施**：在历史记录的回显中，直接渲染即可，不做抛错阻止；对于后续写入的记录 `mode` 全定为 `"real"`。
