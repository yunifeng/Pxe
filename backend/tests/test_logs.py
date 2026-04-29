"""日志模块测试"""
import logging
import os
import tempfile

from app.utils.logs import get_logger, setup_logging


class TestLogging:
    """setup_logging() 测试"""

    def test_returns_logger(self):
        logger = setup_logging(enable_stdout=False, enable_file=False)
        assert isinstance(logger, logging.Logger)

    def test_stdout_handler(self):
        logger = logging.getLogger("pxe-test-stdout")
        logger.handlers.clear()
        logger.setLevel(logging.INFO)
        setup_logging(enable_stdout=True, enable_file=False)
        assert any(
            isinstance(h, logging.StreamHandler)
            for h in logging.getLogger("pxe").handlers
        )

    def test_file_handler_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            pxe_logger = logging.getLogger("pxe")
            pxe_logger.handlers.clear()

            from app.config import settings

            orig = settings.log_dir
            settings.log_dir = tmp
            try:
                logger = setup_logging(enable_stdout=False, enable_file=True)
                logger.info("test")
                assert os.path.exists(os.path.join(tmp, "pxe.log"))
            finally:
                settings.log_dir = orig
                pxe_logger.handlers.clear()

    def test_get_logger_returns_child(self):
        child = get_logger("test")
        assert child.name == "pxe.test"
