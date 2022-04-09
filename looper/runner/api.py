from typing import Dict, Iterable

from fastapi import FastAPI
from nuclear.sublog import log

from looper.runner.looper import Looper
from looper.runner.plot import generate_track_plot


def setup_looper_endpoints(app: FastAPI, looper: Looper):

    @app.get("/api/player")
    async def get_player_status():
        return await _get_player_status(looper)

    # Tracks
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

    @app.post("/api/track/add")
    async def add_new_track():
        return looper.add_track()

    # Output Recorder
    @app.get("/api/recorder")
    async def get_output_recorder_status():
        return {
            'phase': looper.recorder.phase.name,
            'recorded_duration': looper.recorder.recorded_duration,
        }

    @app.post("/api/recorder/start")
    async def start_saving_output_to_file():
        looper.recorder.start_saving()

    @app.post("/api/recorder/stop")
    async def stop_saving_output_to_file():
        looper.recorder.stop_saving()

    @app.post("/api/recorder/toggle")
    async def toggle_saving_output_to_file():
        looper.recorder.toggle_saving()

    # Input Volume
    @app.get("/api/volume/input")
    async def get_input_volume():
        return {
            'volume': looper.input_volume,
            'muted': looper.input_muted,
        }

    @app.post("/api/volume/input/set/{volume}")
    async def set_input_volume(volume: float):
        looper.input_volume = volume
        log.info('input volume set', volume=f'{volume}dB')

    @app.post("/api/volume/input/mute")
    async def toggle_mute_input_volume():
        looper.toggle_input_mute()

    # Output Volume
    @app.get("/api/volume/output")
    async def get_output_volume():
        return {
            'volume': looper.output_volume,
            'muted': looper.output_muted,
        }

    @app.post("/api/volume/output/set/{volume}")
    async def set_output_volume(volume: float):
        looper.output_volume = volume
        log.info('output volume set', volume=f'{volume}dB')

    @app.post("/api/volume/output/mute")
    async def toggle_mute_output_volume():
        looper.toggle_output_mute()

    # Tracks Volume
    @app.get("/api/volume/track/{track_id}")
    async def get_track_volume(track_id: int):
        return {
            'volume': looper.tracks[track_id].volume,
        }

    @app.post("/api/volume/track/{track_id}/set/{volume}")
    async def set_track_volume(track_id: int, volume: float):
        looper.tracks[track_id].volume = volume
        log.info('track volume set', track=track_id, volume=f'{volume}dB')

    @app.get("/api/volume/track/{track_id}/loudness")
    async def compute_track_loudness(track_id: int):
        return {
            'loudness': looper.tracks[track_id].compute_loudness(),
        }

    # Track Plots
    @app.get("/api/plot/track/{track_id}")
    async def get_track_plot(track_id: int):
        return generate_track_plot(looper.tracks[track_id], looper)



async def _get_track_info(looper: Looper, track_id: int) -> Dict:
    return {
        'index': looper.tracks[track_id].index,
        'recording': looper.is_recording(track_id),
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
        'progress': looper.relative_progress,
        'loop_duration': looper.loop_duration,
    }
