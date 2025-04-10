import pandas as pd
import os

from constant import excel
from util import log_util

_contacts = []


# 读取Excel文件
def read_excel(file_path, columns):
    try:
        df = pd.read_excel(file_path, dtype={columns[0]: str})
        contacts = df[columns].fillna('None').to_dict('records')
        global _contacts
        _contacts = contacts
    except FileNotFoundError as fnfe:
        log_util.error("入力数据文件未找到，请检查文件路径是否正确。")
        raise fnfe
    except PermissionError as pe:
        log_util.error("没有权限读取文件，请确保你有足够的权限。")
        raise pe
    except Exception as e:
        log_util.error(f"发生了一个错误：{e}")
        raise e


def get_data_list_no_none(column, columns):
    return [contact[columns[column]] for contact in _contacts if contact[columns[column]] != 'None']


def write_excel(file_path, data):
    try:
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)
    except FileNotFoundError as fnfe:
        log_util.error("生成文件未找到，请检查文件路径是否正确。")
        raise fnfe
    except PermissionError as pe:
        log_util.error(f"没有权限写文件，请确保你有足够的权限。 {pe}")
        raise pe
    except Exception as e:
        log_util.error(f"发生了一个错误：{e}")
        raise e

