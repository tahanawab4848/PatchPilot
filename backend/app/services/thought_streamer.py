"""
ThoughtBroadcaster: Real-time thinking stream broadcaster for Nebius / Nemotron inference.
Allows SSE endpoints and clients to consume token-by-token reasoning streams with zero latency.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional


class ThoughtBroadcaster:
    def __init__(self) -> None:
        # job_id -> list of subscriber queues
        self._subscribers: Dict[str, List[asyncio.Queue[str]]] = {}
        # job_id -> accumulated string
        self._history: Dict[str, str] = {}
        # lock for thread-safe subscriber management
        self._lock = asyncio.Lock()

    async def publish(self, job_id: str, chunk: str) -> None:
        """Publish a thought chunk to all active subscribers for the job."""
        if not chunk:
            return

        # Append to in-memory history
        if job_id not in self._history:
            self._history[job_id] = chunk
        else:
            self._history[job_id] += chunk

        # Broadcast to active queues
        subscribers = self._subscribers.get(job_id, [])
        for queue in subscribers:
            try:
                queue.put_nowait(chunk)
            except asyncio.QueueFull:
                pass

    async def subscribe(self, job_id: str) -> asyncio.Queue[str]:
        """Subscribe to live thought chunks for a specific job."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            if job_id not in self._subscribers:
                self._subscribers[job_id] = []
            self._subscribers[job_id].append(queue)
        return queue

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue[str]) -> None:
        """Remove a subscriber queue."""
        async with self._lock:
            if job_id in self._subscribers:
                try:
                    self._subscribers[job_id].remove(queue)
                except ValueError:
                    pass
                if not self._subscribers[job_id]:
                    del self._subscribers[job_id]

    def get_history(self, job_id: str) -> str:
        """Return accumulated reasoning stream so far for job_id."""
        return self._history.get(job_id, "")

    def clear(self, job_id: str) -> None:
        """Clear memory for finished job."""
        self._history.pop(job_id, None)


# Global singleton
thought_broadcaster = ThoughtBroadcaster()
