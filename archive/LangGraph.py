from typing import TypedDict
from langgraph.graph import StateGraph, END

# 1. 定义全局状态 (State)
# 这是所有 Agent 共享的“内存”，大家都在这个数据结构上进行读写
class AgentState(TypedDict):
    user_query: str        # 用户的初始自然语言需求
    dataset_schema: str    # 数据集的列名和类型 (供 Planner 参考)
    plan: str              # Planner 生成的步骤
    code: str              # Coder 生成的 Python 代码
    execution_result: str  # 沙盒执行的标准输出 (如 df.head() 或图表路径)
    error: str             # 沙盒执行的报错信息 (用于反馈给 Coder)
    iterations: int        # 记录 Debug 的次数，防止死循环
    final_report: str      # Reporter 生成的最终业务总结

# 2. 定义节点 (Nodes) - 每个节点对应一个 Agent 的具体动作
def planner_node(state: AgentState):
    print("🧠 Planner Agent 正在拆解任务...")
    # TODO: 调用 LLM，传入 user_query 和 dataset_schema，生成 plan
    mock_plan = "1. 读取数据 2. 处理缺失值 3. 绘制销量趋势图"
    return {"plan": mock_plan, "iterations": 0}

def coder_node(state: AgentState):
    print("💻 Coder Agent 正在编写/修改代码...")
    # TODO: 调用 LLM，传入 plan。如果有 error，则让 LLM 根据 error 修改代码
    mock_code = "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head())"
    return {"code": mock_code}

def executor_node(state: AgentState):
    print("⚙️ Executor Agent 正在沙盒中运行代码...")
    # TODO: 实际执行 state["code"] (可使用 E2B Sandbox 或 Python 内置 exec/subprocess)
    # 模拟执行结果：这里我们假设第一次执行失败，第二次成功
    current_iters = state.get("iterations", 0) + 1
    
    if current_iters < 2: # 模拟第一次报错
        return {"error": "KeyError: 'sales_amount' not found", "execution_result": "", "iterations": current_iters}
    else: # 模拟修改后执行成功
        return {"error": "", "execution_result": "Success. Image saved to output.png", "iterations": current_iters}

def reporter_node(state: AgentState):
    print("📝 Reporter Agent 正在撰写业务洞察报告...")
    # TODO: 调用 LLM，传入 execution_result，生成最终的文字分析
    return {"final_report": "根据图表分析，周末销量有显著提升..."}

# 3. 定义路由逻辑 (Conditional Edge) - 决定下一步去哪
def route_execution(state: AgentState):
    if state["error"] and state["iterations"] < 3:
        print("⚠️ 发现报错，打回给 Coder Agent 重新修改！")
        return "coder" # 代码出错且未达到最大重试次数，回到 coder
    elif state["error"] and state["iterations"] >= 3:
        print("❌ 达到最大重试次数，任务失败。")
        return END # 死循环保护
    else:
        print("✅ 执行成功，进入报告生成阶段。")
        return "reporter" # 执行成功，去写报告

# 4. 构建图 (Graph)
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("planner", planner_node)
workflow.add_node("coder", coder_node)
workflow.add_node("executor", executor_node)
workflow.add_node("reporter", reporter_node)

# 定义边 (数据流向)
workflow.set_entry_point("planner")
workflow.add_edge("planner", "coder")
workflow.add_edge("coder", "executor")

# 添加条件边 (根据执行结果决定分支)
workflow.add_conditional_edges(
    "executor",
    route_execution,
    {
        "coder": "coder",
        "reporter": "reporter",
        END: END
    }
)
workflow.add_edge("reporter", END)

# 编译图
app = workflow.compile()

# 5. 运行测试
if __name__ == "__main__":
    initial_state = {
        "user_query": "分析销售数据",
        "dataset_schema": "Date, Product, Sales",
        "error": "",
        "iterations": 0
    }
    print("🚀 启动 AutoDS 智能体工作流...\n")
    for output in app.stream(initial_state):
        # 实时打印状态流转
        pass