# helloAgent_selfDev
An application sourced from the code of HelloAgent, used for learning.

## 开发日志

以下记录按时间降序排列，最新改动优先展示，并保留各阶段当时的设计与实现状态。

### 至2026-08-31
- 完成了mcp客户端的搭建，同时也有一个示例的mcp服务器
- 完成了mcp适配。参考了HelloAgents的方法，为mcp客户端创建后台进程和事件循环，从而适配整个项目同步的框架
- 新建了mcp_wrapper_tool。这个tool导入mcp对工具的描述，使单个工具适配于Agent的原生同步工具，而执行是异步执行的
- 新建了mcp同步桥，维护一个配备独立事件循环的后台线程，通过主线程向其中插入协程函数来异步执行mcp的工具
- 其线程调度如下：
```
主线程 start()
  -> _ready.clear()
  -> 启动后台线程
  -> _ready.wait()  阻塞等待

后台线程
  -> 创建 asyncio loop
  -> 执行 _start_client_async()
       -> 成功：self._client = MCPClient(...)
       -> 失败：self._startup_error = error
       -> finally: _ready.set()

主线程被唤醒
  -> 如果 _startup_error 不为空，抛 RuntimeError
  -> 否则说明 MCP client 已经连接好
```
- 计划后续建立基于mcp的skills系统
### 2026-08-21
- 目前完善了配置系统，写了file_config配置类，用于设置文件读写的工作目录。
- 文件读写的目录设置的是以其作为根目录读/写。
- 这个config的使用模式是先由file_config加载配置，然后创建文件工具时直接通过初始化注入到工具类型中
- config里workspace_root可以写为绝对或相对目录
- 已经可以完成简单的工作任务

### 2026-08-18
- 新增了程序记忆模块。如需编辑则在skills中添加文档。
- 新增了文件读写、目录浏览操作工具。
- 目前文件读写存在异常，需要进一步调试

### 至2026-08-17
- 进一步优化。新增了一个状态机，控制Agent运行状态的管理和转换
- 实现了工具的权限控制。如果相关
- 增加了工具权限确认机制和检查点机制，增加了线程调度，完善了Agent运行中的相关状态模式
- 目前仅仅将"read_only"和"network"设置为工具注册表初始允许的权限策略
- 完善了各个模块的注释和文档
- 对项目做了清理，删除了一些自项目反复修改以来重复的、多余的方法
- 注意，当需要添加高危工具时，如编辑文件工具，定义时需要声明权限并显示要求确认，同时注册表要添加放行策略（目前不支持）。

### 至2026-08-14
- 完成了豆包搜索工具。
- 对原搜索函数做出如下更改：
新增 SearchFilter 模型，正确支持 NeedContent、NeedUrl、Sites、BlockHosts、AuthInfoLevel。
新增 QueryControl 模型，支持 QueryRewrite。
补齐 SearchRequestParams 中的 QueryControl、ContentFormats、Industry。
支持 snake_case 参数自动转换为豆包 API 所需的 PascalCase 字段。
增加参数约束，例如结果数 1~50、时间范围格式、行业和正文格式枚举。
修正 Filter 原先错误的 Dict[str, bool] 类型，否则 sites 等字符串字段无法通过校验。
修正 RuyiInfo 类型，由字符串改为对象。
允许错误响应中的 Result 为 None。
为 FinalSearchResult 增加 error 字段，保留具体失败原因。
请求增加默认 30 秒超时和 HTTP 状态检查。
识别 API 返回的业务错误，而不再把错误响应当成成功结果。
删除包含硬编码 API Key 的调试入口，避免密钥继续保存在源码中。

### 至2026-08-13
- 修正了部分错误。修正了memory_types\base的死代码。优化了异常控制和异常保护，完善了异常降级机制，单轮失败不终止对话。修复了其他一些潜在的bug
- 做好了网页搜索的api，初步测试正常。目前调用豆包搜索的API联网搜索信息。相关信息需要在config里定义字段。

### 至2026-08-11
- 添加了语义记忆的功能。改根目录下的memory_lib中的文档即可。
- 目前md文档按段落拆分，所以可以把小标题和段落内容合在一段里写
- 计划添加更多工具，包括浏览器操作。
- 再次大改
本轮将原本依赖 `Thought/Action` 文本正则解析的 ReAct 循环，改造成了结构化决策循环。

**主要改动**

- 新增 [agent_protocol.py]
  - `ToolDecision`：请求调用工具
  - `FinishDecision`：返回最终答案
  - `AgentStepRecord`：记录每一步决策和工具结果
  - `AgentRunResult`：记录运行状态、输出、错误和完整步骤
  - `AgentDecision` 使用普通联合类型，消除了 PyCharm 对 `kind` 的误报

