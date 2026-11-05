"""Set up ordinary workflow logs for one command, then restore the caller."""

import logging


def start_preparation_logging(
    logger_name: str = "kelpseg.prepare",
) -> tuple[logging.StreamHandler, tuple[int, bool]]:
    """Return the handler and old settings needed by the command's finally block."""
    logger = logging.getLogger(logger_name)
    previous = (logger.level, logger.propagate)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return handler, previous


def stop_preparation_logging(
    handler: logging.StreamHandler,
    previous: tuple[int, bool],
    logger_name: str = "kelpseg.prepare",
) -> None:
    """Remove this command's handler, including when it failed or was interrupted."""
    logger = logging.getLogger(logger_name)
    logger.removeHandler(handler)
    logger.setLevel(previous[0])
    logger.propagate = previous[1]
    handler.close()
