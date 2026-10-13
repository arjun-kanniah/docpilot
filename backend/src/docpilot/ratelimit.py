import hmac
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

    def check(self, visitor: str, cost: int = 1) -> str | None:
        """Record `cost` questions and return None, or return why they aren't allowed."""
        now = self._clock()
        with self._lock:
            if int(now // DAY) != self._day:
                self._day, self._today = int(now // DAY), 0
            if self._today + cost > self._per_day:
                return "The public demo has reached its question limit for today. Try tomorrow."

            recent = self._visitors.setdefault(visitor, deque())
            while recent and recent[0] <= now - HOUR:
                recent.popleft()
            if len(recent) + cost > self._per_hour:
                return (
                    f"The public demo allows {self._per_hour} questions an hour. "
                    "Try again later, or run DocPilot locally."
                )
            recent.extend([now] * cost)
            self._today += cost
            if len(self._visitors) > 10_000:  # drop visitors with no recent questions
                self._visitors = {k: v for k, v in self._visitors.items() if v[-1] > now - HOUR}
            return None


PROXY_SECRET_HEADER = "x-docpilot-proxy-secret"
CLIENT_IP_HEADER = "x-docpilot-client-ip"


def visitor_id(request: Request, proxy_secret: str = "") -> str:
    """The client's IP.

    Requests through the Cloudflare Worker reach Cloud Run from Cloudflare's addresses, so the
    Worker passes the visitor's IP in a header, trusted only with the shared secret. Otherwise
    Google's front end appends the client's IP to X-Forwarded-For, so take the last entry;
    anything before it was sent by the client and can't be trusted.
    """
    sent_secret = request.headers.get(PROXY_SECRET_HEADER, "")
    client_ip = request.headers.get(CLIENT_IP_HEADER)
    if proxy_secret and client_ip and hmac.compare_digest(sent_secret, proxy_secret):
        return client_ip
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


@lru_cache
def get_rate_limiter() -> RateLimiter:
    settings = get_settings()
    return RateLimiter(settings.demo_questions_per_hour, settings.demo_questions_per_day)
