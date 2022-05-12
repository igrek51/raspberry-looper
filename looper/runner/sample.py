import numpy as np


def sample_format_bytes(sample_format: str) -> int:
    if sample_format == 'int16':
        return 2
    elif sample_format == 'int32':
        return 4
    elif sample_format == 'float32':
        return 4
    raise ValueError(f"Unknown sample format: {sample_format}")


def sample_format_numpy_type(sample_format: str):
    if sample_format == 'int16':
        return np.int16
    elif sample_format == 'int32':
        return np.int32
    elif sample_format == 'float32':
        return np.float32
    raise ValueError(f"Unknown sample format: {sample_format}")


def sample_format_max_amplitude(sample_format: str) -> int:
    """Return full-scale amplitude"""
    if sample_format == 'int16':
        return 32767  # 2**16/2-1
    elif sample_format == 'int32':
        return 2147483647  # 2**32/2-1
    elif sample_format == 'float32':
        return 1
    raise ValueError(f"Unknown sample format: {sample_format}")
