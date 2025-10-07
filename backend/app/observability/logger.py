import logging
from pythonjsonlogger import jsonlogger

def setup_json_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(filename)s %(lineno)d"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
