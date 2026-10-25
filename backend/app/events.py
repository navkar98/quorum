"""In-process async pub/sub for Server-Sent Events.

Supports two kinds of subscribers:
  - Broadcast subscribers (e.g. the security dashboard) receive every event.
  - Targeted subscribers (e.g. a student) attach an `audience` predicate so the
    publisher only forwards events relevant to them (used for zone-targeted pushes).

Audience matching lets us push feedback/alert events to students near a targeted zone
WITHOUT exposing any identities: the predicate runs server-side per subscriber and the
payload itself never contains device ids.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# An audience predicate decides whether a given (event_type, data) should go to this
# subscriber. None means "receive everything" (broadcast).
Audience = Optional[Callable[[str, dict], bool]]


@dataclass
class Subscriber:
    queue: asyncio.Queue
    audience: Audience = None
    meta: dict = field(default_factory=dict)


_subscribers: set[Subscriber] = set()


def subscribe(audience: Audience = None, meta: Optional[dict] = None) -> Subscriber:
    sub = Subscriber(queue=asyncio.Queue(maxsize=100), audience=audience,
                     meta=meta or {})
    _subscribers.add(sub)
    return sub


def unsubscribe(sub: Subscriber) -> None:
    _subscribers.discard(sub)


def publish(event_type: str, data: dict[str, Any]) -> None:
    """Publish an event. Safe to call from sync or async code.

    Each subscriber receives it only if its audience predicate accepts it (or if it is a
    broadcast subscriber). Payloads must contain only aggregate/non-identifying data.
    """
    payload = json.dumps({"type": event_type, "data": data})
    for sub in list(_subscribers):
        try:
            if sub.audience is not None and not sub.audience(event_type, data):
                continue
        except Exception:
            # A faulty predicate must never crash publishing; just skip delivery.
            continue
        try:
            sub.queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass


async def event_stream(sub: Subscriber):
    """Yield SSE-formatted messages for one subscriber."""
    try:
        # Initial hello so the client knows the stream is live.
        yield "event: hello\ndata: {}\n\n"
        while True:
            try:
                payload = await asyncio.wait_for(sub.queue.get(), timeout=15)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    finally:
        unsubscribe(sub)
