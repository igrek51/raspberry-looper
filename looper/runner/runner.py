import time

from nuclear.sublog import log
from nuclear.utils.shell import shell

from looper.runner.config import Config
from looper.runner.pinout import Pinout
from looper.runner.looper import Looper


def run_looper():
    log.info('Starting looper...')
    pinout = Pinout()
    config = Config()
    log.info('Config loaded', 
        sampling_rate=f'{config.sampling_rate}Hz',
        chunk_size=f'{config.chunk_size} samples',
        chunk_length=f'{round(config.chunk_length_ms, 2)}ms',
        format_bytes=config.format_bytes,
        in_device=config.in_device,
        out_device=config.out_device,
        channels=config.channels,
    )
    player = Looper(pinout, config)

    pinout.shutdown_button.when_held = lambda: shutdown(player)
    
    player.run()


def shutdown(player: Looper):
    log.info('shutting down...')
    player.close()
    player.pinout.loopback_led.blink(on_time=0.04, off_time=0.04)
    time.sleep(0.5)
    shell('sudo shutdown -h now')
