import logging
import os
import tempfile

from utils.bot_logging import setup_bot_logging


def test_setup_bot_logging_writes_to_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'bot.log')
        os.environ['BOT_LOG_PATH'] = path
        logger = setup_bot_logging()
        logger.info('test line')
        for handler in logging.root.handlers:
            handler.flush()
        with open(path, encoding='utf-8') as fh:
            body = fh.read()
        assert 'test line' in body
        del os.environ['BOT_LOG_PATH']


if __name__ == '__main__':
    test_setup_bot_logging_writes_to_file()
    print('bot_logging: ok')
