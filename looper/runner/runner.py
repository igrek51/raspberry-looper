import asyncio
import os
import time
from pathlib import Path
from typing import Optional
import warnings
from threading import Thread

from nuclear.sublog import log
from nuclear.utils.shell import shell, shell_output
from gpiozero import BadPinFactory, PinFactoryFallback
from getkey import getkey, keys

from looper.runner.server import Server, start_api_in_background
from looper.runner.config import AudioBackendType
from looper.runner.config_load import load_config
from looper.runner.pinout import Pinout
from looper.runner.looper import Looper


def run_looper(config_path: Optional[str], audio_backend_type: Optional[str]):
    log.info('Starting looper...')
    config = load_config(config_path)
    if audio_backend_type:
        config.audio_backend = AudioBackendType(audio_backend_type)

    try:
        warnings.filterwarnings("ignore", category=PinFactoryFallback)
        pinout = Pinout()
    except BadPinFactory:
        log.warn('GPIO pins are not available, turning OFFLINE mode')
        config.offline = True
        pinout = None

    log.info('Current Configuration', 
        audio_backend=config.active_audio_backend_type.value,
        offline_mode=config.offline,
        sample_format=config.sample_format,
        sampling_rate=f'{config.sampling_rate}Hz',
        chunk_size=f'{config.chunk_size} samples',
        chunk_length=f'{config.chunk_length_s * 1000:.2f}ms',
        channels=config.channels,
        in_device=config.in_device,
        out_device=config.out_device,
        number_of_tracks=config.tracks_num,
        gpio_tracks=config.tracks_gpio_num,
        output_recordings_dir=config.output_recordings_dir,
        output_sessions_dir=config.output_sessions_dir,
        metronome_volume=f'{config.metronome_volume}dB',
        http_port=config.http_port,
        spacebar_footswitch=config.spacebar_footswitch,
    )
    
    _change_workdir(config.workdir)

    if config.prioritize_process:
        prioritize_process()

    looper = Looper(pinout, config)
    looper.run()

    if config.online:
        pinout.shutdown_button.when_held = lambda: shutdown(looper)

    server: Server = start_api_in_background(looper)

    log.info('Ready to work')
    try:
        if looper.config.async_loops:
            asyncio.run(main_async_loop(looper, server))
        server.wait()
    except KeyboardInterrupt:
        looper.close()
        server.stop()

    log.debug('Off I go then')


def _change_workdir(workdir: str):
    if Path(workdir).is_dir():
        os.chdir(workdir)
    else:
        log.warn(f"can't change working directory to {workdir}, running in {os.getcwd()}")


async def main_async_loop(looper: Looper, server: Server):
    await asyncio.wait([
            progress_loop(looper),
            update_leds_loop(looper),
            handle_key_press(looper),
        ], return_when=asyncio.FIRST_EXCEPTION)


async def progress_loop(looper: Looper):
    if looper.config.online:
        while True:
            await looper.update_progress()


async def update_leds_loop(looper: Looper):
    while True:
        if looper.config.online:
            looper.update_leds()
        await asyncio.sleep(1)


async def handle_key_press(looper: Looper):
    if looper.config.spacebar_footswitch:

        def read_keys_endless(looper):
            while True:
                key = getkey()
                if key == keys.SPACE:
                    log.debug('Space key pressed, simulating footswitch')
                    looper.on_footswitch_press()

        Thread(target=read_keys_endless, args=(looper,), daemon=True).start()


def prioritize_process():
    pids = shell_output('pgrep -f "looper run"').strip().splitlines()[:-1]
    if not pids:
        log.warn('looper process was not found')
        return
    if len(pids) > 1:
        log.warn('multiple looper process found', pids=pids)
    priority = -20
    shell(f'sudo renice -n {priority} -p {" ".join(pids)}')
    log.info('process reniced with favorable priority', pid=pids[0], priority=priority)


def shutdown(looper: Looper):
    log.info('shutting down...')
    looper.close()
    looper.pinout.loopback_led.blink(on_time=0.04, off_time=0.04)
    time.sleep(0.5)
    shell('sudo shutdown -h now')
