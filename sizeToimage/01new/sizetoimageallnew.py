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
from qiniu import Auth, put_file_v2, BucketManager, CdnManager
import time
import hashlib
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
    ret, info = put_file_v2(token, qiniu_file_name, local_file_path)
    
    if info.status_code == 200:
        # 返回公网URL
        base_url = 'https://qncdn.sytlz.com'  # 替换为您的七牛云域名
        url = f"{base_url}/{qiniu_file_name}"

        # 挂上文件内容hash。CDN刷新只能清边缘节点，终端用户浏览器里
        # 缓存的旧图不受影响；URL变了才是新资源，浏览器必然重新请求。
        # 用内容hash而不是时间戳：图没变时URL就不变，重跑脚本不会让
        # 整批商品的sizeToImg字段产生无意义的变更。
        # 统一用七牛返回的hash(etag)，和02exist复用已有图片时的取值保持一致，
        # 否则同一个文件在两个脚本里会得到不同的URL。
        content_hash = (ret or {}).get('hash')
        if not content_hash:
            with open(local_file_path, 'rb') as f:
                content_hash = hashlib.md5(f.read()).hexdigest()

        return f"{url}?v={content_hash[:12]}"
    else:
        raise Exception(f"七牛云上传失败: {info}")


def refresh_cdn(brand_name, uploaded_urls):
    """批量刷新CDN缓存

    文件名固定为 {code}.jpg，覆盖上传后URL不变，不刷新的话
    CDN边缘节点会一直返回旧图（商品页看到的还是上一版尺码表）。

    七牛刷新配额是按条计数的：URL刷新 500条/天，目录刷新 10条/天。
    所以整批跑完只刷一次目录，跟商品数量无关；目录刷新不可用时
    再退回按URL刷（每次最多60条）。
    """
    if not uploaded_urls:
        return

    access_key = 'cBWnI5kLc3PwbeMkhcTVEQIF9dDnoUzLuY-6cuG9'
    secret_key = 'hBo8wjRGkngB_xn2txneCYkD5FheUeok4MG_Frd3'
    base_url = 'https://qncdn.sytlz.com'

    cdn = CdnManager(Auth(access_key, secret_key))
    target_dir = f"{base_url}/sizetoimg/{brand_name}/"

    # 优先刷目录：一条配额搞定整批
    try:
        ret, info = cdn.refresh_dirs([target_dir])
        if info.status_code == 200 and ret and ret.get('code') == 200:
            print(f"CDN目录刷新成功: {target_dir} (今日剩余目录配额: {ret.get('dirSurplusDay')})")
            return
        print(f"CDN目录刷新未生效，改用URL刷新: {ret}")
    except Exception as e:
        print(f"CDN目录刷新失败，改用URL刷新: {e}")

    # 退路：按URL刷，每批最多60条（去掉?v=版本号，刷的是文件本身）
    plain_urls = [u.split('?')[0] for u in uploaded_urls]
    failed = 0
    for i in range(0, len(plain_urls), 60):
        batch = plain_urls[i:i + 60]
        try:
            ret, info = cdn.refresh_urls(batch)
            if info.status_code != 200 or not ret or ret.get('code') != 200:
                failed += len(batch)
                print(f"CDN刷新失败(不影响上传): {ret}")
        except Exception as e:
            failed += len(batch)
            print(f"CDN刷新失败(不影响上传): {e}")

    if failed:
        print(f"共 {failed}/{len(plain_urls)} 个URL未刷新成功，"
              f"可能已超今日配额，这些商品页可能仍显示旧图")
    else:
        print(f"CDN刷新完成: {len(plain_urls)} 个URL")


def save_description_uili_as_image(description, current_code, temp_img_path):
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
        <ul>
        """
        
        # 假设描述是以逗号分隔的尺寸信息
        if pd.notna(description):
            size_items = str(description).split('<br>')
            for item in size_items:
                html_content += '<li>' + f"{item.strip()}" + '</li>'
        
        html_content += """
        </ul>
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
                    /* inline-block容器宽度由最宽的表格决定，
                       配合 table{{width:100%}} 让所有表格自适应到相同宽度 */
                    .size-wrap {{
                        display: inline-block;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                    }}
                    /* 多个表格宽度一致且紧贴时会连成一张表，
                       加间距把它们在视觉上分开 */
                    table + table {{
                        margin-top: 24px;
                    }}
                    th, td {{
                        border: 1px solid #dddddd;
                        text-align: left;
                        padding: 8px;
                    }}
                    th {{
                        background-color: #f2f2f2;
                    }}
                </style>
            </head>
            <body>
                <div class="size-wrap">
                {description}
                </div>
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
            # 内容可能高于/宽于默认窗口(1920x1080)，截图只会截到视口大小，
            # 导致下方表格被截掉。先把窗口撑到内容实际尺寸再截图。
            content_width = driver.execute_script(
                "return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth);")
            content_height = driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
            driver.set_window_size(max(content_width + 100, 800), content_height + 100)
            time.sleep(0.5)

            # 找到所有的<table>元素（窗口尺寸变了，位置需要重新读取）
            tables = driver.find_elements(By.TAG_NAME, "table")
             
            # 打印找到的<table>元素数量
            # print(f"找到的<table>数量: {len(tables)}")
            
            if not tables:
                raise Exception("页面中未找到table元素")

            # 计算所有<table>的并集包围盒（表格是块级元素，纵向堆叠，
            # 需要取所有表格的最小left/top和最大right/bottom）
            left = top = None
            right = bottom = None
            for table in tables:
                location = table.location
                size = table.size

                t_left = location['x']
                t_top = location['y']
                t_right = location['x'] + size['width']
                t_bottom = location['y'] + size['height']

                if left is None:
                    left, top, right, bottom = t_left, t_top, t_right, t_bottom
                else:
                    left = min(left, t_left)
                    top = min(top, t_top)
                    right = max(right, t_right)
                    bottom = max(bottom, t_bottom)
                # print(f"<table>的left-top-rightbottom: {t_left}-{t_top}-{t_right}-{t_bottom}")
                
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
        uploaded_urls = []  # 本次上传的所有URL，跑完统一刷新CDN
        
        # 定义品牌列表并预先转换为大写
        brands = [
            "YONEX",
            "SWANS",
            "Gregory", 
            "HellyHansen",
            "TheNorthFace",
            "descente",
            "ASICS",
            "Mizuno",
            "OAKLEY",
            "UnderArmour"
        ]
        
        # 创建一个大写的品牌集合
        brands_upper = {brand.upper() for brand in brands}

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
                    
                    # 检查输入的大写版本是否在集合中
                    if current_brand.upper() in brands_upper:
                        # 保存描述为图片
                        process_result = save_description_uili_as_image(str(description), current_code, temp_img_path)
                        # print(f"该Code的process_result: {process_result}")
                    else:
                        # 保存描述为图片
                        process_result = save_description_as_image(str(description), temp_img_path)
                        # print(f"该Code的process_result: {process_result}")
                    
                    try:
                        if process_result == 0:
                            # 上传到七牛云
                            qiniu_path = f"sizetoimg/{current_brand}/{current_code}.jpg"
                            image_url = upload_to_qiniu(temp_img_path, qiniu_path)
                            uploaded_urls.append(image_url)

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
        
        # 全部上传完成后，统一刷新一次CDN
        refresh_cdn(current_brand, uploaded_urls)

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