from dataclasses import dataclass
from typing import Any, Awaitable, Callable


ToolHandler = Callable[[dict[str, Any]], Awaitable["SuspectToolResult"]]
ToolFormatter = Callable[["SuspectToolResult"], str]


@dataclass
class SuspectToolResult:
    """Generic result from a suspect actor tool."""

    name: str
    content: str
    metadata: dict[str, Any] | None = None


@dataclass
class SuspectActorTool:
    """Tool available to the suspect actor agent."""

    name: str
    description: str
    handler: ToolHandler
    format_context: ToolFormatter | None = None

    async def arun(self, args: dict[str, Any]) -> SuspectToolResult:
        return await self.handler(args)


class SuspectActorToolSet:
    """Registry for tools available to the suspect actor."""

    def __init__(self, tools: list[SuspectActorTool] | None = None):
        self._tools = {tool.name: tool for tool in tools or []}

    def get(self, name: str | None) -> SuspectActorTool | None:
        if not name:
            return None
        return self._tools.get(name)

    def describe(self) -> str:
        if not self._tools:
            return ""
        lines = ["[AVAILABLE TOOLS]"]
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)

    def format_result(self, result: SuspectToolResult) -> str:
        tool = self.get(result.name)
        if tool and tool.format_context:
            return tool.format_context(result)
        return f"[TOOL RESULT: {result.name}]\n{result.content}"
