"""尺码表转图片：渲染Description里的尺码表并上传七牛云

由原来的 sizetoimageallnew.py 和 02exist/sizetoimageuseexist.py 合并而来。
两者的差别只有"是否复用七牛上已有的图片"，其余逻辑（渲染、裁剪、上传、
CDN刷新、Excel读写）完全重复，改一处要改两遍还得测两回，所以合并。

用法:
    python sizetoimageallnew.py 文件名.xlsx 品牌名 [颜色尺码标识] [--skip-existing]

    颜色尺码标识  0(默认)=Code按'-'切分取前段  非0=Code整体作为货号
    --skip-existing  七牛上已有同名图片时直接复用，不重新生成
                     （原 02exist 的行为，默认关闭）
"""

import os
import sys
import time
import hashlib
import traceback
from io import BytesIO
from datetime import datetime

import pandas as pd
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from qiniu import Auth, put_file_v2, BucketManager, CdnManager


# ---------------------------------------------------------------- 配置

ACCESS_KEY = 'cBWnI5kLc3PwbeMkhcTVEQIF9dDnoUzLuY-6cuG9'
SECRET_KEY = 'hBo8wjRGkngB_xn2txneCYkD5FheUeok4MG_Frd3'
BUCKET_NAME = 'pximages'
BASE_URL = 'https://qncdn.sytlz.com'

# 渲染模式。多数品牌的Description里是<table>，直接渲染表格；
# 下面这些品牌是纯文本尺码信息，按<br>切分后渲染成列表。
MODE_TABLE = 'table'
MODE_LIST = 'list'

LIST_BRANDS = {
    'YONEX', 'SWANS', 'GREGORY', 'HELLYHANSEN', 'THENORTHFACE',
    'DESCENTE', 'ASICS', 'MIZUNO', 'OAKLEY', 'UNDERARMOUR',
}


def get_render_mode(brand_name):
    """按品牌决定用哪种渲染模式"""
    return MODE_LIST if brand_name.upper() in LIST_BRANDS else MODE_TABLE


# ---------------------------------------------------------------- 参数

def parse_args():
    argv = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}

    unknown = flags - {'--skip-existing'}
    if unknown:
        raise ValueError(f"无法识别的参数: {', '.join(sorted(unknown))}")

    if len(argv) < 2:
        raise ValueError(
            "必须提供两个参数：Excel文件名和品牌名\n"
            "使用方式: python sizetoimageallnew.py 文件名.xlsx 品牌名 [颜色尺码标识] [--skip-existing]"
        )

    excel_file = argv[0]
    if not excel_file.lower().endswith(('.xlsx', '.xls')):
        raise ValueError("第一个参数必须是Excel文件（.xlsx或.xls）")
    if not os.path.exists(excel_file):
        raise ValueError(f"文件不存在: {excel_file}")

    brand_name = argv[1]
    if not brand_name.strip():
        raise ValueError("品牌名不能为空")

    color_size_flag = 0
    if len(argv) >= 3:
        try:
            color_size_flag = int(argv[2])
        except ValueError:
            raise ValueError("第三个参数（颜色尺码标识）必须是整数")

    return excel_file, brand_name, color_size_flag, '--skip-existing' in flags


# ---------------------------------------------------------------- 渲染

