import pyaudio
from nuclear.sublog import log


def list_devices():
    pa = pyaudio.PyAudio()
    devices_num = pa.get_device_count()
    log.info(f'Found {devices_num} devices.')

    for i in range(devices_num):
        info = pa.get_device_info_by_index(i)["name"]
        log.info(f'INDEX {i}: {info}')

    pa.terminate()
