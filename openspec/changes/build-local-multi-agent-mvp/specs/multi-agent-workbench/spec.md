## ADDED Requirements

### Requirement: 本地多智能体任务编排

系统 MUST 提供一个本地可运行的多智能体编排流程，至少包含 `Planner`、`Coder`、`Executor`、`Reporter` 四类代理，并以确定的状态顺序驱动一次分析任务完成。

#### Scenario: 成功完成一次分析任务

- GIVEN 用户在本地工作台提交了一条分析需求并选择了一个可用数据集
- WHEN 后端创建分析任务并启动编排
- THEN 系统 SHALL 依次记录 `Planner`、`Coder`、`Executor`、`Reporter` 的执行步骤
- AND 系统 SHALL 将任务状态更新为成功完成
- AND 系统 SHALL 返回最终报告和相关产物索引

### Requirement: 执行失败后的有限重试

系统 MUST 在执行阶段失败时，将错误摘要和先前代码回送给 `Coder`，并在预设上限内进行有限重试，而非无限循环。

#### Scenario: 第一次执行失败后重试成功

- GIVEN `Executor` 首次运行代码返回错误
- WHEN 系统将错误摘要与先前代码交给 `Coder`
- THEN 系统 SHALL 增加一次重试计数并重新生成修复后的代码
- AND 系统 SHALL 再次触发 `Executor`
- AND 若后续执行成功，系统 SHALL 继续进入 `Reporter` 阶段

#### Scenario: 超过最大重试次数

- GIVEN 执行阶段连续失败且已达到最大重试次数
- WHEN 系统完成最后一次失败记录
- THEN 系统 SHALL 将任务标记为失败
- AND 系统 SHALL 返回清晰错误摘要

### Requirement: 纯本地持久化与产物管理

系统 MUST 使用本地存储保存任务元数据、步骤记录与分析产物，不得依赖云数据库。

#### Scenario: 运行记录与图表落盘

- GIVEN 一次任务成功生成了文本输出和图表
- WHEN 后端归档本次运行结果
- THEN 系统 SHALL 将任务与步骤信息写入本地 SQLite
- AND 系统 SHALL 将图表和相关运行文件保存到本地文件系统
- AND 系统 SHALL 返回可供前端查询的产物索引

### Requirement: React 本地工作台

系统 MUST 提供基于 React 的本地工作台，使用户能够提交任务、查看运行过程并浏览结果。

#### Scenario: 用户在前端查看多代理执行轨迹

- GIVEN 用户已在浏览器打开本地工作台
- WHEN 用户提交分析任务
- THEN 前端 SHALL 展示任务当前状态和各代理步骤摘要
- AND 前端 SHALL 在任务完成后展示最终报告
- AND 若存在图表产物，前端 SHALL 提供可视化或下载入口

### Requirement: 无密钥可演示的 Mock 模式

系统 MUST 在未配置真实模型密钥时提供 `mock` 代理模式，以保证本地可测试性。

#### Scenario: 未配置 API Key 时运行任务

- GIVEN 本地环境未配置任何真实模型 API Key
- WHEN 用户以默认配置提交任务
- THEN 系统 SHALL 自动使用 `mock` 模式完成代理编排
- AND 系统 SHALL 在运行记录中标识当前模式
- AND 前端 SHALL 能看到完整的步骤轨迹与结果