def build_table_html(description):
    return f"""
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


def build_list_html(description):
    """纯文本尺码信息按<br>切分渲染成列表"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            ul { list-style-type: none; padding: 0; }
            li { margin: 2px 0; padding: 4px; background-color: #f5f5f5; border-radius: 2px; }
        </style>
    </head>
    <body>
    <ul>
    """

    if pd.notna(description):
        for item in str(description).split('<br>'):
            html += '<li>' + item.strip() + '</li>'

    return html + """
    </ul>
    </body>
    </html>
    """


def render_table_to_image(description, code, out_path):
    """渲染表格并按所有<table>的并集包围盒裁剪"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    driver = None
    temp_html = f"temp_{code}.html"

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options)

        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(build_table_html(description))

        driver.get(f"file://{os.path.abspath(temp_html)}")
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

            # 窗口尺寸变了，位置需要重新读取
            tables = driver.find_elements(By.TAG_NAME, "table")
            if not tables:
                raise Exception("页面中未找到table元素")

            # 计算所有<table>的并集包围盒（表格是块级元素，纵向堆叠，
            # 需要取所有表格的最小left/top和最大right/bottom）
            left = top = right = bottom = None
            for table in tables:
                location, size = table.location, table.size
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

            im = Image.open(BytesIO(driver.get_screenshot_as_png()))

            margin = 5
            im = im.crop((
                max(0, left - margin),
                max(0, top - margin),
                min(im.width, right + margin),
                min(im.height, bottom + margin)
            ))
            im.save(out_path, "JPEG")

            return 0

        except Exception:
            print("description中没有尺码信息存在")
            return 1

    except Exception:
        print(f"render_table_to_image函数出错: {code}")
        return 1

    finally:
        if driver:
            driver.quit()
        if os.path.exists(temp_html):
            os.remove(temp_html)


