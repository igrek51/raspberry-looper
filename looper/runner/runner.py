from nuclear.sublog import log
from looper.runner.config import Config

from looper.runner.pinout import Pinout
from looper.runner.player import Player


def run_looper():
    log.info('Starting looper...')
    pinout = Pinout()
    config = Config()
    log.info('Config loaded', 
        sampling_rate=f'{config.sampling_rate}Hz',
        chunk_size=f'{config.chunk_size} samples',
        chunk_length=f'{config.chunk_length_ms}ms',
        in_device=config.in_device,
        out_device=config.out_device,
        channels=config.channels,
    )
    player = Player(pinout, config)
    player.run()
