"""Set up ordinary preparation logs for one command, then restore the caller."""

import logging


def start_preparation_logging():
    """Return the handler and old settings needed by the command's finally block."""
    logger = logging.getLogger("kelpseg.prepare")
    previous = (logger.level, logger.propagate)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return handler, previous


def stop_preparation_logging(handler, previous) -> None:
    """Remove this command's handler, including when it failed or was interrupted."""
    logger = logging.getLogger("kelpseg.prepare")
    logger.removeHandler(handler)
    logger.setLevel(previous[0])
    logger.propagate = previous[1]
    handler.close()