- 改造 [llm_client.py]
  - 新增 `decide()` 方法
  - 使用 Pydantic 校验模型返回的 JSON
  - 首次格式错误时反馈校验信息并允许模型修复一次
  - 再次失败时抛出明确的 `LLMClientError`

- 重写 [react_agent_v2.py]
  - 新增 `run_structured()` 结构化执行入口
  - 支持“模型决策 → 工具执行 → 结果回传 → 下一次决策”
  - `run()` 仍返回字符串，保持现有多轮会话兼容
  - 可通过 `last_run_result` 查看完整运行轨迹
  - 区分 `finished` 和 `failed`
  - 达到最大步骤、缺少注册表、模型协议错误均会产生结构化失败结果
  - 用户输入和最终回答只在结束时写入一次，修复工具循环中的重复记忆
  - 工具执行结果只保留在本次步骤轨迹中，不再污染长期记忆

- 更新 [react_prompt_template.py]
  - 模型只能返回 `tool` 或 `finish` JSON
  - 禁止 Markdown 和额外文本
  - 不再要求输出完整 `Thought`

- 更新 [react_context_manager.py]
  - 补充空的 `semantic_str`，避免基础 Context 使用新模板时缺少占位参数

- 加强 [base.py]
  - `ToolCall` 禁止未知字段，工具请求协议更严格

- 新增 [test_structured_react_agent.py]
  - 覆盖直接完成
  - 工具调用后完成
  - 达到最大步骤
  - 未知协议字段
  - 非法 JSON 自动修复

**验证情况**

`AgentDecision` 的 `tool` 和 `finish` JSON 分流已通过实际 Pydantic 解析验证。现有测试中有 15 项通过；完整新测试尚未跑通，因为 Codex 自带 Python 缺少 `openai`，而调用项目 Python 的权限请求被中止。

工作区里的 `.env`、`.idea`、`__pycache__` 等原有未跟踪文件没有被本轮修改。

#### 学到了什么：
这轮修改最核心的学习点是：**LLM 应该是“不可靠的决策建议者”，而程序才是“可靠的流程控制者”。**

你原来的结构是：

```text
模型生成任意文本
→ 正则表达式猜测 Thought 和 Action
→ 从字符串中继续猜工具名称和参数
→ 执行工具
```

现在变成：

```text
模型生成决策 JSON
→ Pydantic 校验
→ 程序识别 ToolDecision 或 FinishDecision
→ 执行工具或结束
```

**1. 从字符串约定升级为数据协议**

原来：

```python
thought, action = phrase_output(response)

if action.startswith("Finish"):
    ...
```

这里的 `Action` 只是字符串，拼写、标点或括号变化都可能导致程序失效。

现在：

```python
decision = self.llm_client.decide(messages)

if isinstance(decision, ToolDecision):
    ...
elif isinstance(decision, FinishDecision):
    ...
```

这就是“协议思维”：模块之间传递有明确字段、类型和约束的数据，而不是依赖双方默契理解一段文本。

**2. LLM 输出应当视为外部不可信输入**

模型即使很强，也可能返回：

- 不合法 JSON
- 不存在的工具
- 缺少参数
- 多余字段
- 空答案

因此它和 HTTP 请求、用户输入一样，都必须先校验：

```python
parse_agent_decision(response)
```

只有通过校验的数据才能进入工具执行层。

**3. Prompt 不能代替程序校验**

原来的提示词虽然要求模型遵守 `Thought/Action` 格式，但“要求”不等于“保证”。

现在形成了两层约束：

```text
Prompt：告诉模型应该怎样输出
Pydantic：决定程序实际接受什么
```

Prompt 用于提高成功率，Schema 才是真正的安全边界。

**4. Agent 循环本质上是状态转换**

原来的 `while` 循环虽然也在运行，但状态是隐含在字符串和 `if` 中的。

现在每一步都有明确含义：

```text
ToolDecision
→ 执行工具
→ 记录 ToolResult
→ 将观察结果交给模型
→ FinishDecision
```

`AgentStepRecord` 使过程成为可检查的数据，而不是执行完就消失的临时变量。

严格来说，目前还是“结构化状态循环”，还不是完整状态机。以后可以继续增加：

```text
running / retrying / cancelled / timed_out
```

**5. 执行轨迹和记忆是不同的数据**

原来的工具结果直接进入工作记忆，而且每次工具调用都重复保存用户输入。这混淆了两件事：

