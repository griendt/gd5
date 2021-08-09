import logging
from rich.logging import RichHandler

logging.basicConfig(
    format='%(message)s',
    handlers=[RichHandler(markup=True, rich_tracebacks=True, show_time=False)]
)
logger = logging.getLogger('gd5')
logger.setLevel(logging.DEBUG)
