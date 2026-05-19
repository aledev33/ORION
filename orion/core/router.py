from orion.commands.base import CommandResult


class CommandRouter:
    def __init__(self, commands: list):
        self.commands = commands

    def dispatch(self, context, intent: str, payload: str, text: str, confidence: float) -> CommandResult:
        for command in self.commands:
            if command.can_handle(intent, payload, text):
                return command.execute(context, text, payload, confidence)

        return CommandResult(
            success=False,
            message="Todavía no sé ejecutar esa acción.",
            action="NO_HANDLER",
            payload=payload,
        )