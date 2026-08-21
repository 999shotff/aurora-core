"""WebSocket abstraction for real-time market data streaming.

Provides a protocol-level abstraction for WebSocket connections.
No live trading. No broker connections. Data streaming only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class WSMessage:
    """A WebSocket message."""
    channel: str
    data: dict[str, Any]
    timestamp: str = ""


@dataclass(frozen=True)
class WSSubscription:
    """A channel subscription request."""
    channel: str
    symbols: list[str]
    timeframe: str = "1d"


class WebSocketHandler(Protocol):
    """Protocol for WebSocket message handlers."""

    def on_message(self, message: WSMessage) -> None:
        """Handle incoming WebSocket message."""
        ...

    def on_connect(self) -> None:
        """Handle connection established."""
        ...

    def on_disconnect(self) -> None:
        """Handle disconnection."""
        ...


@dataclass
class MockWebSocket:
    """Mock WebSocket for testing and development.

    Simulates a WebSocket connection for chart data streaming.
    No real connection. No live data.
    """
    connected: bool = False
    subscriptions: list[WSSubscription] = field(default_factory=list)
    messages: list[WSMessage] = field(default_factory=list)

    def connect(self) -> None:
        """Simulate connection."""
        self.connected = True

    def disconnect(self) -> None:
        """Simulate disconnection."""
        self.connected = False
        self.subscriptions.clear()

    def subscribe(self, subscription: WSSubscription) -> None:
        """Subscribe to a channel."""
        if self.connected:
            self.subscriptions.append(subscription)

    def unsubscribe(self, channel: str, symbols: list[str]) -> None:
        """Unsubscribe from a channel."""
        self.subscriptions = [
            s for s in self.subscriptions
            if not (s.channel == channel and s.symbols == symbols)
        ]

    def simulate_message(self, channel: str, data: dict[str, Any]) -> None:
        """Simulate an incoming message for testing."""
        msg = WSMessage(channel=channel, data=data)
        self.messages.append(msg)
