"""Set up ordinary preparation logs for one command, then restore the caller."""

import logging


def start_preparation_logging(
    logger_name: str = "kelpseg.prepare",
) -> tuple[logging.Handler, tuple[int, bool]]:
    """Enable progress for logger_name; return handler and settings for restoration.

    Defaults to preparation commands. Reports use the kelpseg parent to include
    preparation selection and report inference messages in the same stream.
    """
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
    handler: logging.Handler,
    previous: tuple[int, bool],
    logger_name: str = "kelpseg.prepare",
) -> None:
    """Remove handler and restore logger_name from previous; close the stream handler."""
    logger = logging.getLogger(logger_name)
    logger.removeHandler(handler)
    logger.setLevel(previous[0])
    logger.propagate = previous[1]
    handler.close()