def render_list_to_image(description, code, out_path):
    """渲染纯文本尺码信息，整页截图（不裁剪）"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = None
    temp_html = f"temp_{code}.html"

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options)

        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(build_list_html(description))

        driver.get(f"file://{os.path.abspath(temp_html)}")
        time.sleep(2)

        driver.save_screenshot(out_path)
        return 0

    except Exception:
        print(f"render_list_to_image函数出错: {code}")
        return 1

    finally:
        if driver:
            driver.quit()
        if os.path.exists(temp_html):
            os.remove(temp_html)


def render_description(description, code, out_path, mode):
    """按渲染模式出图，返回0成功/1失败"""
    if mode == MODE_TABLE:
        return render_table_to_image(description, code, out_path)
    return render_list_to_image(description, code, out_path)


# ---------------------------------------------------------------- 七牛

def build_image_url(qiniu_path, content_hash):
    """图片URL挂上内容hash

    CDN刷新只能清边缘节点，终端用户浏览器里缓存的旧图不受影响；
    URL变了才是新资源，浏览器必然重新请求。
    用内容hash而不是时间戳：图没变时URL就不变，重跑脚本不会让
    整批商品的sizeToImg字段产生无意义的变更。
    """
    url = f"{BASE_URL}/{qiniu_path}"
    return f"{url}?v={content_hash[:12]}" if content_hash else url


def list_existing_images(brand_name):
    """列出七牛上该品牌已有的图片 {文件名: URL}"""
    prefix = f"sizetoimg/{brand_name}/"
    bucket = BucketManager(Auth(ACCESS_KEY, SECRET_KEY))
    marker = None
    url_dict = {}

    try:
        while True:
            ret, eof, info = bucket.list(
                BUCKET_NAME, prefix=prefix, marker=marker, limit=1000)

            for item in ret.get('items', []):
                if item['key'].endswith('.jpg'):
                    filename = os.path.basename(item['key'])
                    url_dict[filename] = build_image_url(item['key'], item.get('hash'))

            marker = ret.get('marker', None)
            if not marker:
                break

        print(f"获取到 {len(url_dict)} 个现有图片URL")
        return url_dict

    except Exception as e:
        print(f"获取现有图片失败，将继续处理: {e}")
        return {}


def upload_to_qiniu(local_file_path, qiniu_path):
    q = Auth(ACCESS_KEY, SECRET_KEY)
    token = q.upload_token(BUCKET_NAME, qiniu_path, 3600)
    ret, info = put_file_v2(token, qiniu_path, local_file_path)

    if info.status_code != 200:
        raise Exception(f"七牛云上传失败: {info}")

    # 用七牛返回的hash(etag)，和列出已有图片时的取值保持一致，
    # 否则同一个文件走不同路径会得到不同的URL
    content_hash = (ret or {}).get('hash')
    if not content_hash:
        with open(local_file_path, 'rb') as f:
            content_hash = hashlib.md5(f.read()).hexdigest()

    return build_image_url(qiniu_path, content_hash)


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

    cdn = CdnManager(Auth(ACCESS_KEY, SECRET_KEY))
    target_dir = f"{BASE_URL}/sizetoimg/{brand_name}/"

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


# ---------------------------------------------------------------- 主流程

def get_current_code(code_value, color_size_flag):
    code_str = str(code_value).strip()
    if color_size_flag == 0:
        parts = code_str.split('-')
        return parts[0] if parts else code_str
    return code_str


def generate_output_filename(input_file):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name, extension = os.path.splitext(input_file)
    return f"{base_name}_processed_{timestamp}{extension}"


def process_excel(excel_file, brand_name, color_size_flag, skip_existing):
    start_time = time.time()

    try:
        mode = get_render_mode(brand_name)
        print(f"开始处理文件: {excel_file}")
        print(f"品牌名称: {brand_name}  渲染模式: {mode}"
              f"{'  (复用已有图片)' if skip_existing else ''}")

        df = pd.read_excel(excel_file)
        if 'Code' not in df.columns or 'Description' not in df.columns:
            raise ValueError("Excel必须包含'Code'和'Description'列")
        if 'sizeToImg' not in df.columns:
            df['sizeToImg'] = ''

        existing_urls = list_existing_images(brand_name) if skip_existing else {}

        stats = {'existing_used': 0, 'new_created': 0, 'errors': 0}
        previous_code = ''
        current_url = ''
        uploaded_urls = []  # 本次上传的所有URL，跑完统一刷新CDN

        for index, row in df.iterrows():
            try:
                current_code = get_current_code(row['Code'], color_size_flag)
                if not current_code:
                    continue

                # 复用七牛上已有的图片
                if skip_existing and f"{current_code}.jpg" in existing_urls:
                    current_url = existing_urls[f"{current_code}.jpg"]
                    previous_code = current_code
                    stats['existing_used'] += 1
                    df.at[index, 'sizeToImg'] = current_url
                    continue

                if current_code != previous_code:
                    # 换货号了先清空。不清的话这个货号出图失败时，
                    # 该行会被写上"上一个货号"的图片URL——尺码表张冠李戴。
                    # 失败就留空，宁可缺图也不能挂错图。
                    current_url = ''

                    description = row['Description']
                    if pd.notna(description) and str(description).strip():
                        os.makedirs(f"sizetoimg/{brand_name}", exist_ok=True)
                        qiniu_path = f"sizetoimg/{brand_name}/{current_code}.jpg"
                        temp_img_path = qiniu_path

                        process_result = render_description(
                            str(description), current_code, temp_img_path, mode)

                        if process_result == 0:
                            current_url = upload_to_qiniu(temp_img_path, qiniu_path)
                            uploaded_urls.append(current_url)
                            os.remove(temp_img_path)

                            stats['new_created'] += 1
                            print(f"已处理: {current_code} ({stats['new_created']})")
                        else:
                            print(f"该Code的尺码信息有误，请确认: {current_code}")

                    previous_code = current_code

                df.at[index, 'sizeToImg'] = current_url

            except Exception as e:
                stats['errors'] += 1
                print(f"处理第 {index + 1} 行时出错: {e}")
                continue

        # 全部上传完成后，统一刷新一次CDN
        refresh_cdn(brand_name, uploaded_urls)

        output_path = generate_output_filename(excel_file)
        df.to_excel(output_path, index=False)

        elapsed = time.time() - start_time
        print("\n" + "=" * 50)
        print("处理完成! 统计信息:")
        print(f"总行数处理: {len(df)}")
        print(f"使用现有图片: {stats['existing_used']}")
        print(f"创建新图片: {stats['new_created']}")
        print(f"错误行数: {stats['errors']}")
        print(f"结果文件: {output_path}")
        print(f"总耗时: {elapsed:.2f} 秒")
        print("=" * 50)

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n处理出错! 已运行 {elapsed:.2f} 秒")

        error_file_path = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(error_file_path, "w", encoding='utf-8') as f:
            f.write(f"错误发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"已运行时间: {elapsed:.2f} 秒\n\n")
            f.write(str(e))
            f.write("\n\n")
            f.write(traceback.format_exc())

        print(f"错误详情已写入 {error_file_path}")
        raise


if __name__ == "__main__":
    try:
        excel_file, brand_name, color_size_flag, skip_existing = parse_args()
        process_excel(excel_file, brand_name, color_size_flag, skip_existing)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
