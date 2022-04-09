from dataclasses import dataclass
import datetime
from enum import Enum
import os
from typing import List
from pathlib import Path
import pickle

from pydub import AudioSegment
from nuclear.sublog import log

from looper.runner.config import Config
from looper.runner.looper import LoopPhase, Looper
from looper.runner.track import Track


@dataclass
class SessionMetadata:
    filename: str
    filesize_mb: float


@dataclass
class Session:
    name: str
    input_volume: float
    output_volume: float
    tracks: List[Track]


class SessionManagerPhase(Enum):
    IDLE = 1
    BUSY = 2  # saving/loading session files


@dataclass
class SessionManager:
    looper: Looper
    phase: SessionManagerPhase = SessionManagerPhase.IDLE

    def save_session(self, name: str):
        if self.phase == SessionManagerPhase.BUSY:
            raise RuntimeError('Recorder is BUSY')
        self.phase = SessionManagerPhase.BUSY

        config = self.looper.config
        if not name:
            name = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        Path(config.output_sessions_dir).mkdir(exist_ok=True, parents=True)
        session_path = Path(config.output_sessions_dir) / f'{name}.pickle'

        log.debug('saving current session', file=session_path)

        session = Session(
            name=name,
            input_volume=self.looper.input_volume,
            output_volume=self.looper.output_volume,
            tracks=self.looper.tracks,
        )

        with open(session_path, 'wb') as handle:
            pickle.dump(session, handle, protocol=pickle.HIGHEST_PROTOCOL)

        self.phase = SessionManagerPhase.IDLE
        filesize_mb = os.path.getsize(str(session_path)) / 1024 / 1024
        log.info('Session saved', file=session_path, size=f'{filesize_mb:.2f}MB')


    def restore_session(self, filename: str):
        if self.phase == SessionManagerPhase.BUSY:
            raise RuntimeError('Recorder is BUSY')
        self.phase = SessionManagerPhase.BUSY

        config = self.looper.config
        looper = self.looper
        session_path = Path(config.output_sessions_dir) / filename
        assert session_path.is_file(), 'session file doesnt exist'

        log.debug('restoring session', file=session_path)

        with open(session_path, 'rb') as handle:
            session: Session = pickle.load(handle)

        looper.reset()

        with looper._lock:
            looper.input_volume = session.input_volume
            looper.output_volume = session.output_volume
            looper.tracks = session.tracks
            for track in looper.tracks:
                track.recording = False
                track.playing = False

            looper.config.tracks_num = len(looper.tracks)
            looper.master_chunks = session.tracks[0].loop_chunks

            self.current_position = 0
            self.phase = LoopPhase.LOOP

        self.phase = SessionManagerPhase.IDLE
        filesize_mb = os.path.getsize(str(session_path)) / 1024 / 1024
        log.info('Session restored', file=session_path, size=f'{filesize_mb:.2f}MB')


    def list_sessions(self) -> List[SessionMetadata]:
        sessions = []
        dirpath = Path(self.looper.config.output_sessions_dir)
        dirpath.mkdir(exist_ok=True, parents=True)
        for path in dirpath.glob('*'):
            filesize_mb = os.path.getsize(path) / 1024 / 1024
            filename = path.name
            sessions.append(SessionMetadata(filename, filesize_mb))
        return sorted(sessions, key=lambda r: r.filename)
