import pandas as pd

from util import log_util


class ExcelUtil:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None

    def load_data(self, columns: list[int], rows_from=0):
        try:
            self.df = pd.read_excel(self.file_path, usecols=columns, header=None, skiprows=rows_from)
            # self.df = self.df.fillna(value=None)  # 适用于整个DataFrame:ml-citation{ref="5,7" data="citationList"}
        except FileNotFoundError as fnfe:
            log_util.error("入力数据文件未找到，请检查文件路径是否正确。")
            raise fnfe
        except PermissionError as pe:
            log_util.error("没有权限读取文件，请确保你有足够的权限。")
            raise pe
        except Exception as e:
            log_util.error(f"发生了一个错误：{e}")
            raise e

    def get_group_by_column(self, group_column):
        # 转换为字典列表格式
        records = self.df.to_dict('records')
        result = {}

        for record in records:
            key = record[group_column]
            if key not in result:
                result[key] = []
            result[key].append(record)

        return result

    def write_excel(self, data):
        try:
            df = pd.DataFrame(data)
            df.to_excel(self.file_path, na_rep='', index=False)
        except FileNotFoundError as fnfe:
            log_util.error("生成文件未找到，请检查文件路径是否正确。")
            raise fnfe
        except PermissionError as pe:
            log_util.error(f"没有权限写文件，请确保你有足够的权限。 {pe}")
            raise pe
        except Exception as e:
            log_util.error(f"发生了一个错误：{e}")
            raise e
