# -*- coding: utf-8 -*-
from qiniu import Auth
from qiniu import BucketManager

access_key = 'cBWnI5kLc3PwbeMkhcTVEQIF9dDnoUzLuY-6cuG9'
secret_key = 'hBo8wjRGkngB_xn2txneCYkD5FheUeok4MG_Frd3'

q = Auth(access_key, secret_key)
bucket = BucketManager(q)

bucket_name = 'pximages'
# 前缀
prefix = 'sizetoimg/lululemon/'
# 列举条目
limit = 1000
# 列举出除'/'的所有文件以及以'/'为分隔的所有前缀
delimiter = None
# 标记
marker = None

total_fize = 0

ret, eof, info = bucket.list(bucket_name, prefix, marker, limit, delimiter)
for i in ret['items']:
    print(i['fsize'])
    print('文件名:', i['key'])  # 注意这里的key是完整的文件路径，包括前缀
    total_fize += i['fsize']

print(total_fize)
