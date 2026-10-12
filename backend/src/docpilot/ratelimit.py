import threading
import time
from collections import deque
from collections.abc import Callable
from functools import lru_cache

from starlette.requests import Request

from docpilot.config import get_settings

HOUR = 3600
DAY = 86400


class RateLimiter:
    """Question limits for the public demo: per visitor per hour, and per instance per day.

    Kept in memory, so with a couple of Cloud Run instances the limits are approximate. The
    hard backstop is the spend limit set on each provider's API key.
    """

    def __init__(self, per_hour: int, per_day: int, clock: Callable[[], float] = time.time) -> None:
        self._per_hour = per_hour
        self._per_day = per_day
        self._clock = clock
        self._lock = threading.Lock()
        self._visitors: dict[str, deque[float]] = {}
        self._day = -1
        self._today = 0

    def check(self, visitor: str) -> str | None:
        """Record a question and return None, or return why it isn't allowed."""
        now = self._clock()
        with self._lock:
            if int(now // DAY) != self._day:
                self._day, self._today = int(now // DAY), 0
            if self._today >= self._per_day:
                return "The public demo has reached its question limit for today. Try tomorrow."

            recent = self._visitors.setdefault(visitor, deque())
            while recent and recent[0] <= now - HOUR:
                recent.popleft()
            if len(recent) >= self._per_hour:
                return (
                    f"The public demo allows {self._per_hour} questions an hour. "
                    "Try again later, or run DocPilot locally."
                )
            recent.append(now)
            self._today += 1
            if len(self._visitors) > 10_000:  # drop visitors with no recent questions
                self._visitors = {k: v for k, v in self._visitors.items() if v[-1] > now - HOUR}
            return None


def visitor_id(request: Request) -> str:
    """The client's IP. Google's front end appends it to X-Forwarded-For, so take the last
    entry; anything before it was sent by the client and can't be trusted."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


@lru_cache
def get_rate_limiter() -> RateLimiter:
    settings = get_settings()
    return RateLimiter(settings.demo_questions_per_hour, settings.demo_questions_per_day)
