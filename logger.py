import logging

from rich.logging import RichHandler

logging.basicConfig(
    #stream=sys.stdout,
    format='%(message)s',
    handlers=[RichHandler(markup=True, rich_tracebacks=False, show_time=False, show_path=False)]
)
logger = logging.getLogger('gd5')
logger.setLevel(logging.DEBUG)
