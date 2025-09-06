import os
import sys
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from io import BytesIO
from qiniu import Auth, put_file, BucketManager
import time
import traceback

def validate_inputs():
    if len(sys.argv) < 3:
        raise ValueError("必须提供两个参数：Excel文件名和品牌名\n使用方式: python script.py 文件名.xlsx 品牌名 [颜色尺码标识]")
    
    excel_file = sys.argv[1]
    if not excel_file.lower().endswith(('.xlsx', '.xls')):
        raise ValueError("第一个参数必须是Excel文件（.xlsx或.xls）")
    
    if not os.path.exists(excel_file):
        raise ValueError(f"文件不存在: {excel_file}")
    
    brand_name = sys.argv[2]
    if not brand_name.strip():
        raise ValueError("品牌名不能为空")
        
    # 处理第三个可选参数
    color_size_flag = 0  # 默认值为0
    if len(sys.argv) >= 4:
        try:
            color_size_flag = int(sys.argv[3])
        except ValueError:
            raise ValueError("第三个参数（颜色尺码标识）必须是整数")
    
    return excel_file, brand_name, color_size_flag

def upload_to_qiniu(local_file_path, qiniu_file_name):
    # 七牛云配置（请替换为您的实际配置）
    access_key = 'cBWnI5kLc3PwbeMkhcTVEQIF9dDnoUzLuY-6cuG9'
    secret_key = 'hBo8wjRGkngB_xn2txneCYkD5FheUeok4MG_Frd3'
    bucket_name = 'pximages'
    
    # 构建鉴权对象
    q = Auth(access_key, secret_key)
    
    # 生成上传 Token
    token = q.upload_token(bucket_name, qiniu_file_name, 3600)
    
    # 上传文件
    ret, info = put_file(token, qiniu_file_name, local_file_path)
    
    if info.status_code == 200:
        # 返回公网URL
        base_url = 'https://qncdn.sytlz.com'  # 替换为您的七牛云域名
        return f"{base_url}/{qiniu_file_name}"
    else:
        raise Exception(f"七牛云上传失败: {info}")

def save_description_as_image(description, file_path):
    # 使用Selenium和ChromeDriver来渲染HTML并截图
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    process_result = 0
    
    try:
        # 创建一个简单的HTML页面来显示描述内容
        html = f"""
        <html>
            <head>
                <style>
                    table {{
                        border-collapse: collapse;
                        
                    }}
                    th, td {{
                        border: 1px solid #dddddd;
                        text-align: left;
                        padding: 8px;
                        width: auto;
                    }}
                    th {{
                        background-color: #f2f2f2;
                    }}
                </style>
            </head>
            <body>
                {description}
            </body>
        </html>
        """
        
        # 写入临时HTML文件
        temp_html = "temp.html"
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(html)
            
        # 打开HTML文件
        driver.get(f"file://{os.path.abspath(temp_html)}")
        
        # 等待页面加载
        time.sleep(1)
        try:
            # 找到所有的<table>元素
            tables = driver.find_elements(By.TAG_NAME, "table")
             
            # 打印找到的<table>元素数量
            # print(f"找到的<table>数量: {len(tables)}")
            
            table_count = 0
            
            # 遍历这些<table>元素：
            for table in tables:
            # 找到表格元素
                if table_count == 0 :
                    # 获取表格位置和大小
                    location = table.location
                    size = table.size
                    
                    left = location['x']
                    top = location['y']
                    right = location['x'] + size['width']
                    bottom = location['y'] + size['height']
                    # print(f"<table>的left-top-rightbottom: {left}-{top}-{right}-{bottom}")
                else:
                    size = table.size
                    
                    right = right + size['width']
                    # bottom = bottom + size['height']
                    # print(f"<table>的left-top-rightbottom: {left}-{top}-{right}-{bottom}")
            
                table_count += 1
                
            # 截图并裁剪
            png = driver.get_screenshot_as_png()
            driver.quit()
            
            im = Image.open(BytesIO(png))

            # 添加5像素的边距
            margin = 5
            
            # im = im.crop((left, top, right, bottom))
            im = im.crop((
                max(0, left - margin),
                max(0, top - margin),
                min(im.width, right + margin),
                min(im.height, bottom + margin)
            ))

            im.save(file_path, "JPEG")
            
            return process_result
        
        except Exception as e:
            print(f"description中没有尺码信息存在")
            
            process_result = 1
            return process_result
           
            
    except Exception as e:
        print(f"save_description_as_image函数出错: {file_path}")
        
        process_result = 1
        return process_result
    
    finally:
        driver.quit()
        if os.path.exists(temp_html):
            os.remove(temp_html)

