import asyncio
import time

from nuclear.sublog import log
from nuclear.utils.shell import shell
from gpiozero import BadPinFactory

from looper.runner.server import start_api
from looper.runner.config import Config
from looper.runner.pinout import Pinout
from looper.runner.looper import Looper


def run_looper():
    log.info('Starting looper...')
    config = Config()
    log.info('Config loaded', 
        sampling_rate=f'{config.sampling_rate}Hz',
        chunk_size=f'{config.chunk_size} samples',
        chunk_length=f'{config.chunk_length_ms:.2f}ms',
        format_bytes=config.format_bytes,
        in_device=config.in_device,
        out_device=config.out_device,
        channels=config.channels,
    )

    try:
        pinout = Pinout()
    except BadPinFactory:
        log.warn('GPIO pins are not available, turning OFFLINE mode')
        config.offline = True
        pinout = None

    looper = Looper(pinout, config)
    looper.run()

    if config.online:
        pinout.shutdown_button.when_held = lambda: shutdown(looper)

    server = start_api()

    log.info('Ready to work')
    try:
        asyncio.run(main_async_loop(looper))
    except KeyboardInterrupt:
        looper.close()
        server.stop()


async def main_async_loop(looper: Looper):
    await asyncio.gather(
        progress_loop(looper),
    )


async def progress_loop(looper: Looper):
    while True:
        await looper.update_progress()


def shutdown(looper: Looper):
    log.info('shutting down...')
    looper.close()
    looper.pinout.loopback_led.blink(on_time=0.04, off_time=0.04)
    time.sleep(0.5)
    shell('sudo shutdown -h now')
