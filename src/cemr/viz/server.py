"""Servidor do dashboard: envia o registo de eventos ao browser por WebSocket.

Ao vivo, durante uma simulação:   python -m cemr.run --scenario c1 --factor 5 --viz 8080
Replay de um run acabado:         python -m cemr.viz.server runs/<run> [--port 8080]

A página (static/index.html) desenha as células, os hubs e o estado dos DAE, as pessoas a
deslocarem-se, os incidentes, as mensagens coloridas por sub-organização, as métricas e a lista de
casos. Em replay o browser recebe o registo todo de uma vez e reprodu-lo com os seus controlos.
"""

import argparse
import asyncio
import json
from pathlib import Path

from aiohttp import WSMsgType, web

from ..metrics.eventlog import read_events

STATIC = Path(__file__).parent / "static"
MAX_BATCH = 500


class VizServer:
    """Servidor HTTP e WebSocket do dashboard.

    Attributes:
        port (int): Porta local.
        mode (str): "live" ou "replay".
        title (str): Título mostrado na página.
        history (list[dict]): Eventos já recebidos, para quem se liga mais tarde.
    """

    def __init__(self, port: int, mode: str, history: list[dict] | None = None, title: str = ""):
        self.port = port
        self.mode = mode
        self.title = title
        self.history: list[dict] = list(history or [])
        self.clients: set[asyncio.Queue] = set()
        self.runner: web.AppRunner | None = None

    def publish(self, record: dict) -> None:
        """Subscritor do EventLog (ao vivo): guarda o evento e envia-o a todos os browsers ligados."""
        self.history.append(record)
        for queue in self.clients:
            queue.put_nowait(record)

    async def index(self, request: web.Request) -> web.Response:
        """Página do dashboard."""
        return web.FileResponse(STATIC / "index.html")

    async def websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Envia o histórico e depois, ao vivo, os eventos novos em lotes."""
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        queue: asyncio.Queue = asyncio.Queue()
        self.clients.add(queue)
        hello = {"type": "hello", "mode": self.mode, "title": self.title, "events": self.history}
        try:
            await ws.send_str(json.dumps(hello, separators=(",", ":")))
            if self.mode == "replay":
                async for msg in ws:                     # mantém a ligação até a página fechar
                    if msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        break
                return ws
            while not ws.closed:
                batch = [await queue.get()]
                while not queue.empty() and len(batch) < MAX_BATCH:
                    batch.append(queue.get_nowait())
                await ws.send_str(json.dumps({"type": "events", "events": batch}, separators=(",", ":")))
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            self.clients.discard(queue)
        return ws

    async def start(self) -> None:
        """Arranca o servidor em 127.0.0.1 (só acessível nesta máquina)."""
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/ws", self.websocket)
        app.router.add_static("/static/", STATIC)
        self.runner = web.AppRunner(app, access_log=None)
        await self.runner.setup()
        await web.TCPSite(self.runner, "127.0.0.1", self.port).start()
        print(f"dashboard: http://127.0.0.1:{self.port}/")

    async def stop(self) -> None:
        """Para o servidor."""
        if self.runner is not None:
            await self.runner.cleanup()


def main() -> None:
    """Replay de um run acabado."""
    parser = argparse.ArgumentParser(description="Replay a finished run in the dashboard.")
    parser.add_argument("run", type=Path, help="run directory with events.jsonl")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = VizServer(args.port, "replay", read_events(args.run / "events.jsonl"), args.run.name)

    async def serve():
        await server.start()
        await asyncio.Event().wait()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