def generate_output_filename(input_file):
    # 获取当前日期时间
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    # 处理输入文件名
    base_name = os.path.splitext(input_file)[0]
    extension = os.path.splitext(input_file)[1]
    
    return f"{base_name}_processed_{timestamp}{extension}"

def process_excel(excel_file, current_brand, color_size_flag):
    # 处理Excel文件主函数
    start_time = time.time()

    try:
        print(f"开始处理文件: {excel_file}")
        print(f"品牌名称: {current_brand}")
        
        # 读取Excel文件
        df = pd.read_excel(excel_file)
        
        # 检查是否已有sizeToImg列，如果没有则添加
        if 'sizeToImg' not in df.columns:
            df['sizeToImg'] = ''
        
        previous_code = ''
        image_url = ''
        processed_count = 0
        
        for index, row in df.iterrows():
            
            # 处理Code列
            if color_size_flag == 0:
                code_parts = str(row['Code']).split('-')
                current_code = code_parts[0] if code_parts else ''
            else:
                code_parts = str(row['Code'])
                current_code = code_parts

            if current_code != previous_code:
                # 处理Description列
                description = row['Description']
                if pd.notna(description) and description != '':
                    # 创建文件夹结构
                    os.makedirs(f"sizetoimg/{current_brand}", exist_ok=True)
                    
                    # 临时图片路径
                    temp_img_path = f"sizetoimg/{current_brand}/{current_code}.jpg"
                    
                    # 保存描述为图片
                    process_result = save_description_as_image(str(description), temp_img_path)
                    # print(f"该Code的process_result: {process_result}")
                    
                    try:
                        if process_result == 0:
                            # 上传到七牛云
                            qiniu_path = f"sizetoimg/{current_brand}/{current_code}.jpg"
                            image_url = upload_to_qiniu(temp_img_path, qiniu_path)
                            
                            # 删除临时图片
                            os.remove(temp_img_path)
                        else:
                            print(f"该Code的尺码信息有误，请确认: {current_code}")
                    
                    except Exception as e:
                        print(f"处理 {current_code} 时出错: {str(e)}")
                        
                        continue
                    
                    processed_count += 1
                    print(f"已处理: {current_code} ({processed_count})")
                
                # 更新previous_code
                previous_code = current_code
            
            # 更新sizeToImg列
            df.at[index, 'sizeToImg'] = image_url
        
        # 生成输出文件名
        output_path = generate_output_filename(excel_file)
        
        # 保存修改后的Excel文件
        df.to_excel(output_path, index=False)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"\n处理完成! 共处理 {processed_count} 个商品")
        print(f"结果已保存到: {output_path}")
        print(f"总耗时: {elapsed_time:.2f} 秒")
        
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"\n处理出错! 已运行 {elapsed_time:.2f} 秒")
    
        # 生成带日期和时间的日志文件名
        log_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        error_file_path = f"error_{log_time}.txt"
    
        # 写入错误文件
        with open(error_file_path, "w", encoding='utf-8') as f:
            f.write(f"错误发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"已运行时间: {elapsed_time:.2f} 秒\n\n")
            f.write(str(e))
            f.write("\n\n")
            f.write(traceback.format_exc())
            
        print(f"错误详情已写入 {error_file_path}")
        raise

if __name__ == "__main__":
    try:
        # 验证输入参数
        excel_file, brand_name, color_size_flag = validate_inputs()
        
        # 处理Excel文件
        process_excel(excel_file, brand_name, color_size_flag)
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)