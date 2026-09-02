from dataclasses import dataclass, field
from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentState:
    id: str
    name: str
    depends_on: list[str]
    status: AgentStatus = AgentStatus.IDLE
    progress: int = 0
    logs: list[str] = field(default_factory=list)
    output: str | None = None

    def to_event_dict(self) -> dict:
        return {
            "agent": self.id,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
        }
