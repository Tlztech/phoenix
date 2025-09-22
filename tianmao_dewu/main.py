import sys
import os


sys.path.append(os.path.abspath('.'))  # 添加当前目录到 sys.path
from util import log_util, env_util

import importlib.util
import traceback

if __name__ == "__main__":
    try:
        log_util.init()
        log_util.info('app start')
        module = env_util.get_env('service_module')
        module = importlib.import_module(module)
        module.service()
    except FileNotFoundError:
        log_util.error(f"错误：模块文件不存在 {module}")
    except Exception as e:
        log_util.error(f"发生未知错误: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
    finally:
        log_util.info('app end')
