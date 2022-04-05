

from looper.runner.track import shift_loop_position


def test_shift_loop_position():
    assert shift_loop_position(7, 5, 10) == 2
    assert shift_loop_position(2, -4, 10) == 8
    assert shift_loop_position(0, -1, 10) == 9