- 这次任务是怎么执行的
- 用户有哪些值得记住的信息

现在：

- 工具调用和结果进入 `AgentStepRecord`
- 用户输入和最终回答在结束时写入一次
- 长期记忆不再保存大量执行噪声

这是 Agent 系统中很重要的边界：

```text
运行轨迹用于调试和审计
对话记录用于保持上下文
长期记忆用于跨会话召回
```

**6. 错误也应该是结构化结果**

原来达到最大步数时，只返回一句普通文本：

```python
"已达到最大迭代次数，无法完成任务。"
```

调用者无法判断这是正常回答还是失败提示。

现在可以检查：

```python
result.status
result.error
result.step_count
result.steps
```

展示给用户的是 `output`，程序判断运行情况则使用 `status` 和 `error`。

**7. 可以在不破坏旧接口的情况下演进架构**

新增了：

```python
run_structured() -> AgentRunResult
```

但保留：

```python
run() -> str
```

所以现有 `MultiTurnConversation` 不需要同步大改。这体现了兼容层的价值：内部逐步升级，对外接口暂时稳定。

**8. 依赖注入让 Agent 更容易测试**

因为 LLM、Context、Memory 和 ToolRegistry 都由外部传入，测试可以使用 Fake LLM：

```python
FakeDecisionLLM([
    ToolDecision(...),
    FinishDecision(...),
])
```

不用调用真实模型，就能稳定验证工具循环、最大步数和记忆写入。这比测试模型“会不会恰好输出指定格式”可靠得多。

目前的新结构仍有提升空间：工具失败还是字符串、运行轨迹尚未持久化、没有取消和超时、工具观察暂时用普通消息传递。但它已经建立了正确的主干。

一句话概括这轮架构变化：**模型负责提出下一步，程序负责验证、执行和决定状态如何转换。**

### 2026-08-09
- 借AI大改，具体如下
- 今天的改动围绕“统一协议、可靠记忆、依赖解耦”三条主线展开。当前工作区相对 `HEAD` 约有 35 个受跟踪文件变化，新增 533 行、删除 645 行，尚未提交。

#### 1. Agent 架构重组

- 删除旧的 `agents/agent_types` 和 `complex_agents` 双重目录结构。
- Agent 实现统一迁移到 `project1/agents/types`。
- 删除旧 `SimpleAgent`、旧 `ReactAgent` 和原 `MultiAskingAgent`。
- 多轮流程重命名并拆分为 `MultiTurnConversation`。
- 测试脚本同步迁移到 `project1/agents/test`。

#### 2. 引入组合根与工厂

- 新增 `agent_factory.py`。
- LLM、记忆、Context、ReAct Agent 和 Summary Agent 的创建移出多轮流程类。
- `MultiTurnConversation` 只负责用户输入、轮次控制、调用子 Agent 和触发摘要。
- `main.py` 成为真实启动入口，负责输入接口和工具注册。
- `Config` 新增 `max_steps` 和 `max_ask`，由工厂消费。

#### 3. LLM 错误契约

- 新增 `LLMClientError`。
- `HelloAgentsLLM.think()` 成功始终返回字符串，失败抛出明确异常并保留原始异常链。
- 不再把错误伪装成普通模型回答。
- API Key 输出已关闭。

#### 4. 工具调用协议统一

- 新增结构化 `ToolCall`。
- 工具参数统一使用 JSON 对象，保留旧 `key=value` 格式兼容。
- 修复多参数解析错误和工具调用标记残留 `]`。
- `register_function()` 通过 `FunctionTool` 接入同一注册与执行路径。
- 增加必填参数、未知参数校验。
- `SimpleAgent`、两套 ReAct 调用点和响应处理器均迁移到新接口。
- 修正工具描述中把参数文本误用为工具描述的问题。

#### 5. 可配置记忆名称

- `MemoryManager` 统一保存工作记忆和情景记忆名称。
- Context Manager 不再硬编码 `"working"`/`"episodic"`。
- `ReactAgentV2`、`SummaryAgent` 和多轮流程都从同一个 `MemoryManager` 获取名称。
- 支持类似 `session/profile` 的自定义名称。
- 删除存在字典/列表实现冲突的旧 `WorkingMemory`。

#### 6. 摘要记忆事务化

- 完善 `MemoryOperation` 和 `MemoryOperationBatch`。
- 增加条件字段、重复目标、重复新增和批次数量校验。
- 兼容旧 `summary` 字段，内部统一为 `content`。
- `MemoryManager.apply_operation_batch()` 在深拷贝上执行整批操作，全部成功后才提交。
- `SummaryAgent` 不再逐条直接修改记忆。
- 记忆 ID 改用 UUID，解决快速连续写入时的覆盖问题。
- 摘要提示词的字段名称及 `<ANSWER>` 输出协议已统一。

