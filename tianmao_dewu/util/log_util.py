import logging
from util import env_util


def init():
    log_level = env_util.get_env('LOG_LEVEL')
    if log_level == 'info':
        level = logging.INFO
    elif log_level == 'debug':
        level = logging.DEBUG
    else:
        level = logging.DEBUG
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    log_file = env_util.get_env('LOG_FILE')  # 日志文件的名字
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    # 将文件处理器添加到根日志记录器中
    logging.getLogger().addHandler(handler)


def info(msg):
    logging.info(msg)


def error(msg):
    logging.error(msg)
