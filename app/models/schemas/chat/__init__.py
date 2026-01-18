"""Chat schema modules organized by purpose."""
from .common import (
    ChatMessageSchema,
    SuspectChatHistorySchema,
    ClueChatHistorySchema
)
from .request import (
    SuspectChatRequest,
    ClueChatRequest
)
from .response import (
    SuspectChatResponse,
    ClueChatResponse
)

__all__ = [
    # Common
    "ChatMessageSchema",
    "SuspectChatHistorySchema",
    "ClueChatHistorySchema",
    # Request
    "SuspectChatRequest",
    "ClueChatRequest",
    # Response
    "SuspectChatResponse",
    "ClueChatResponse",
]