#### 7. 测试补充

新增三组聚焦测试：

- 工具注册、JSON/兼容参数和函数工具执行。
- 自定义记忆名称及 Context 构建。
- 记忆批次校验、原子失败、合法提交和 UUID 唯一性。

当前验证结果：

- 15 项聚焦测试全部通过。
- 55 个 Python 文件通过 AST 语法检查。
- Fake LLM 的 ReAct 和摘要事务完整流程已验证。
- 未运行需要真实 API 或交互输入的旧脚本测试。
- `git diff --check` 当前仅报告存在行尾空格。
- `.env`、`.idea` 和多个 `__pycache__` 仍处于未跟踪状态，仓库目前仍缺少 `.gitignore`。

### 2026-08-08
- 完成了总结Agent
- 完成了多轮对话Agent的全部内容，包含一个配置了工作记忆和情景记忆的记忆系统。主要loop文件在project1/complex_agents/types/multi_asking_agent/multi_asking_agent内
- 这个Agent配备两个子Agent，一个负责用户交互，另一个负责整理记忆
- 注意，现在记忆系统的manager默认通过init的配置选择是否启用工作记忆和情景记忆，且工作记忆和情景记忆的字典键值默认为 working 和 episodic，这个默认的规则已经嵌入了工程的各个系统和环节，不易修改
- 以后打算做语义记忆，并且增强工具配置

### 2026-08-07
- 正在做记忆摘要系统
- 记忆系统要大改，必须将存储结构改成以id为主键的字典
- 其他改动太多，不想写了

### 2026-08-06
- 首先，记忆系统只有在多轮对话的环境下才有用
- 所以说，记忆系统和上下文构建系统实际上是一个可选项。于是我在complex_agents基类里并未实际上要求这两个系统是必填的
- 因此首要任务是实现一个多轮对话的Agent。工作记忆存在于单轮对话内，而其他记忆类型则是持久化的，活跃于整个程序的生命周期
- 完成多轮对话multi_asking_agent配套的记忆和上下文模块advanced_context_manager和simple_episodic_memory
- 计划将逻辑高度重复的响应处理模块分离出来
- 部分完成了multi_asking_agent

### 2026-08-05
- 完成了工作记忆，大改了TF-IDF检索的返回逻辑，同时完成了关键词检索。
- 工作记忆评分没有写时间衰减因子
- 经过分析，觉得需要重写架构
    - 首先，负责上下文工程的模块必须解耦，因为这些过于复杂且复用性较高
    - 记忆系统必须解构。这个之前就这么写的
    - 也在考虑是否要解耦后处理模块。
- 写了上下文接口的基本实现，在context包里
- 写了memory的manager，用于实现基本记忆操作
- 加了complex_agents，这是装配了规范的上下文处理接口和记忆管理模块的agent，与之前写的不一样，适用于复杂的上下文处理情况
- 为了论证新架构的可行性，写了:
    - simple_context_manager，直接堆记忆的提示词构建器
    - simple_memory，直接添加、没有任何特殊逻辑的记忆系统
    - simple_complex_agent，相当于之前写的react_agent，只不过用了新的架构
- 所以说后处理模块因为依赖过于灵活，不同的agent有不同的实现方式，所以不解耦
- 计划基于这些基础设施完成后续的上下文构建和记忆处理系统

### 截至z2026-08-04
- 部分完成了记忆系统，自己借助AI写了TF-IDF向量化检索

### 截至2026-08-01
- 需要重点关注simple_agent写的工具参数解析和tool_calls方面。文档给出的解决方案不够简洁
- 目前想法是将tool_calls写成独立的类型，并将工具参数解析、tool_call解析等方法重新设计
- 以后可能需要将每个模块内部通信的字段进行规范化处理
- 我不理解，很多时候定义了相关类型，为什么文档编撰者不用，辟之如message
- 大改了工具调用，以及参数系统。我把单个工具的参数描数用base里定义的参数类统一处理，似乎会好些
- 重写了simple_agent里的message系统，全部换成本项目里定义好的message类型，以后似乎可以和history合并
- 改了client的think，message换成Message类型列表硬转
- Agent这个抽象基类默认不包含tool_registry。所以说次级方法在继承时需要在超类的init方法外面加上这个字段
- 完成了ReAct。将工具参数提取和工具调用方法统一移到了register中。修改了文档提供的对ReAct的长短期记忆系统
