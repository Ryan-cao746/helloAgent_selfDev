# helloAgent_selfDev
A application sourced from the code of HelloAgent, used for learning

#### 截至2026.8.1
- 需要重点关注simple_agent写的工具参数解析和tool_calls方面。文档给出的解决方案不够简洁
- 目前想法是将tool_calls写成独立的类型，并将工具参数解析、tool_call解析等方法重新设计
- 以后可能需要将每个模块内部通信的字段进行规范化处理
- 我不理解，很多时候定义了相关类型，为什么文档编撰者不用，辟之如message
- 大改了工具调用，以及参数系统。我把单个工具的参数描数用base里定义的参数类统一处理，似乎会好些
- 重写了simple_agent里的message系统，全部换成本项目里定义好的message类型，以后似乎可以和history合并
- 改了client的think，message换成Message类型列表硬转
- Agent这个抽象基类默认不包含tool_registry。所以说次级方法在继承时需要在超类的init方法外面加上这个字段
- 完成了ReAct。将工具参数提取和工具调用方法统一移到了register中。修改了文档提供的对ReAct的长短期记忆系统

---

#### 截至2026.8.4
- 部分完成了记忆系统，自己借助AI写了TF-IDF向量化检索
---

#### 2026.8.5
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
---

#### 2026.8.6
- 首先，记忆系统只有在多轮对话的环境下才有用
- 所以说，记忆系统和上下文构建系统实际上是一个可选项。于是我在complex_agents基类里并未实际上要求这两个系统是必填的
- 因此首要任务是实现一个多轮对话的Agent。工作记忆存在于单轮对话内，而其他记忆类型则是持久化的，活跃于整个程序的生命周期
- 完成多轮对话multi_asking_agent配套的记忆和上下文模块advanced_context_manager和simple_episodic_memory
- 计划将逻辑高度重复的响应处理模块分离出来
- 部分完成了multi_asking_agent

---
#### 2026.8.7
- 正在做记忆摘要系统
- 记忆系统要大改，必须将存储结构改成以id为主键的字典
- 其他改动太多，不想写了

---
#### 2026.8.8
- 完成了总结Agent
- 完成了多轮对话Agent的全部内容，包含一个配置了工作记忆和情景记忆的记忆系统。主要loop文件在project1/complex_agents/types/multi_asking_agent/multi_asking_agent内
- 这个Agent配备两个子Agent，一个负责用户交互，另一个负责整理记忆
- 注意，现在记忆系统的manager默认通过init的配置选择是否启用工作记忆和情景记忆，且工作记忆和情景记忆的字典键值默认为 working 和 episodic，这个默认的规则已经嵌入了工程的各个系统和环节，不易修改
- 以后打算做语义记忆，并且增强工具配置

---
#### 2026.8.9
- 借AI大改，具体如下
- 今天的改动围绕“统一协议、可靠记忆、依赖解耦”三条主线展开。当前工作区相对 `HEAD` 约有 35 个受跟踪文件变化，新增 533 行、删除 645 行，尚未提交。

**1. Agent 架构重组**

- 删除旧的 `agents/agent_types` 和 `complex_agents` 双重目录结构。
- Agent 实现统一迁移到 `project1/agents/types`。
- 删除旧 `SimpleAgent`、旧 `ReactAgent` 和原 `MultiAskingAgent`。
- 多轮流程重命名并拆分为 [MultiTurnConversation]。
- 测试脚本同步迁移到 `project1/agents/test`。

**2. 引入组合根与工厂**

- 新增 [agent_factory.py]。
- LLM、记忆、Context、ReAct Agent 和 Summary Agent 的创建移出多轮流程类。
- `MultiTurnConversation` 只负责用户输入、轮次控制、调用子 Agent 和触发摘要。
- [main.py] 成为真实启动入口，负责输入接口和工具注册。
- `Config` 新增 `max_steps` 和 `max_ask`，由工厂消费。

**3. LLM 错误契约**

- 新增 `LLMClientError`。
- `HelloAgentsLLM.think()` 成功始终返回字符串，失败抛出明确异常并保留原始异常链。
- 不再把错误伪装成普通模型回答。
- API Key 输出已关闭。

**4. 工具调用协议统一**

- 新增结构化 `ToolCall`。
- 工具参数统一使用 JSON 对象，保留旧 `key=value` 格式兼容。
- 修复多参数解析错误和工具调用标记残留 `]`。
- `register_function()` 通过 `FunctionTool` 接入同一注册与执行路径。
- 增加必填参数、未知参数校验。
- `SimpleAgent`、两套 ReAct 调用点和响应处理器均迁移到新接口。
- 修正工具描述中把参数文本误用为工具描述的问题。

**5. 可配置记忆名称**

- [MemoryManager]统一保存工作记忆和情景记忆名称。
- Context Manager 不再硬编码 `"working"`/`"episodic"`。
- `ReactAgentV2`、`SummaryAgent` 和多轮流程都从同一个 `MemoryManager` 获取名称。
- 支持类似 `session/profile` 的自定义名称。
- 删除存在字典/列表实现冲突的旧 `WorkingMemory`。

**6. 摘要记忆事务化**

- 完善 [MemoryOperation 和 MemoryOperationBatch]。
- 增加条件字段、重复目标、重复新增和批次数量校验。
- 兼容旧 `summary` 字段，内部统一为 `content`。
- [MemoryManager.apply_operation_batch()]在深拷贝上执行整批操作，全部成功后才提交。
- `SummaryAgent` 不再逐条直接修改记忆。
- 记忆 ID 改用 UUID，解决快速连续写入时的覆盖问题。
- 摘要提示词的字段名称及 `<ANSWER>` 输出协议已统一。

**7. 测试补充**

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