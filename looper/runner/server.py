from pathlib import Path
import time
import threading

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from nuclear.sublog import log, log_exception

from looper.runner.api import setup_looper_endpoints
from looper.runner.looper import Looper
from looper.runner.views import setup_web_views


class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        while not self.started:
            time.sleep(1e-3)
        log.debug("HTTP server started")
    
    def stop(self):
        self.should_exit = True
        self.thread.join()
        log.debug("HTTP server stopped")

    def wait(self):
        self.thread.join()


def start_api_in_background(looper: Looper) -> Server:
    fastapi_app = creat_fastapi_app(looper)
    port = looper.config.http_port
    config = uvicorn.Config(app=fastapi_app, host="0.0.0.0", port=port, log_level="debug")
    server = Server(config=config)
    log.info(f'Starting HTTP server', addr=f'http://0.0.0.0:{port}')
    server.start()
    return server


def creat_fastapi_app(looper: Looper) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/status")
    async def status():
        return {"status": "ok"}

    Path('out').mkdir(exist_ok=True)
    app.mount("/out", StaticFiles(directory="out"), name="static_out")
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.exception_handler(Exception)
    async def error_handler(request: Request, exc: Exception):
        log_exception(exc)
        return JSONResponse(
            status_code=500,
            content={'error': str(exc)},
        )

    async def catch_exceptions_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            log_exception(exc)
            return JSONResponse(
                status_code=500,
                content={'error': str(exc)},
            )

    app.middleware('http')(catch_exceptions_middleware)

    setup_web_views(app, looper)
    setup_looper_endpoints(app, looper)

    return app
