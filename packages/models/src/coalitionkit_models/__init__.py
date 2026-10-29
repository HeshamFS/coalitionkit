# SPDX-License-Identifier: Apache-2.0
"""The model provider gateway, media client, settings, price table and cost meter."""

from .errors import (
    BudgetExhaustedError,
    MediaInputError,
    MissingKeyError,
    ProviderError,
    SchemaValidationError,
    SettingsError,
    TruncatedReply,
    UnpricedModelError,
)
from .gateway import (
    ChatMessage,
    Completer,
    Completion,
    FakeModel,
    ModelGateway,
    OpenAITransport,
    ScriptedResponse,
    Transport,
    Usage,
    connection_error,
    status_error,
)
from .media import MediaClient, Transcript, Turn
from .meter import SYSTEM_PARTICIPANT, BudgetEvent, CostMeter, CostRecord
from .prices import ModelPrice, PriceTable, load_price_table
from .sam import Box, Mask, SamParseError, Segment, parse_sam_output
from .settings import ROLES, Role, Route, Settings, load_settings
from .structured import ToolCall
from .wav import WavInfo, validate_wav

__all__ = [
    "ROLES",
    "SYSTEM_PARTICIPANT",
    "Box",
    "BudgetEvent",
    "BudgetExhaustedError",
    "ChatMessage",
    "Completer",
    "Completion",
    "CostMeter",
    "CostRecord",
    "FakeModel",
    "Mask",
    "MediaClient",
    "MediaInputError",
    "MissingKeyError",
    "ModelGateway",
    "ModelPrice",
    "OpenAITransport",
    "PriceTable",
    "ProviderError",
    "Role",
    "Route",
    "SamParseError",
    "SchemaValidationError",
    "ScriptedResponse",
    "Segment",
    "Settings",
    "SettingsError",
    "ToolCall",
    "Transcript",
    "Transport",
    "TruncatedReply",
    "Turn",
    "UnpricedModelError",
    "Usage",
    "WavInfo",
    "connection_error",
    "load_price_table",
    "load_settings",
    "parse_sam_output",
    "status_error",
    "validate_wav",
]
