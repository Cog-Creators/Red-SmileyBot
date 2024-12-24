import functools
import logging
import os

if os.getenv("RED_INSPECT_DRIVER_QUERIES"):
    LOGGING_INVISIBLE = logging.DEBUG
else:
    LOGGING_INVISIBLE = 0

log = logging.getLogger("red.driver")
log.invisible = functools.partial(log.log, LOGGING_INVISIBLE)
