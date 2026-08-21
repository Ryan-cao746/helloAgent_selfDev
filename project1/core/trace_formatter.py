"""将结构化运行结果转换为不泄露敏感数据的文本轨迹。"""

from project1.core.agent_protocol import AgentRunResult, FinishDecision, ToolDecision
from project1.tools.security import redact_sensitive_text


def format_run_trace(result: AgentRunResult) -> str:
    """格式化单次运行摘要，不输出提示词和原始工具内容。"""
    lines = [
        f"Run: {result.run_id}",
        f"状态: {result.status}",
        f"总耗时: {result.duration_ms:.2f} ms",
        f"上下文构建: {result.context_duration_ms:.2f} ms",
        f"步骤数: {result.step_count}",
    ]

    if result.transitions:
        state_path = " -> ".join(
            transition.to_state for transition in result.transitions
        )
        lines.append(f"状态流: {state_path}")

    for step in result.steps:
        lines.append(f"步骤 {step.step_number}: LLM {step.llm_duration_ms:.2f} ms")
        if isinstance(step.decision, ToolDecision):
            for tool_result in step.tool_results:
                lines.append(
                    f"  工具: {tool_result.tool_name} / {tool_result.status} / "
                    f"{tool_result.duration_ms:.2f} ms"
                )
                if tool_result.error:
                    lines.append(
                        f"  工具错误: {redact_sensitive_text(tool_result.error)}"
                    )
        elif isinstance(step.decision, FinishDecision):
            lines.append("  决策: 返回最终答案")
        elif step.error:
            lines.append(f"  LLM错误: {step.error}")

    if result.error:
        lines.append(f"运行错误: {redact_sensitive_text(result.error)}")
    if result.error_code:
        lines.append(f"错误代码: {result.error_code}")
    return "\n".join(lines)
