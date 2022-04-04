import time
import threading

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nuclear.sublog import log
from looper.runner.api import setup_looper_endpoints

from looper.runner.looper import Looper


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


def start_api(looper: Looper) -> Server:
    fastapi_app = creat_fastapi_app(looper)
    config = uvicorn.Config(app=fastapi_app, host="0.0.0.0", port=8000, log_level="debug")
    server = Server(config=config)
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

    @app.get("/")
    async def home():
        return {"status": "ok"}

    setup_looper_endpoints(app, looper)

    return app
