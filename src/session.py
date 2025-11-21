"""
Session manager for flash messages and event log.

What it holds:
- state: position, inventory, stats (loaded from persistence).
- _event_log: list of EventEntry (timestamp, action, result, position).
- _flash_buffer: one-shot messages shown once then cleared.

Key behaviors:
- add_flash/consume_flash: queue and drain transient notifications.
- record_event: append MOVE outcomes with timestamp and position.
- history: returns serializable view of events.
- recent_statuses/is_stubborn: detects 3 consecutive BLOCKED/OOB to trigger sarcasm in responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class EventEntry:
    timestamp: str
    action: str
    result: str
    position: Dict[str, int]


class SessionManager:
    """In-memory session state."""

    def __init__(self, username: str, initial_state: Dict[str, Any]):
        self.username = username
        self.state: Dict[str, Any] = {
            "position": initial_state.get("position", {"x": 0, "y": 0}),
            "inventory": initial_state.get("inventory", []),
            "stats": initial_state.get("stats", {"total_steps": 0}),
        }
        self._event_log: List[EventEntry] = []
        self._flash_buffer: List[str] = []

    def add_flash(self, msg: str) -> None:
        self._flash_buffer.append(msg)

    def consume_flash(self) -> List[str]:
        flashes = list(self._flash_buffer)
        self._flash_buffer.clear()
        return flashes

    def record_event(self, action: str, result: str, position: Dict[str, int]) -> None:
        entry = EventEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            result=result,
            position=position,
        )
        self._event_log.append(entry)

    def history(self) -> List[Dict[str, Any]]:
        return [
            {"timestamp": e.timestamp, "action": e.action, "result": e.result, "position": e.position}
            for e in self._event_log
        ]

    def recent_statuses(self, n: int = 3) -> List[str]:
        return [e.result for e in self._event_log[-n:]]

    def is_stubborn(self) -> bool:
        last = self.recent_statuses()
        return len(last) == 3 and all(status in {"BLOCKED", "OOB"} for status in last)
