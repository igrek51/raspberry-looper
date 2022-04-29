from typing import Tuple, Dict

import pyaudio
from nuclear.sublog import log


def list_devices():
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


def find_device_index(in_device: int, out_device: int, online: bool, pa: pyaudio.PyAudio) -> Tuple[int, int]:
    if online:
        if in_device == out_device:
            verify_device_index(in_device, pa)
        return in_device, out_device
    else:
        devices = populate_devices(pa)
        assert devices, 'no devices found'

        for devname in ['default', 'pulse', 'sysdefault']:
            device = devices.get(devname)
            if device is not None:
                index = device['index']
                name = device['name']
                log.info(f'using device "{name}" (index {index})')
                return index, index

        # get device with lowest index
        device = min(devices.values(), key=lambda x: x['index'])
        index = device['index']
        name = device['name']
        log.info(f'using device {name} (index {index})')
        return index, index
