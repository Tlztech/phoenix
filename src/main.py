import sys
import os

sys.path.append(os.path.abspath('.'))  # 添加当前目录到 sys.path

from util import excel_util, yaml_util, env_util, log_util
from constant import excel
import importlib.util

if __name__ == "__main__":

    try:
        log_util.init()
        log_util.info('app start')
        module = env_util.get_env('service_module')
        # 读取Excel数据
        excel_util.read_excel(env_util.get_env('EXCEL_INPUT_FILE'), excel.COLUMNS_NAMES)
        yaml_util.read_yaml(env_util.get_env('DICT_FILE'))
        module = importlib.import_module(module)
        module.service()
    except FileNotFoundError:
        log_util.error(f"错误：模块文件不存在 {module}")
    except Exception as e:
        log_util.error(f"发生未知错误: {str(e)}")

    log_util.info('app end')
