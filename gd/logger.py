import logging

from rich.logging import RichHandler

old_record_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
    record = old_record_factory(*args, **kwargs)
    record.indent = "  "*getattr(logger, "indents", 0)
    return record


logging.setLogRecordFactory(record_factory)
logging.basicConfig(
    format='%(indent)s%(message)s',
    handlers=[RichHandler(markup=True, rich_tracebacks=False, show_time=False, show_path=False)]
)
logger = logging.getLogger('gd5')
logger.setLevel(logging.INFO)
logger.indents = 0
