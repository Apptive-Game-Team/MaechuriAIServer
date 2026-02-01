"""Chat schema modules organized by purpose."""
from .common import (
    ChatMessageSchema,
    SuspectChatHistorySchema,
    ClueChatHistorySchema
)
from .request import (
    SuspectChatRequest,
    ClueChatRequest,
    GeneralChatRequest
)
from .response import (
    SuspectChatResponse,
    ClueChatResponse,
    GeneralChatResponse
)

__all__ = [
    # Common
    "ChatMessageSchema",
    "SuspectChatHistorySchema",
    "ClueChatHistorySchema",
    # Request
    "SuspectChatRequest",
    "ClueChatRequest",
    "GeneralChatRequest",
    # Response
    "SuspectChatResponse",
    "ClueChatResponse",
    "GeneralChatResponse",
]
