import datetime
import logging
import sys
from pathlib import Path

from loguru import logger


def setup_logging(terminal_loglevel: str = "INFO", logfile_loglevel: str = "DEBUG", root_logger_loglevel: str = "ERROR",
                  logfile_dir=None, enqueue=True) -> None:
    """Setup loguru logger (use loguru because it has thread- and process-safe logging).

    Args:
        terminal_loglevel (str): Log level of the terminal output.
        logfile_loglevel (str): Log level of the log file.
        root_logger_loglevel (str): Log level of the root logger (ie. logger from imported libraries)
        logfile_dir: Directory to store the log file.
        enqueue (bool): Wait until a thread or process has finished before outputting the logs for that thread/process.

    Returns:
        None
    """
    # Intercept loggers from imported libraries and redirect them to loguru
    # (https://github.com/Delgan/loguru#entirely-compatible-with-standard-logging)
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            # Following is modified from https://github.com/Delgan/loguru/issues/396
            loguru_opt = logger.opt(depth=depth, exception=record.exc_info)
            loguru_opt.bind(intercepted=True).log(level, record.getMessage())
    # Get the root logger and add the InterceptHandler()
    root_logger = logging.getLogger()
    root_logger.setLevel(root_logger_loglevel.upper())
    root_logger.handlers = [InterceptHandler()]
    # NOTE: The following code can be used to only intercept some libraries instead of the entire root logger.
    # intercept_libraries = ['sentinelsat']  # Provide this as input argument to this function (ie. setup_logging())
    # if intercept_libraries is not None:  # If libraries to intercept has been provided
    #     if not isinstance(intercept_libraries, (list, tuple)):  # Ensure that libraries are in a list or tuple
    #         intercept_libraries = [intercept_libraries]
    #     logger_list = []  # Instantiate list to store the loggers from the individual libraries
    #     for i, library in enumerate(intercept_libraries):  # Loop through the libraries
    #         logger_list.append(logging.getLogger(library))  # Get the logger and append it to the list of loggers
    #         logger_list[i].addHandler(InterceptHandler())  # Intercept the logger and re-direct to loguru
    #         logger_list[i].propagate = False  # Silence original logger (https://github.com/Delgan/loguru/issues/328)

    # Define the formatting. Add padding to vertically align lines and use different colors for intercepted loggers.
    # (https://loguru.readthedocs.io/en/latest/resources/recipes.html#dynamically-formatting-messages-to-properly-align-values-with-padding)
    class Formatter:
        def __init__(self):
            self.padding = 52

        def format(self, record):
            length = len("{name}:{function}:{line}".format(**record))
            self.padding = max(self.padding, length)
            record["extra"]["padding"] = " " * (self.padding - length)
            if record["extra"].get("intercepted", False):  # Format for intercepted loggers
                fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS!UTC} UTC</green> | " \
                      "<level>{level: <8}</level> | " \
                      "<magenta>{name}</magenta>:<magenta>{function}</magenta>:" \
                      "<magenta>{line}</magenta>{extra[padding]} | " \
                      "<level>{message}</level>\n{exception}"
            else:  # Format for our own logger
                fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS!UTC} UTC</green> | " \
                      "<level>{level: <8}</level> | " \
                      "<cyan>{name}</cyan>:<cyan>{function}</cyan>:" \
                      "<cyan>{line}</cyan>{extra[padding]} | " \
                      "<level>{message}</level>\n{exception}"
            return fmt
    formatter = Formatter()

    # Remove standard loguru logger and re-add it with configured log-level and formatter
    # Note: Loguru is not designed to configure handlers, so it is easier to remove and re-add them again
    logger.remove()
    logger.add(sys.stdout, enqueue=enqueue, format=formatter.format, level=terminal_loglevel.upper())

    # Also save the logs to logfile
    t = datetime.datetime.now(datetime.timezone.utc)
    file_name_format = f'{t.year:04d}{t.month:02d}{t.day:02d}-{t.hour:02d}{t.minute:02d}{t.second:02d}-UTC.log'
    if logfile_dir is None:
        logfile_dir = Path(f'/tmp/python_logs/')
    logfile_path = logfile_dir / file_name_format
    logger.add(logfile_path, enqueue=enqueue, format=formatter.format, level=logfile_loglevel.upper())

    # Log the different levels to see result
    # logger.debug("Test debug")
    # logger.info("Test info")
    # logger.warning("Test warning")
    # logger.error("Test error")
    # logger.critical("Test fatal")

