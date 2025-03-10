import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("End migration process")
