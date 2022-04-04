from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from nuclear.sublog import log

from looper.runner.looper import Looper


def setup_web_views(app: FastAPI, looper: Looper):
    templates = Jinja2Templates(directory="templates")

    @app.get("/")
    async def home():
        return RedirectResponse("/looper")

    @app.get("/looper", response_class=HTMLResponse)
    async def view_looper(request: Request):
        return templates.TemplateResponse("looper.html", {
            "request": request,
            "track_ids": list(range(looper.config.tracks_num)),
        })

    @app.get("/recordings", response_class=HTMLResponse)
    async def view_recordings(request: Request):
        return templates.TemplateResponse("recordings.html", {
            "request": request,
            "recordings": looper.saver.list_recordings(),
        })
