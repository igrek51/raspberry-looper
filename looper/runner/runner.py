import asyncio
import dataclasses
import os
import time
from pathlib import Path
from typing import Dict, Optional
import yaml

from nuclear.sublog import log
from nuclear.utils.shell import shell
from gpiozero import BadPinFactory
import dacite

from looper.runner.server import Server, start_api
from looper.runner.config import AudioBackendType, Config
from looper.runner.pinout import Pinout
from looper.runner.looper import Looper


def run_looper(audio_backend_type: Optional[str] = None):
    log.info('Starting looper...')
    config = load_config()
    if audio_backend_type:
        config.audio_backend = AudioBackendType(audio_backend_type)

    try:
        pinout = Pinout()
    except BadPinFactory:
        log.warn('GPIO pins are not available, turning OFFLINE mode')
        config.offline = True
        pinout = None

    log.info('Config loaded', 
        audio_backend=config.audio_backend_type.value,
        offline_mode=config.offline,
        sampling_rate=f'{config.sampling_rate}Hz',
        chunk_size=f'{config.chunk_size} samples',
        chunk_length=f'{config.chunk_length_ms:.2f}ms',
        format_bytes=config.format_bytes,
        channels=config.channels,
        in_device=config.in_device,
        out_device=config.out_device,
        number_of_tracks=config.tracks_num,
        gpio_tracks=config.tracks_gpio_num,
        output_recordings_dir=config.output_recordings_dir,
        output_sessions_dir=config.output_sessions_dir,
        metronome_volume=f'{config.metronome_volume}dB',
        http_port=config.http_port,
    )
    
    _change_workdir(config.workdir)

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
        log.warn(f"can't change working directory to {workdir}, running in {os.getcwd()}")


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
    while True:
        if looper.config.online:
            looper.update_leds()
        await asyncio.sleep(1)


def shutdown(looper: Looper):
    log.info('shutting down...')
    looper.close()
    looper.pinout.loopback_led.blink(on_time=0.04, off_time=0.04)
    time.sleep(0.5)
    shell('sudo shutdown -h now')


def load_config() -> Config:
    config_file_path = os.environ.get('CONFIG_FILE')
    if not config_file_path:
        log.info('CONFIG_FILE unspecified, loading default config')
        return Config()

    path = Path(config_file_path)
    if not path.is_file():
        raise FileNotFoundError(f"config file {config_file_path} doesn't exist")

    try:
        with path.open() as file:
            config_dict = yaml.load(file, Loader=yaml.FullLoader)
            config = dacite.from_dict(
                data_class=Config,
                data=config_dict,
                config=dacite.Config(cast=[AudioBackendType]),
            )
            log.info(f'config loaded from {config_file_path}: {config_dict}')
            return config
    except Exception as e:
        raise RuntimeError('loading config failed') from e
