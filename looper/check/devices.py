from typing import Tuple, Dict

import pyaudio
from looper.runner.config import Config
from nuclear.sublog import log
from nuclear import shell


def list_devices():
    log.info(f'Listing sound cards (for JACK)')
    shell('cat /proc/asound/cards')

    pa = pyaudio.PyAudio()
    devices_num = pa.get_device_count()
    log.info(f'Found {devices_num} devices.')
    candidates = []

    for i in range(devices_num):
        info = pa.get_device_info_by_index(i)
        if info.get('maxInputChannels', 0) > 0 \
            and info.get('maxOutputChannels', 0) > 0:
            candidates.append(info)
        log.info(f'INDEX {i}: {info["name"]}', **info)

    if candidates:
        for info in candidates:
            log.info("Found device with input/output channels. This is probably the one you're looking for", **info)
    else:
        log.warn("Can't find any device with input and output channels.")

    pa.terminate()


def populate_devices(pa: pyaudio.PyAudio) -> Dict:
    devices = {}
    devices_num = pa.get_device_count()
    for i in range(devices_num):
        info = pa.get_device_info_by_index(i)
        if info.get('maxInputChannels', 0) > 0 \
            and info.get('maxOutputChannels', 0) > 0:
            name = info["name"]
            devices[name] = info
    return devices


def verify_device_index(device_index: int, pa: pyaudio.PyAudio):
    info = pa.get_device_info_by_index(device_index)
    assert info.get('maxInputChannels', 0) > 0, 'device has no input channels'
    assert info.get('maxOutputChannels', 0) > 0, 'device has no output channels'
    return info


def find_device_index(config: Config, pa: pyaudio.PyAudio) -> Tuple[int, int]:
    in_device = config.in_device
    out_device = config.out_device
    
    if in_device >= 0 and out_device >= 0:
        if in_device == out_device:
            device = verify_device_index(in_device, pa)
            name = device['name']
            log.info(f'using selected device "{name}" (index {in_device})')
        return in_device, out_device

    default_devices = []

    devices = populate_devices(pa)
    assert devices, 'no devices found'

    for devname in default_devices:
        device = devices.get(devname)
        if device is not None:
            index = device['index']
            name = device['name']
            log.info(f'default device found, using device "{name}" (index {index})')
            return index, index

    # get device with lowest index
    device = min(devices.values(), key=lambda x: x['index'])
    index = device['index']
    name = device['name']
    log.info(f'device chosen automatically, using device "{name}" (index {index})')
    return index, index
