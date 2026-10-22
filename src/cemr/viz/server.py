"""Dashboard server: streams the event log to the browser over a WebSocket.

Live, during a simulation:   python -m cemr.run --scenario c1 --factor 5 --viz 8080
Replay of a finished run:    python -m cemr.viz.server runs/<run> [--port 8080]

The page (static/index.html) draws the cells, hubs and AED states, people moving, incidents, message
arcs coloured by sub-organisation, live metric tiles and the case list. In replay mode the browser gets
the whole log at once and plays it back with its own controls.
"""

import argparse
import asyncio
import json
from pathlib import Path

from aiohttp import WSMsgType, web

STATIC = Path(__file__).parent / "static"


class VizServer:
    def __init__(self, port: int, mode: str, history: list[dict] | None = None, title: str = ""):
        self.port = port
        self.mode = mode
        self.title = title
        self.history: list[dict] = list(history or [])
        self.clients: set[asyncio.Queue] = set()
        self.runner: web.AppRunner | None = None

    def publish(self, record: dict) -> None:
        """EventLog subscriber (live mode): keep the record for late joiners and push it to every client."""
        self.history.append(record)
        for queue in self.clients:
            queue.put_nowait(record)

    async def index(self, request: web.Request) -> web.Response:
        return web.FileResponse(STATIC / "index.html")

    async def websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        queue: asyncio.Queue = asyncio.Queue()
        self.clients.add(queue)
        try:
            await ws.send_str(json.dumps({"type": "hello", "mode": self.mode, "title": self.title,
                                          "events": self.history}, separators=(",", ":")))
            if self.mode == "replay":
                async for msg in ws:                     # keep the socket open until the page closes
                    if msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        break
                return ws
            while not ws.closed:
                batch = [await queue.get()]
                while not queue.empty() and len(batch) < 500:
                    batch.append(queue.get_nowait())
                await ws.send_str(json.dumps({"type": "events", "events": batch}, separators=(",", ":")))
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            self.clients.discard(queue)
        return ws

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/ws", self.websocket)
        app.router.add_static("/static/", STATIC)
        self.runner = web.AppRunner(app, access_log=None)
        await self.runner.setup()
        await web.TCPSite(self.runner, "127.0.0.1", self.port).start()
        print(f"dashboard: http://127.0.0.1:{self.port}/")

    async def stop(self) -> None:
        if self.runner is not None:
            await self.runner.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a finished run in the dashboard.")
    parser.add_argument("run", type=Path, help="run directory with events.jsonl")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    events = [json.loads(line) for line in (args.run / "events.jsonl").open() if line.strip()]
    server = VizServer(args.port, "replay", events, args.run.name)

    async def serve():
        await server.start()
        await asyncio.Event().wait()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
