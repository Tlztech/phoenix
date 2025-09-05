from datetime import datetime
import os
import requests
from qiniu import Auth, put_file, BucketManager
import time
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# 七牛云配置 - 请替换为您的实际信息
QINIU_ACCESS_KEY = 'cBWnI5kLc3PwbeMkhcTVEQIF9dDnoUzLuY-6cuG9'
QINIU_SECRET_KEY = 'hBo8wjRGkngB_xn2txneCYkD5FheUeok4MG_Frd3'
QINIU_BUCKET_NAME = 'pximages'
QINIU_DOMAIN = 'https://qncdn.sytlz.com'  # 例如：'http://xxx.clouddn.com'

# 初始化七牛云Auth和BucketManager
q = Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)
bucket = BucketManager(q)

# 统计结果
result_stats = {
    'total': 0,
    'success': 0,
    'fail': 0,
    'fail_reasons': []
}

def create_qiniu_folder(folder_path):
    """在七牛云上创建文件夹（实际上是上传一个空文件）"""
    try:
        # 七牛云没有真正的文件夹概念，我们通过上传一个空文件来模拟文件夹
        key = f"{folder_path}/.keep"
        token = q.upload_token(QINIU_BUCKET_NAME, key, 3600)
        ret, info = put_file(token, key, os.devnull)
        return ret is not None
    except Exception as e:
        result_stats['fail_reasons'].append(f"创建文件夹失败 {folder_path}: {str(e)}")
        return False

def download_image(url, save_path):
    """下载图片到本地临时文件"""
    try:
        # 发送HTTP请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        else:
            result_stats['fail_reasons'].append(f"下载图片失败 {url}: HTTP状态码 {response.status_code}")
            return False
    except Exception as e:
        result_stats['fail_reasons'].append(f"下载图片失败 {url}: {str(e)}")
        return False

def upload_to_qiniu(local_path, remote_path):
    """上传文件到七牛云"""
    try:
        token = q.upload_token(QINIU_BUCKET_NAME, remote_path, 3600)
        ret, info = put_file(token, remote_path, local_path)
        if ret is not None:
            return f"{QINIU_DOMAIN}/{remote_path}"
        else:
            result_stats['fail_reasons'].append(f"上传失败 {remote_path}: {info}")
            return None
    except Exception as e:
        result_stats['fail_reasons'].append(f"上传失败 {remote_path}: {str(e)}")
        return None

def sanitize_filename(name):
    """清理文件名中的特殊字符"""
    # 替换Windows文件名中不允许的字符
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()

def process_line(line, output_file):
    """处理每一行数据"""
    global result_stats
    result_stats['total'] += 1
    
    try:
        parts = line.strip().split('\t')
        if len(parts) < 3:
            result_stats['fail'] += 1
            result_stats['fail_reasons'].append(f"行格式错误: {line}")
            return
        
        brand, model, pic_urls = parts[0], parts[1], parts[2]
        pic_url_list = [url.strip() for url in pic_urls.split(';') if url.strip()]
        
        if not pic_url_list:
            result_stats['fail'] += 1
            result_stats['fail_reasons'].append(f"无有效图片URL: {brand}/{model}")
            output_file.write(line.strip() + '\t\n')
            return
        
        # 清理品牌和模型名称中的特殊字符
        brand_folder = sanitize_filename(brand)
        model_folder = sanitize_filename(model)
        folder_path = f"{brand_folder}/{model_folder}"
        
        # 在七牛云上创建品牌文件夹和模型子文件夹
        if not create_qiniu_folder(brand_folder):
            result_stats['fail'] += 1
            result_stats['fail_reasons'].append(f"无法创建品牌文件夹: {brand_folder}")
            return
        
        if not create_qiniu_folder(folder_path):
            result_stats['fail'] += 1
            result_stats['fail_reasons'].append(f"无法创建模型文件夹: {folder_path}")
            return
        
        # 处理每个图片URL
        uploaded_urls = []
        for i, url in enumerate(pic_url_list):
            try:
                # 下载图片到临时文件
                temp_file = f"temp_{int(time.time() * 1000)}_{i}.jpg"
                if not download_image(url, temp_file):
                    continue
                
                # 上传到七牛云
                file_name = os.path.basename(url).split('?')[0]  # 去除URL参数
                if not file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    file_name = f"image_{i}.jpg"
                
                file_name = sanitize_filename(file_name)
                remote_path = f"{folder_path}/{file_name}"
                public_url = upload_to_qiniu(temp_file, remote_path)
                
                if public_url:
                    uploaded_urls.append(public_url)
                
                # 删除临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
            except Exception as e:
                result_stats['fail_reasons'].append(f"处理图片失败 {url}: {str(e)}")
                continue
        
        # 写入输出文件
        output_line = '\t'.join(parts[:3])
        if uploaded_urls:
            output_line += '\t' + ';'.join(uploaded_urls)
            result_stats['success'] += 1
        else:
            output_line += '\t'
            result_stats['fail'] += 1
            result_stats['fail_reasons'].append(f"所有图片处理失败: {brand}/{model}")
        
        output_file.write(output_line + '\n')
        
    except Exception as e:
        result_stats['fail'] += 1
        result_stats['fail_reasons'].append(f"处理行失败: {line}. 错误: {str(e)}")

def main():
    """主函数"""
    start_time = time.time()
    
    # 生成带日期和时间的日志文件名
    log_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # 输入输出文件路径
    input_file_path = 'input.txt'
    output_file_path = f"output_{log_time}.txt"
    result_file_path = f"result_{log_time}.txt"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file_path):
        print(f"错误: 输入文件 {input_file_path} 不存在")
        with open(result_file_path, 'w', encoding='utf-8') as resfile:
            resfile.write(f"错误: 输入文件 {input_file_path} 不存在\n")
        return
    
    # 准备输出文件
    with open(input_file_path, 'r', encoding='utf-8') as infile, \
         open(output_file_path, 'w', encoding='utf-8') as outfile:
        
        # 写入输出文件标题行（如果输入文件有标题行）
        first_line = infile.readline()
        if not first_line.strip().startswith('brand\t'):
            # 如果没有标题行，回退到文件开头
            infile.seek(0)
        else:
            outfile.write(first_line.strip() + '\tqiniu_urls\n')
        
        # 处理每一行
        lines = infile.readlines()
        with ThreadPoolExecutor(max_workers=5) as executor:
            list(tqdm(executor.map(lambda line: process_line(line, outfile), lines), total=len(lines)))
    
    # 写入结果统计
    with open(result_file_path, 'w', encoding='utf-8') as resfile:
        resfile.write(f"处理完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        resfile.write(f"总处理记录数: {result_stats['total']}\n")
        resfile.write(f"成功记录数: {result_stats['success']}\n")
        resfile.write(f"失败记录数: {result_stats['fail']}\n")
        resfile.write(f"总耗时: {time.time() - start_time:.2f}秒\n\n")
        
        if result_stats['fail_reasons']:
            resfile.write("失败原因详情:\n")
            for reason in set(result_stats['fail_reasons']):  # 去重
                count = result_stats['fail_reasons'].count(reason)
                resfile.write(f"- {reason} (出现次数: {count})\n")
    
    print(f"处理完成。结果已写入 {output_file_path} 和 {result_file_path}")

if __name__ == '__main__':
    print("开始处理input.txt文件...")
    main()