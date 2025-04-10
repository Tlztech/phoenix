from datetime import datetime
import pytz


def get_timestamp(timezone="Asia/Tokyo"):
    # 创建一个UTC时间
    utc_now = datetime.utcnow()

    # 定义日本时区
    jst_timezone = pytz.timezone('Asia/Tokyo')

    # 将UTC时间转换为日本时区时间
    jst_now = utc_now.replace(tzinfo=pytz.utc).astimezone(jst_timezone)

    # 获取时间戳
    timestamp = int(jst_now.timestamp())

    return timestamp
