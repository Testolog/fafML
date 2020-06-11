import functools
import os
from pathlib import Path

from faf_ml.constant import FAILED_FILE, SUCCESS_FILE


def dump_flag(process_location, default=None):
    failed_path = os.path.join(process_location, FAILED_FILE)
    success_path = os.path.join(process_location, SUCCESS_FILE)
    if os.path.exists(failed_path):
        os.remove(failed_path)

    def _call_func(func):
        @functools.wraps(func)
        def _inner_call(*args, **kwargs):
            try:
                value = func(*args, **kwargs) if not os.path.exists(success_path) else default
                Path(success_path).touch()
                return value
            except Exception as inst:
                Path(failed_path).touch()
                raise inst

        return _inner_call

    return _call_func
