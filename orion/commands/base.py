from dataclasses import dataclass
from typing import Optional


@dataclass
class CommandResult:
    success: bool
    message: str
    action: str
    payload: Optional[str] = None


class BaseCommand:
    intent_name = None

    def can_handle(self, intent: str, payload: str, text: str) -> bool:
        return intent == self.intent_name

    def execute(self, context, text: str, payload: str, confidence: float) -> CommandResult:
        raise NotImplementedError("Cada comando debe implementar execute().")