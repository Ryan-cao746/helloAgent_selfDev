# helloAgent_selfDev
A application sourced from the code of HelloAgent, used for learning

- 截至2026.8.1
    - 需要重点关注simple_agent写的工具参数解析和tool_calls方面。文档给出的解决方案不够简洁
    - 目前想法是将tool_calls写成独立的类型，并将工具参数解析、tool_call解析等方法重新设计
    - 以后可能需要将每个模块内部通信的字段进行规范化处理
    - 我不理解，很多时候定义了相关类型，为什么文档编撰者不用，辟之如message
    - 大改了工具调用，以及参数系统。我把单个工具的参数描数用base里定义的参数类统一处理，似乎会好些
    - 重写了simple_agent里的message系统，全部换成本项目里定义好的message类型，以后似乎可以和history合并
    - 改了client的think，message换成Message类型列表硬转