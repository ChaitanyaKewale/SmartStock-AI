"""Structured event logging system for SmartStock AI.

Provides monotonic, chronological event tracking for all decisions, movements,
and state changes, powering the live AI decision log.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from simulation.models import Position, SimulationEvent


class EventManager:
    """Manages ordered, monotonic simulation events."""

    def __init__(self):
        self._events: List[SimulationEvent] = []
        self._next_event_id: int = 1

    @property
    def events(self) -> List[SimulationEvent]:
        """Return shallow copy of all logged events in chronological order."""
        return list(self._events)

    def log(
        self,
        category: str,
        action: str,
        outcome: str,
        explanation: str,
        order_id: Optional[str] = None,
        position: Optional[Position] = None,
        timestamp: Optional[str] = None
    ) -> SimulationEvent:
        """Create, append, and return a new structured SimulationEvent with a monotonic ID."""
        ts = timestamp or datetime.now().strftime("%H:%M:%S")
        event = SimulationEvent(
            event_id=self._next_event_id,
            timestamp=ts,
            category=category.upper(),
            order_id=order_id,
            position=position,
            action=action,
            outcome=outcome.upper(),
            explanation=explanation
        )
        self._events.append(event)
        self._next_event_id += 1
        return event

    def get_recent(self, limit: int = 20, category: Optional[str] = None) -> List[SimulationEvent]:
        """Return the most recent events, optionally filtered by category, newest first."""
        matched = self._events
        if category and category != "ALL":
            matched = [e for e in matched if e.category == category.upper()]
        return list(reversed(matched[-limit:]))

    def clear(self) -> None:
        """Reset event stream (used in testing or explicit simulation reset)."""
        self._events.clear()
        self._next_event_id = 1
