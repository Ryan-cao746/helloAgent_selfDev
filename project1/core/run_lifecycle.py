"""定义单次 Agent 运行的状态、合法转换规则和协作式中止机制。"""

from datetime import datetime, timezone
from threading import Event
from time import perf_counter
from typing import Callable, Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, Field


RunStatus: TypeAlias = Literal[
    "finished",
    "failed",
    "cancelled",
    "timed_out",
]
RunPhase: TypeAlias = Literal[
    "building_context",
    "deciding",
    "retrying",
    "executing_tool",
    "waiting_confirmation",
]
RunState: TypeAlias = RunStatus | RunPhase  # 创建了一个名叫 RunState 的新类型，它等价于 RunStatus 或 RunPhase 中的任何一种情况。
RunErrorCode: TypeAlias = Literal[
    "context_build_failed",
    "llm_failed",
    "tool_registry_missing",
    "tool_call_budget_exceeded",
    "repeated_tool_call_limit",
    "tool_output_budget_exceeded",
    "maximum_steps_reached",
    "cancelled",
    "timed_out",
]


class RunTransition(BaseModel):
    """记录一次状态转换及其发生时间，可用于调试和运行轨迹展示。"""

    from_state: RunState | None = None
    to_state: RunState
    reason: str | None = None
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RunCancelled(RuntimeError):
    """表示运行在检查点响应了取消请求。"""


class RunTimedOut(RuntimeError):
    """表示运行在检查点超过了设定期限。"""


_TERMINAL_STATES = {"finished", "failed", "cancelled", "timed_out"} # 最终状态转换阶段
_ALLOWED_TRANSITIONS: dict[RunState | None, set[RunState]] = {
    None: {"building_context"},
    "building_context": {"deciding", "failed", "cancelled", "timed_out"},
    "deciding": {
        "retrying",
        "executing_tool",
        "finished",
        "failed",
        "cancelled",
        "timed_out",
    },
    "retrying": {"deciding", "failed", "cancelled", "timed_out"},
    "executing_tool": {
        "executing_tool",   # 同一决策内依次执行多个工具时的自环转换
        "deciding",
        "waiting_confirmation",
        "failed",
        "cancelled",
        "timed_out",
    },
    "waiting_confirmation": {
        "deciding",
        "executing_tool",
        "cancelled",
        "timed_out",
    },
}   # 状态转换策略


class RunController:
    """控制单次同步运行的状态转换、超时和协作式取消。"""

    def __init__(
            self,
            timeout_seconds: float | None = None,
            clock: Callable[[], float] = perf_counter,
    ):
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds 必须大于 0")

        self.run_id = str(uuid4())
        self.started_at = datetime.now(timezone.utc)
        self.started_monotonic = clock()
        self.deadline = (
            self.started_monotonic + timeout_seconds
            if timeout_seconds is not None
            else None
        )
        self.context_duration_ms = 0.0
        self.current_state: RunState | None = None
        self.transitions: list[RunTransition] = []  # 状态转换的记录队列
        self._cancel_event = Event()    # 用于线程间的简单信号通信。它通过一个内部标志（Flag）的True/False来控制线程的等待与唤醒。
        self._clock = clock

    def cancel(self) -> None:
        """发出取消信号；运行会在下一个检查点终止。"""
        self._cancel_event.set()    # 将标志设为True，唤醒所有等待的线程

    def checkpoint(self) -> None:
        """检查取消和超时条件，并在满足条件时抛出对应异常。"""
        if self._cancel_event.is_set():
            raise RunCancelled("run cancelled")
        if self.deadline is not None and self._clock() >= self.deadline:
            raise RunTimedOut("run timed out")

    def transition(self, to_state: RunState, reason: str | None = None) -> None:
        """执行并记录一次合法状态转换。"""
        if self.current_state in _TERMINAL_STATES:
            raise RuntimeError("终态不能继续转换")

        allowed = _ALLOWED_TRANSITIONS.get(self.current_state, set())
        if to_state not in allowed:
            raise ValueError(
                f"非法状态转换: {self.current_state!r} -> {to_state!r}"
            )   # 状态转换合法性校验

        self.transitions.append(RunTransition(
            from_state=self.current_state,
            to_state=to_state,
            reason=reason,
        ))
        self.current_state = to_state

    def elapsed_ms(self) -> float:
        """返回控制器创建至今的单调时钟耗时，单位为毫秒。"""
        return (self._clock() - self.started_monotonic) * 1000
