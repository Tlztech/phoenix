import os
import sys
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from io import BytesIO
from qiniu import Auth, BucketManager, put_file
import time
import traceback
from datetime import datetime
from urllib.parse import urlparse

class QiniuImageProcessor:
    def __init__(self):
        self.start_time = time.time()
        self.excel_file, self.brand_name, self.color_size_flag = self.validate_inputs()
        self.bucket, self.auth, self.bucket_name, self.domain = self.init_qiniu()
        self.existing_urls = self.get_existing_images()
        self.process_excel()

    def print_time_used(self, message):
        """打印已用时间"""
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:.2f}s] {message}")

    def validate_inputs(self):
        """验证输入参数是否正确"""
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
            
        self.print_time_used("参数验证完成")
        return excel_file, brand_name, color_size_flag

    def init_qiniu(self):
        """初始化七牛云配置"""
        # 配置需要替换为您的实际信息
        config = {
            'access_key': 'cBWnI5kLc3PwbeMkhcTVEQIF9dDnoUzLuY-6cuG9',
            'secret_key': 'hBo8wjRGkngB_xn2txneCYkD5FheUeok4MG_Frd3',
            'bucket_name': 'pximages',
            'domain': 'https://qncdn.sytlz.com'
        }
        
        auth = Auth(config['access_key'], config['secret_key'])
        bucket = BucketManager(auth)
        
        self.print_time_used("七牛云初始化完成")
        return bucket, auth, config['bucket_name'], config['domain']

    def get_existing_images(self):
        """获取七牛云上已存在的图片URL字典（文件名:URL）"""
        prefix = f"sizetoimg/{self.brand_name}/"
        marker = None
        limit = 1000
        url_dict = {}
        
        try:
            while True:
                ret, eof, info = self.bucket.list(self.bucket_name, prefix=prefix, marker=marker, limit=limit)

                for item in ret.get('items', []):
                    if item['key'].endswith('.jpg'):
                        filename = os.path.basename(item['key'])
                        url = f"{self.domain}/{item['key']}"
                        url_dict[filename] = url
                        # print(f"文件名: {item['key']}    URL: {url}")  # 注意这里的key是完整的文件路径，包括前缀
                
                marker = ret.get('marker', None)
                if not marker:
                    break
            
            self.print_time_used(f"获取到 {len(url_dict)} 个现有图片URL")
            return url_dict
            
        except Exception as e:
            self.print_time_used(f"获取现有图片失败，将继续处理: {str(e)}")
            return {}

    def get_current_code(self, code_value):
        """根据颜色尺码标识获取currentCode"""
        code_str = str(code_value).strip()
        if self.color_size_flag == 0:
            # 分割取第一个字符串
            parts = code_str.split('-')
            return parts[0] if parts else code_str
        else:
            # 不分割，使用原始值
            return code_str

    def render_table_to_image(self, description, code, temp_img_path):
        """将描述内容渲染为表格并保存为图片"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        driver = None
        process_result = 0
        
        try:
            # 初始化浏览器驱动
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            
            # 构建HTML内容
            html = f"""
            <html>
                <head>
                    <style>
                        table {{
                            border-collapse: collapse;
                            font-family: Arial, sans-serif;
                        }}
                        th, td {{
                            border: 1px solid #dddddd;
                            text-align: left;
                            padding: 8px;
                            width: auto;
                        }}
                        th {{
                            background-color: #f2f2f2;
                            font-weight: bold;
                        }}
                        tr:nth-child(even) {{
                            background-color: #f9f9f9;
                        }}
                    </style>
                </head>
                <body>
                    {description}
                </body>
            </html>
            """
          
            # 写入临时HTML文件
            temp_html = f"temp_{code}.html"
            with open(temp_html, "w", encoding="utf-8") as f:
                f.write(html)
                
            # 渲染页面
            driver.get(f"file://{os.path.abspath(temp_html)}")
            time.sleep(1)  # 等待页面加载
            
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
                
                # 保存临时图片
                # temp_img_path = f"temp_{code}.jpg"
                im.save(temp_img_path, "JPEG", quality=85)
                
                return process_result
            
            except Exception as e:
                print(f"description中没有尺码信息存在")
                process_result = 1
                return process_result
    
        except Exception as e:
            print(f"render_table_to_image函数出错: {code}")
            process_result = 1
            return process_result
        
        finally:
            if driver:
                driver.quit()
            if os.path.exists(temp_html):
                os.remove(temp_html)

    
    def save_description_uili_as_image(self, description, current_code, temp_img_path):
        """从描述中截取尺寸图表"""
        # 设置Chrome浏览器选项
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # 启动浏览器
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        # driver = webdriver.Chrome(options=chrome_options)
        
        process_result = 0
            
        try:
        
            # 创建HTML内容
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    ul {{ list-style-type: none; padding: 0; }}
                    li {{ margin: 2px 0; padding: 4px; background-color: #f5f5f5; border-radius: 2px; }}
                </style>
            </head>
            <body>
            """
            
            # 假设描述是以逗号分隔的尺寸信息
            if pd.notna(description):
                size_items = str(description).split(',')
                for item in size_items:
                    html_content += f"{item.strip()}"
            
            html_content += """
            </body>
            </html>
            """
            
            # 保存HTML到临时文件并打开
            temp_html = f"temp_{current_code}.html"
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            driver.get(f"file://{os.path.abspath(temp_html)}")
            
            # 等待页面加载
            time.sleep(2)
            
            try:
                # 获取body元素的高度
                #body = driver.find_element(By.TAG_NAME, 'body')
                #body_height = body.size['height']
                
                # 设置窗口大小以适应内容（避免滚动条）
                #driver.set_window_size(800, body_height + 100)
                
                # 截取整个页面
                #screenshot_path = f"{current_code}.jpg"
                driver.save_screenshot(temp_img_path)
                
                return process_result
            
            except Exception as e:
                print(f"description中没有尺码信息存在")
                
                process_result = 1
                return process_result
               
                
        except Exception as e:
            print(f"save_description_uili_as_image函数出错: {current_code}")
            
            process_result = 1
            return process_result
        
        finally:
            driver.quit()
            if os.path.exists(temp_html):
                os.remove(temp_html)
    
    
    def upload_image_to_qiniu(self, local_path, code):
        """上传图片到七牛云"""
        qiniu_path = f"sizetoimg/{self.brand_name}/{code}.jpg"
        # auth = Auth(self.bucket.auth.access_key, self.bucket.auth.secret_key)
        token = self.auth.upload_token(self.bucket_name, qiniu_path, 3600)
        
        ret, info = put_file(token, qiniu_path, local_path)
        
        if info.status_code == 200:
            url = f"{self.domain}/{qiniu_path}"
            self.existing_urls[f"{code}.jpg"] = url  # 更新本地缓存
            return url
        else:
            raise Exception(f"上传失败: {info}")

    def process_excel(self):
        """处理Excel文件主逻辑"""
        temp_files = []
        try:
            # 读取Excel文件
            self.print_time_used(f"开始读取Excel文件: {self.excel_file}")
            df = pd.read_excel(self.excel_file)
            
            # 验证必要列
            if 'Code' not in df.columns or 'Description' not in df.columns:
                raise ValueError("Excel必须包含'Code'和'Description'列")
            
            # 初始化结果列
            if 'sizeToImg' not in df.columns:
                df['sizeToImg'] = ''
            
            # 处理统计
            stats = {
                'total': len(df),
                'existing_used': 0,
                'new_created': 0,
                'errors': 0
            }
            
            previous_code = ''
            last_created_url = ''
            
            for index, row in df.iterrows():
                try:
                    # 处理Code列
                    code = str(row['Code']).strip()
                    if not code:
                        continue
                        
                    # 根据颜色尺码标识处理Code
                    current_code = self.get_current_code(code)
                    search_key = f"{current_code}.jpg"
                    
                    # 检查现有图片
                    if search_key in self.existing_urls:
                        df.at[index, 'sizeToImg'] = self.existing_urls[search_key]
                        stats['existing_used'] += 1
                        if stats['existing_used'] % 50 == 0:
                            self.print_time_used(f"已使用 {stats['existing_used']} 个现有图片")
                        continue
                    
                    # 没有现有图片的情况
                    if current_code != previous_code:
                        description = row['Description']
                        if pd.notna(description) and str(description).strip():
                            try:
                            
                                # 创建文件夹结构
                                os.makedirs(f"sizetoimg/{self.brand_name}", exist_ok=True)
                                
                                # 临时图片路径
                                temp_img_path = f"sizetoimg/{self.brand_name}/{current_code}.jpg"
                    
                                if self.brand_name.upper() == "LACOSTE":
                                    # 保存描述为图片
                                    process_result = self.save_description_uili_as_image(str(description), current_code, temp_img_path)
                                    # print(f"该Code的process_result: {process_result}")
                                else:
                                    # 生成图片
                                    process_result = self.render_table_to_image(str(description), current_code, temp_img_path)
                                    # print(f"该Code的process_result: {process_result}")

                                
                                if process_result == 0:
                                    temp_files.append(temp_img_path)
                                    
                                    # 上传到七牛云
                                    image_url = self.upload_image_to_qiniu(temp_img_path, current_code)
                                    last_created_url = image_url
                                    stats['new_created'] += 1
                                    print(f"已处理: {current_code} ({stats['new_created']})")
                                    
                                    if stats['new_created'] % 10 == 0:
                                        self.print_time_used(f"已创建 {stats['new_created']} 个新图片")
                                else:
                                    print(f"该Code的尺码信息有误，请确认: {current_code}")
                                    
                            except Exception as e:
                                stats['errors'] += 1
                                print(f"处理 {current_code} 时出错: {str(e)}")
                                continue
                            
                        previous_code = current_code
                    
                    # 更新当前行的图片URL
                    df.at[index, 'sizeToImg'] = last_created_url
                    
                except Exception as e:
                    stats['errors'] += 1
                    print(f"处理第 {index+1} 行时出错: {str(e)}")
                    continue
            
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(self.excel_file)[0]
            extension = os.path.splitext(self.excel_file)[1]
            output_path = f"{base_name}_processed_{timestamp}{extension}"
            
            # 保存结果
            df.to_excel(output_path, index=False)
            
            # 打印统计信息
            elapsed = time.time() - self.start_time
            print("\n" + "="*50)
            print("处理完成! 统计信息:")
            print(f"总行数处理: {stats['total']}")
            print(f"使用现有图片: {stats['existing_used']}")
            print(f"创建新图片: {stats['new_created']}")
            print(f"错误行数: {stats['errors']}")
            print(f"结果文件: {output_path}")
            print(f"总耗时: {elapsed:.2f} 秒")
            print("="*50)
            
        except Exception as e:
            self.handle_error(e)
        finally:
            # 清理临时文件
            for file in temp_files:
                if os.path.exists(file):
                    os.remove(file)

    def handle_error(self, error):
        """错误处理"""
        elapsed = time.time() - self.start_time
        error_msg = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        error_msg += f"已运行时间: {elapsed:.2f} 秒\n\n"
        error_msg += str(error) + "\n\n"
        error_msg += traceback.format_exc()
        
        with open("error.txt", "w", encoding='utf-8') as f:
            f.write(error_msg)
        
        print("\n" + "!"*50)
        print(f"处理出错! 已运行 {elapsed:.2f} 秒")
        print(f"错误详情已写入 error.txt")
        print("!"*50)
        sys.exit(1)

if __name__ == "__main__":
    processor = QiniuImageProcessor()