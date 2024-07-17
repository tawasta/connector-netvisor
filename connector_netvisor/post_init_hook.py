import logging

_logger = logging.getLogger(__name__)


def init_netvisor_data(env):
    _logger.info("Adding Netvisor codes to taxes")
    env["account.tax"]._init_netvisor_codes()
