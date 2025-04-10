from dotenv import load_dotenv
import os

# 加载.env文件
load_dotenv()

def get_env(key):
    return os.getenv(key)