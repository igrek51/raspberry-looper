from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

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

    @app.get("/master", response_class=HTMLResponse)
    async def view_master(request: Request):
        return templates.TemplateResponse("master.html", {
            "request": request,
        })

    @app.get("/volume", response_class=HTMLResponse)
    async def view_volume(request: Request):
        return templates.TemplateResponse("volume.html", {
            "request": request,
            "track_ids": list(range(looper.config.tracks_num)),
        })

    @app.get("/plot", response_class=HTMLResponse)
    async def view_volume(request: Request):
        return templates.TemplateResponse("plot.html", {
            "request": request,
            "track_ids": list(range(looper.config.tracks_num)),
        })

    @app.get("/recordings", response_class=HTMLResponse)
    async def view_recordings(request: Request):
        return templates.TemplateResponse("recordings.html", {
            "request": request,
            "recordings": looper.recorder.list_recordings(),
        })
