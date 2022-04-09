import asyncio
import os
import time
from pathlib import Path

from nuclear.sublog import log
from nuclear.utils.shell import shell
from gpiozero import BadPinFactory

from looper.runner.server import Server, start_api
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
    _change_workdir(config.workdir)

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

    server: Server = start_api(looper)

    log.info('Ready to work')
    try:
        asyncio.run(main_async_loop(looper))
    except KeyboardInterrupt:
        looper.close()
        server.stop()


def _change_workdir(workdir: str):
    if Path(workdir).is_dir():
        os.chdir(workdir)
    else:
        log.warn(f"can't change working directory to {workdir}")


async def main_async_loop(looper: Looper):
    await asyncio.gather(
        progress_loop(looper),
        update_leds_loop(looper),
    )


async def progress_loop(looper: Looper):
    if looper.config.online:
        while True:
            await looper.update_progress()


async def update_leds_loop(looper: Looper):
    if looper.config.online:
        while True:
            looper.update_leds()
            await asyncio.sleep(1)


def shutdown(looper: Looper):
    log.info('shutting down...')
    looper.close()
    looper.pinout.loopback_led.blink(on_time=0.04, off_time=0.04)
    time.sleep(0.5)
    shell('sudo shutdown -h now')
