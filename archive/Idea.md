# AutoDS: Multi-Agent Interactive Data Analysis System

## Project Overview

AutoDS is an automated exploratory data analysis (EDA) tool built on top of a multi-agent collaboration model. Users describe their analysis goals in natural language—for example, "Analyze the sales dataset and identify unusual weekend demand spikes"—and the underlying agents collaborate to break down the task, write code, run it in a sandbox, debug failures, and produce final insights.

The system uses a state-graph architecture so that code generation can be self-healing, making it suitable for end-to-end analysis of messy real-world datasets.

## Components

The system is divided into four core modules:

- **Interaction Interface**: A chat-style UI that supports CSV/Excel uploads, multi-turn conversation, and live rendering of generated charts and dataset previews.
- **Orchestration Engine**: Maintains global state and routes work between agents.
- **LLM Backend**: Provides reasoning and code generation capability through a code-friendly model.
- **Secure Execution Sandbox**: Runs agent-generated Python code in an isolated environment and returns stdout, stderr, and generated artifacts such as PNG charts.

## Agent Roles

The system is composed of four cooperating agents, each with a dedicated role and system prompt:

### Planner Agent

- **Role**: Receives the user request and dataset schema, then decomposes the goal into 3–4 concrete analysis steps.
- **Output**: A Markdown step-by-step execution plan.

### Coder Agent

- **Role**: Writes high-quality Python code based on the Planner output, primarily using pandas, matplotlib, and seaborn.
- **Characteristic**: Can revise code based on runtime tracebacks and schema mismatches.

### Executor Agent

- **Role**: A tool-calling agent responsible for running the generated Python code inside the sandbox.
- **Output**: Text output, chart file references, or error traces.

### Reporter Agent

- **Role**: Summarizes successful outputs and charts into a business-friendly analytical report.

## Orchestration and Collaboration Logic

The system uses a cyclic directed graph. The core workflow is:

1. The user uploads data and provides an instruction.
2. The Planner Agent creates an analysis plan.
3. The Coder Agent writes code.
4. The Executor Agent runs the code.
5. Conditional routing:
   - If execution fails, send the traceback and prior code back to the Coder Agent for debugging, with a retry limit such as 3 attempts.
   - If execution succeeds, pass the result to the Reporter Agent.
6. The Reporter Agent returns the final insight summary, and the UI renders charts and text output.

A state-transition diagram can be added with Mermaid or Excalidraw to visualize the flow:

`Planner -> Coder <-> Executor -> Reporter`

## Tools and APIs

- **LLM API**: Gemini 1.5 Pro / OpenAI GPT-4o or another strong code-capable model.
- **Orchestration Framework**: LangGraph or AutoGen.
- **Execution Sandbox**: E2B Code Interpreter SDK or an isolated Docker container.
- **Frontend/UI**: Streamlit was the original concept recommendation because it can render DataFrames and charts quickly.

## Core Design Decisions

### Why separate responsibilities across multiple agents?

Compared with asking one model to plan, code, and summarize in a single step, role separation reduces hallucinations and keeps each stage focused. Planner protects analytical rigor, Coder focuses on executable syntax, and Reporter focuses on communication quality.

### Why include a closed-loop debugging cycle?

Real-world data analysis code rarely works on the first attempt. Schema mismatches, missing values, and dtype issues are common. The feedback loop between Executor and Coder demonstrates fault tolerance and robustness.

### Data privacy and safety

The system follows the principle of “send code to the data, not the data to the model.” The model only sees dataset schema and execution logs, not the raw full dataset.
