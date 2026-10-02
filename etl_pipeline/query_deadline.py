"""A shared absolute query budget checked at each expensive stage."""

import time

from etl_pipeline.model_errors import ModelTimeout


def check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise ModelTimeout("Query deadline exceeded")
