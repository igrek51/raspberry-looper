from typing import Dict, List, Iterable

from fastapi import FastAPI

from looper.runner.looper import Looper


def setup_looper_endpoints(app: FastAPI, looper: Looper):

    @app.get("/api/player")
    async def get_player_status():
        return await _get_player_status(looper)


    @app.get("/api/track")
    async def get_all_tracks_status():
        return [item async for item in _get_all_tracks_info(looper)]

    @app.get("/api/track/{track_id}")
    async def get_track_status(track_id: int):
        return await _get_track_info(looper, track_id)

    @app.post("/api/track/{track_id}/record")
    async def toggle_track_recording(track_id: int):
        looper.toggle_record(track_id)

    @app.post("/api/track/{track_id}/play")
    async def toggle_track_playing(track_id: int):
        looper.toggle_play(track_id)

    @app.post("/api/track/{track_id}/reset")
    async def reset_track(track_id: int):
        looper.reset_track(track_id)


    @app.post("/api/save/start")
    async def start_saving_output_to_file():
        looper.saver.start_saving()

    @app.post("/api/save/stop")
    async def stop_saving_output_to_file():
        looper.saver.stop_saving()

    @app.post("/api/save")
    async def toggle_saving_output_to_file():
        looper.saver.toggle_saving()



async def _get_track_info(looper: Looper, track_id: int) -> Dict:
    return {
        'index': looper.tracks[track_id].index,
        'recording': looper.tracks[track_id].recording,
        'playing': looper.tracks[track_id].playing,
        'empty': looper.tracks[track_id].empty,
    }


async def _get_all_tracks_info(looper: Looper) -> Iterable[Dict]:
    for track in looper.tracks:
        yield {
            'index': track.index,
            'recording': track.recording,
            'playing': track.playing,
            'empty': track.empty,
        }


async def _get_player_status(looper: Looper) -> Dict:
    return {
        'phase': looper.phase.name,
        'position': looper.current_position,
        'loop_duration': looper.loop_duration,
    }
