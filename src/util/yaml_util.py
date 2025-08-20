import copy
import yaml

from util import log_util

_dict = {}


def read_yaml(file_path: str) -> dict:
    try:
        """读取 YAML 文件并返回字典"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)  # 使用 safe_load 避免潜在的安全风险
        global _dict
        _dict = data
    except FileNotFoundError:
        log_util.error("模板文件未找到，请检查文件路径是否正确。")
    except PermissionError:
        log_util.error("没有权限读取文件，请确保你有足够的权限。")
    except Exception as e:
        log_util.error(f"发生了一个错误：{e}")


def get_object_actions_top(brand: str, host: str, o='price'):
    actions = []
    for data in _dict:
        if 'brand' in data and data['brand'] and data['brand'] == brand:
            for target in data['targets']:
                if target['host'] == host:
                    objects = target['objects']
                    for obj in objects:
                        if o in obj['object']:
                            return copy.deepcopy(obj['actions'])
            break
    return actions


def get_object_price_actions_top(brand: str, host: str):
    actions = []
    for data in _dict:
        if 'brand' in data and data['brand'] and data['brand'] == brand:
            for target in data['targets']:
                if target['host'] == host:
                    objects = target['objects']
                    for obj in objects:
                        if obj['object'] == 'price':
                            return copy.deepcopy(obj['actions'])
            break
    return actions


def get_brand_hosts(brand: str):
    hosts = []
    for data in _dict:
        if 'brand' in data and data['brand'] and data['brand'] == brand:
            for target in data['targets']:
                if 'host' in target and target['host']:
                    hosts.append(target['host'])
            break
    return hosts
