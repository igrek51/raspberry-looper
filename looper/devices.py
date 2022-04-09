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
            and info.get('maxOutputChannels', 0) > 0 \
            and info.get('name') not in {'default', 'pulse'}:
            candidates.append(info)
        log.info(f'INDEX {i}: {info["name"]}', **info)

    if candidates:
        for info in candidates:
            log.info("Found device with input/output channels. This is probably the one you're looking for", **info)
    else:
        log.warn("Can't find any device with input and output channels.")

    pa.terminate()


def verify_device_index(device_index: int, pa: pyaudio.PyAudio):
    info = pa.get_device_info_by_index(device_index)
    assert info.get('maxInputChannels', 0) > 0, 'device has no input channels'
    assert info.get('maxOutputChannels', 0) > 0, 'device has no output channels'
