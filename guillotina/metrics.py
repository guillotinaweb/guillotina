from prometheus_client import Counter
from prometheus_client import Histogram
from typing import Dict
from typing import Optional
from typing import Type

import time
import traceback


ERROR_NONE = "none"
ERROR_GENERAL_EXCEPTION = "exception"


class watch:
    start: float

    def __init__(
        self,
        *,
        counter: Optional[Counter] = None,
        histogram: Optional[Histogram] = None,
        error_mappings: Dict[str, Type[Exception]] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        self.counter = counter
        self.histogram = histogram
        self.labels = labels or {}
        self.error_mappings = error_mappings or {}

    def __enter__(self):
        self.start = time.time()

    def __exit__(
        self,
        exc_type: Optional[Type[Exception]],
        exc_value: Optional[Exception],
        exc_traceback: Optional[traceback.StackSummary],
    ):
        error = ERROR_NONE
        if self.histogram is not None:
            finished = time.time()
            if len(self.labels) > 0:
                self.histogram.labels(**self.labels).observe(finished - self.start)
            else:
                self.histogram.observe(finished - self.start)

        if self.counter is not None:
            if exc_value is None:
                error = ERROR_NONE
            else:
                for error_type, mapped_exc_type in self.error_mappings.items():
                    if isinstance(exc_value, mapped_exc_type):
                        error = error_type
                        break
                else:
                    error = ERROR_GENERAL_EXCEPTION
            self.counter.labels(error=error, **self.labels).inc()