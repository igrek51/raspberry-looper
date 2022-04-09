from typing import Dict
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from looper.runner.looper import Looper


def setup_web_views(app: FastAPI, looper: Looper):
    templates = Jinja2Templates(directory="templates")

    @app.get("/")
    async def home():
        return RedirectResponse("/looper")

    def _tracks_context(request: Request) -> Dict:
        return {
            "request": request,
            "track_ids": list(range(looper.config.tracks_num)),
            "tracks_num": looper.config.tracks_num,
            "tracks": looper.tracks,
        }


    @app.get("/looper", response_class=HTMLResponse)
    async def view_looper(request: Request):
        return templates.TemplateResponse("looper.html", _tracks_context(request))

    @app.get("/master", response_class=HTMLResponse)
    async def view_master(request: Request):
        return templates.TemplateResponse("master.html", _tracks_context(request))

    @app.get("/volume", response_class=HTMLResponse)
    async def view_volume(request: Request):
        return templates.TemplateResponse("volume.html", _tracks_context(request))

    @app.get("/plot", response_class=HTMLResponse)
    async def view_volume(request: Request):
        return templates.TemplateResponse("plot.html", _tracks_context(request))

    @app.get("/recordings", response_class=HTMLResponse)
    async def view_recordings(request: Request):
        return templates.TemplateResponse("recordings.html", {
            "request": request,
            "recordings": looper.recorder.list_recordings(),
        })

    @app.get("/metronome", response_class=HTMLResponse)
    async def view_metronome(request: Request):
        return templates.TemplateResponse("metronome.html", _tracks_context(request))

    @app.get("/manage", response_class=HTMLResponse)
    async def view_manage(request: Request):
        return templates.TemplateResponse("manage.html", _tracks_context(request))
