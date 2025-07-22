import logging
import logging.config


def init_logging():
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "file_handler": {
                    "class": "logging.FileHandler",
                    "formatter": "standard",
                    "filename": "elma_recplot.log",
                },
                "console_handler": {
                    "class": "rich.logging.RichHandler",
                    "level": "DEBUG",
                },
            },
            "root": {
                "handlers": ["file_handler", "console_handler"],
                "level": "DEBUG",
            },
        }
    )


if __name__ == "__main__":
    init_logging()
    print("Hello")
    logging.debug("HI")