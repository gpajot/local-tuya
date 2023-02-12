import logging

import pytest

from local_tuya.domoticz.logger import DomoticzHandler
from local_tuya.domoticz.types import DomoticzEx


@pytest.fixture()
def logger():
    logger = logging.getLogger(__name__)
    initial_level = logger.level
    logger.setLevel(logging.DEBUG)
    yield logger
    logger.setLevel(initial_level)


@pytest.fixture()
def domoticz_logger(mocker, logger):
    handler = DomoticzHandler()
    logger.addHandler(handler)
    yield mocker.patch("local_tuya.domoticz.logger.DomoticzEx", spec=DomoticzEx)
    logger.removeHandler(handler)


def test_debug(logger, domoticz_logger):
    logger.debug("the message")
    domoticz_logger.Log.assert_called_once_with(f"DEBUG: {__name__}: the message")


def test_info(logger, domoticz_logger):
    logger.info("the message")
    domoticz_logger.Status.assert_called_once_with(f"INFO: {__name__}: the message")


def test_warning(logger, domoticz_logger):
    logger.warning("the message")
    domoticz_logger.Error.assert_called_once_with(f"WARNING: {__name__}: the message")


def test_error(logger, domoticz_logger):
    logger.error("the message")
    domoticz_logger.Error.assert_called_once_with(f"ERROR: {__name__}: the message")


def test_exception(logger, domoticz_logger):
    try:
        raise ValueError("err")
    except ValueError:
        logger.exception("the message")
    domoticz_logger.Error.assert_called_once()
    log = domoticz_logger.Error.call_args[0][0]
    assert log.startswith(f"ERROR: {__name__}: the message")
    assert log.endswith("ValueError: err")
