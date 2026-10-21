"""SF-WEB-1 exact loopback authority and bearer ASGI boundary."""
from __future__ import annotations

import asyncio
import hmac

from starlette.responses import JSONResponse


class WebApiAuth:
    """Raw ASGI headers preserve duplicates; never trust forwarded headers."""

    def __init__(self, app, *, feed, config):
        self.app, self.feed, self.config = app, feed, config
        self.active = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        gate = None
        values = {}
        for name, label in ((b"host", "HOST"), (b"origin", "ORIGIN"),
                            (b"authorization", "TOKEN")):
            items = [v for k, v in scope["headers"] if k.lower() == name]
            if len(items) > 1:
                gate = label + "_DUPLICATE"
                break
            values[name] = items[0] if items else None
        if gate is None:
            host = f"127.0.0.1:{self.config.port}".encode("ascii")
            if values[b"host"] != host:
                gate = "HOST"
            elif values[b"origin"] not in (None, b"http://" + host):
                gate = "ORIGIN"
            elif not hmac.compare_digest(values[b"authorization"] or b"",
                                          b"Bearer " + self.feed._token_bytes):
                gate = "TOKEN"
        headers = {"Cache-Control": "no-store"}
        if gate is not None:
            status = 401 if gate == "TOKEN" else 403
            if status == 401:
                headers["WWW-Authenticate"] = "Bearer"
            await JSONResponse({"error": "MONITOR_FORBIDDEN", "gate": gate},
                               status_code=status, headers=headers)(scope, receive, send)
            return
        if self.active >= self.config.max_connections:
            await JSONResponse({"error": "MONITOR_CAPACITY_EXCEEDED"},
                               status_code=503, headers=headers)(scope, receive, send)
            return
        if scope["method"] != "GET":
            await JSONResponse({"error": "MONITOR_READ_ONLY"}, status_code=405,
                               headers=headers)(scope, receive, send)
            return
        started = False

        async def bounded_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await asyncio.wait_for(send(message), self.config.send_seconds)

        self.active += 1
        try:
            streaming = scope["path"] in ("/api/v1/stream", "/api/v1/events")
            await asyncio.wait_for(self.app(scope, receive, bounded_send),
                self.config.request_seconds + (self.config.stream_seconds if streaming else 0))
        except TimeoutError:
            if not started:
                await JSONResponse({"error": "MONITOR_PROJECTION_UNAVAILABLE"},
                                   status_code=503, headers=headers)(scope, receive, send)
            # After headers, cancellation closes the response, never a second status.
        finally:
            self.active -= 1
