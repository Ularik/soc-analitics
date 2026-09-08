import logging
import sys


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    # fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)