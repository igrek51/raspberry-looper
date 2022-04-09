import time
from contextlib import contextmanager


@contextmanager
def measure_duration(context: str):
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        minutes = int(duration // 60)
        seconds = duration % 60
        duration_human = (f'{minutes}min ' if minutes else '') + f'{seconds:.2f}s'
        print(f'{context} done in {duration_human}')
