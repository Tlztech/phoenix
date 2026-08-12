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
import re
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
from qiniu import Auth, BucketManager, CdnManager
try:
    # 七牛SDK 7.11+ 才有 put_file_v2，旧版本退回 put_file
    from qiniu import put_file_v2 as qiniu_put_file
except ImportError:
    from qiniu import put_file as qiniu_put_file


# ---------------------------------------------------------------- 配置

ACCESS_KEY = 'cBWnI5kLc3PwbeMkhcTVEQIF9dDnoUzLuY-6cuG9'
SECRET_KEY = 'hBo8wjRGkngB_xn2txneCYkD5FheUeok4MG_Frd3'
BUCKET_NAME = 'pximages'
BASE_URL = 'https://qncdn.sytlz.com'

# 渲染模式，按品牌区分Description的内容形态：
#   table  里面是<table>，渲染后按表格包围盒裁剪(多数品牌)
#   list   纯文本尺码信息，按<br>切分后逐条包<li>
#   raw    本身已经是完整的列表HTML(<ul><li>...)，原样输出即可
#   styled Description自带<style>，样式和内容都以它为准，按内容整体裁剪
MODE_TABLE = 'table'
MODE_LIST = 'list'
MODE_RAW = 'raw'
MODE_STYLED = 'styled'

# 静态尺码图主要在手机端展示。400px 接近常见手机内容区宽度，
# 既能避免桌面宽图在手机上被过度缩小，也给浏览器窗口留出少量外边距。
MOBILE_CONTENT_WIDTH = 400
MOBILE_VIEWPORT_WIDTH = MOBILE_CONTENT_WIDTH + 40
MOBILE_INITIAL_HEIGHT = 1080

LIST_BRANDS = {
    'YONEX', 'SWANS', 'GREGORY', 'HELLYHANSEN', 'THENORTHFACE',
    'DESCENTE', 'ASICS', 'MIZUNO', 'OAKLEY', 'UNDERARMOUR',
}

# LACOSTE的Description是现成的<ul><li><span>..</span><p>..</p></li></ul>，
# 既没有<table>也没有<br>：走表格模式会全军覆没，走list模式会被
# 再包一层<li>导致嵌套变形，只能原样输出。
RAW_BRANDS = {'LACOSTE'}

# MONTBELL的Description是一整段带<style>的HTML：标题、表格、单位、脚注齐全，
# 样式也自己写好了。走table模式有两处会坏：脚本自带的CSS会跟它的样式打架；
# 按<table>裁剪会把表格外面的标题/单位/脚注全裁掉。所以原样渲染、整体裁剪。
STYLED_BRANDS = {'MONTBELL'}

# 部分品牌的普通表格需要在最上方补一行品牌指定的标题。
# 标题只作用于对应品牌，避免改变其他品牌现有的出图样式。
TABLE_TITLES = {
    'UNIQLO': '商品尺寸(cm)',
    '优衣库': '商品尺寸(cm)',
    '昂跑': '人体净尺寸参考表(cm)',
    'ON': '人体净尺寸参考表(cm)',
    'ON RUNNING': '人体净尺寸参考表(cm)',
    'PATAGONIA': '商品尺寸表(cm)',
    '巴塔哥尼亚': '商品尺寸表(cm)',
}


def get_render_mode(brand_name):
    """按品牌决定用哪种渲染模式（品牌名不区分大小写）"""
    brand = brand_name.upper()
    if brand in LIST_BRANDS:
        return MODE_LIST
    if brand in RAW_BRANDS:
        return MODE_RAW
    if brand in STYLED_BRANDS:
        return MODE_STYLED
    return MODE_TABLE


def get_table_title(brand_name):
    """返回品牌专属的表格标题；没有配置时不添加标题。"""
    return TABLE_TITLES.get(brand_name.strip().upper())


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

# 尺码区间值里的各种全角/长破折号（如昂跑的"91 — 96"），统一成半角"91-96"。
# 前后空格一并去掉，配合.range的nowrap样式保证区间值不折行。
# 可选的短字母前缀(如美码"W 8 — 10.5"的W/M)一并包进span，否则会在
# 前缀后的空格处折行。ー(片假名长音)只在两侧都是数字时才会被当作
# 破折号，不影响正常日文。
_RANGE_DASH_RE = re.compile(
    r'(?:\b([A-Za-z]{1,3})\s+)?(\d+(?:\.\d+)?)\s*[—–―−ー]\s*(\d+(?:\.\d+)?)')
_TAG_SPLIT_RE = re.compile(r'(<[^>]+>)')


def _range_repl(m):
    prefix = f'{m.group(1)} ' if m.group(1) else ''
    return f'<span class="range">{prefix}{m.group(2)}-{m.group(3)}</span>'


def normalize_range_dashes(html):
    """把"[前缀 ]数字 — 数字"规整为"[前缀 ]数字-数字"并包上防折行的span

    只处理标签外的文本，避免改坏属性值里的内容(URL、颜色值等)。
    """
    parts = _TAG_SPLIT_RE.split(str(html))
    for i, part in enumerate(parts):
        if not part.startswith('<'):
            parts[i] = _RANGE_DASH_RE.sub(_range_repl, part)
    return ''.join(parts)


def build_table_html(description, table_title=None):
    description = normalize_range_dashes(description)
    title_html = (
        f'<div class="size-title">{table_title}</div>'
        if table_title else ''
    )
    # 含区间值(91-96)的表格改用自动布局：固定等宽下宽区间值会溢出压到
    # 边框线；自动布局按内容分配列宽。同时把"可在任意字符间折行"收紧为
    # 正常折行规则，否则窄列里"90"会被竖排成"9/0"。没有区间值的品牌不受影响。
    range_css = (
        '.size-wrap table { table-layout: auto !important; }'
        '.size-wrap th, .size-wrap td {'
        ' overflow-wrap: normal !important;'
        ' word-break: normal !important; }'
        if 'class="range"' in description else ''
    )
    return f"""
    <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    background: #ffffff;
                }}
                body {{
                    width: {MOBILE_CONTENT_WIDTH}px;
                    padding: 8px;
                    color: #222222;
                    font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
                    font-size: 14px;
                }}
                .size-wrap {{
                    display: block;
                    box-sizing: border-box;
                    width: 100%;
                }}
                .size-wrap, .size-wrap * {{
                    box-sizing: border-box;
                    font-family: "PingFang SC", "Microsoft YaHei", sans-serif !important;
                }}
                .size-title {{
                    width: 100%;
                    border: 1px solid #dddddd;
                    border-bottom: 0;
                    background-color: #f2f2f2;
                    color: #222222;
                    font-weight: 600;
                    font-size: 14px;
                    text-align: center;
                    line-height: 1.2;
                    padding: 4px 5px;
                }}
                .size-wrap table {{
                    border-collapse: collapse;
                    table-layout: fixed !important;
                    width: 100% !important;
                    max-width: 100% !important;
                }}
                /* 多个表格宽度一致且紧贴时会连成一张表，
                   加间距把它们在视觉上分开 */
                table + table {{
                    margin-top: 12px;
                }}
                .size-wrap th, .size-wrap td {{
                    border: 1px solid #dddddd;
                    text-align: left;
                    vertical-align: middle;
                    white-space: normal !important;
                    overflow-wrap: anywhere;
                    word-break: break-word;
                    font-size: 14px !important;
                    line-height: 1.2 !important;
                    padding: 4px 5px !important;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                /* 尺码区间值(如91-96)保持一行，不跟随单元格的强制折行 */
                .range {{
                    white-space: nowrap !important;
                    overflow-wrap: normal !important;
                    word-break: keep-all !important;
                }}
                {range_css}
            </style>
        </head>
        <body>
            <div class="size-wrap">
            {title_html}
            {description}
            </div>
        </body>
    </html>
    """


def build_list_html(description, mode):
    """渲染尺码列表

    MODE_LIST 按<br>切分，逐条包<li>；
    MODE_RAW  Description本身就是完整的列表HTML，原样放进body。
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            html, body {{ margin: 0; padding: 0; background: #ffffff; }}
            body {{
                width: {MOBILE_CONTENT_WIDTH}px;
                padding: 8px;
                color: #222222;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }}
            .mobile-content, .mobile-content * {{
                box-sizing: border-box;
                max-width: 100%;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif !important;
                overflow-wrap: anywhere;
            }}
            .mobile-content {{ width: 100%; }}
            ul {{ list-style-type: none; margin: 0; padding: 0; }}
            li {{
                margin: 2px 0;
                padding: 3px 5px;
                font-size: 14px !important;
                line-height: 1.25;
                background-color: #f5f5f5;
                border-radius: 2px;
            }}
            .mobile-content li *, .mobile-content p {{
                font-size: 14px !important;
                line-height: 1.25;
            }}
            .mobile-content p {{ margin: 2px 0; }}
            table {{ width: 100% !important; table-layout: fixed !important; }}
            th, td {{
                white-space: normal !important;
                word-break: break-word;
                line-height: 1.2 !important;
                padding: 4px 5px !important;
            }}
            img {{ max-width: 100% !important; height: auto !important; }}
        </style>
    </head>
    <body><div class="mobile-content">
    """

    if mode == MODE_RAW:
        html += str(description) if pd.notna(description) else ''
    else:
        html += '<ul>'
        if pd.notna(description):
            for item in str(description).split('<br>'):
                html += '<li>' + item.strip() + '</li>'
        html += '</ul>'

    return html + """
    </div>
    </body>
    </html>
    """


def build_styled_html(description):
    """保留Description的品牌样式，并追加移动端尺寸约束

    品牌自带的颜色、边框等继续生效；统一字体、紧凑行高、宽度和换行规则，
    避免桌面宽表格在手机页面上整体缩得过小。
    """
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        html {{
            margin: 0;
            padding: 0;
            background: #ffffff;
        }}
        body {{
            margin: 0;
            width: {MOBILE_CONTENT_WIDTH}px;
            padding: 8px;
            background: #ffffff;
            color: #222222;
            font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
            font-size: 14px;
        }}
    </style>
</head>
<body class="mobile-canvas">
{description if pd.notna(description) else ''}
<style>
    html body.mobile-canvas {{
        box-sizing: content-box;
        font-family: "PingFang SC", "Microsoft YaHei", sans-serif !important;
        overflow-wrap: anywhere;
    }}
    html body.mobile-canvas * {{
        box-sizing: border-box;
        font-family: "PingFang SC", "Microsoft YaHei", sans-serif !important;
        overflow-wrap: anywhere;
    }}
    html body.mobile-canvas > *,
    html body.mobile-canvas div,
    html body.mobile-canvas section,
    html body.mobile-canvas article,
    html body.mobile-canvas p,
    html body.mobile-canvas ul,
    html body.mobile-canvas ol {{
        max-width: 100% !important;
    }}
    html body.mobile-canvas table {{
        width: 100% !important;
        max-width: 100% !important;
        table-layout: fixed !important;
    }}
    html body.mobile-canvas th,
    html body.mobile-canvas td,
    html body.mobile-canvas th *,
    html body.mobile-canvas td * {{
        white-space: normal !important;
        word-break: break-word;
        font-size: 14px !important;
        line-height: 1.2 !important;
        padding: 4px 5px !important;
    }}
    html body.mobile-canvas img {{
        max-width: 100% !important;
        height: auto !important;
    }}
</style>
</body>
</html>
"""


class NoSizeTableError(Exception):
    """Description里没有可渲染的尺码表——数据问题，重试没有意义"""


# 整批复用一个浏览器实例。原来每张图都新建一次driver(还要调一次
# ChromeDriverManager().install())，启动开销占了单张耗时的绝大部分。
_driver = None


def get_driver(mode):
    """取得浏览器实例，没有就新建"""
    global _driver
    if _driver is not None:
        return _driver

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    if mode in (MODE_TABLE, MODE_STYLED):
        options.add_argument('--disable-gpu')
        options.add_argument(
            f'--window-size={MOBILE_VIEWPORT_WIDTH},{MOBILE_INITIAL_HEIGHT}')
    else:
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

    _driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options)
    return _driver


def drop_driver():
    """丢弃当前实例，下次renders会重新拉起。浏览器崩溃后重试前调用"""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None


def render_table_to_image(description, code, out_path, table_title=None):
    """渲染表格并按所有<table>的并集包围盒裁剪

    成功返回None；Description里没有table时抛NoSizeTableError；
    其余异常(浏览器崩溃、超时等)原样抛出，交给上层重试。
    """
    temp_html = f"temp_{code}.html"

    try:
        driver = get_driver(MODE_TABLE)

        # 固定为手机内容宽度，避免桌面宽图在手机端被整体缩小。
        driver.set_window_size(MOBILE_VIEWPORT_WIDTH, MOBILE_INITIAL_HEIGHT)

        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(build_table_html(description, table_title))

        driver.get(f"file://{os.path.abspath(temp_html)}")
        time.sleep(1)

        # 宽度保持不变，只把窗口高度撑到完整内容，防止长表格被截断。
        content_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
        driver.set_window_size(
            MOBILE_VIEWPORT_WIDTH,
            max(int(content_height) + 40, 200)
        )
        time.sleep(0.5)

        # 窗口尺寸变了，位置需要重新读取
        tables = driver.find_elements(By.TAG_NAME, "table")
        if not tables:
            raise NoSizeTableError("Description中没有table元素")

        # 计算所有<table>和可选标题的并集包围盒（表格是块级元素，纵向堆叠，
        # 需要取所有元素的最小left/top和最大right/bottom）。只在有标题时
        # 把标题加入范围，其他品牌仍保持原来的表格裁剪逻辑。
        crop_elements = list(tables)
        if table_title:
            crop_elements.extend(driver.find_elements(By.CLASS_NAME, "size-title"))

        left = top = right = bottom = None
        for element in crop_elements:
            location, size = element.location, element.size
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

        margin = 2
        im = im.crop((
            max(0, left - margin),
            max(0, top - margin),
            min(im.width, right + margin),
            min(im.height, bottom + margin)
        ))
        im.save(out_path, "JPEG")

    finally:
        if os.path.exists(temp_html):
            os.remove(temp_html)


# 取内容包围盒：只算"真正画了东西"的元素——直接带文字的元素，以及
# 表格和图片。不能拿最外层的div算，它是块级元素、宽度铺满整个窗口，
# 裁出来两边全是空白；也不能只拿<table>算，标题和脚注在表格外面。
CONTENT_BOX_JS = """
const boxes = [];
document.querySelectorAll('body *').forEach(el => {
    const hasText = Array.from(el.childNodes).some(
        n => n.nodeType === Node.TEXT_NODE && n.textContent.trim() !== '');
    if (!hasText && el.tagName !== 'TABLE' && el.tagName !== 'IMG') return;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;
    boxes.push([r.left + window.scrollX, r.top + window.scrollY,
                r.right + window.scrollX, r.bottom + window.scrollY]);
});
if (!boxes.length) return null;
return [Math.min(...boxes.map(b => b[0])), Math.min(...boxes.map(b => b[1])),
        Math.max(...boxes.map(b => b[2])), Math.max(...boxes.map(b => b[3]))];
"""


def render_styled_to_image(description, code, out_path):
    """Description自带样式，原样渲染后按内容整体裁剪

    和table模式的区别：不套脚本的CSS，裁剪范围也不限于<table>，
    标题、单位、脚注这些表格外面的内容一并保留。
    """
    temp_html = f"temp_{code}.html"

    try:
        driver = get_driver(MODE_STYLED)

        # 用手机宽度解析Description里的响应式样式。
        driver.set_window_size(MOBILE_VIEWPORT_WIDTH, MOBILE_INITIAL_HEIGHT)

        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(build_styled_html(description))

        driver.get(f"file://{os.path.abspath(temp_html)}")
        time.sleep(1)

        # 宽度保持为手机视口，只把高度撑到完整内容。
        content_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
        driver.set_window_size(
            MOBILE_VIEWPORT_WIDTH,
            max(int(content_height) + 40, 200)
        )
        time.sleep(0.5)

        box = driver.execute_script(CONTENT_BOX_JS)
        if not box:
            raise NoSizeTableError("Description渲染后没有可见内容")

        left, top, right, bottom = box
        im = Image.open(BytesIO(driver.get_screenshot_as_png()))

        margin = 4
        im = im.crop((
            max(0, int(left) - margin),
            max(0, int(top) - margin),
            min(im.width, int(right) + margin + 1),
            min(im.height, int(bottom) + margin + 1)
        ))
        im.convert("RGB").save(out_path, "JPEG", quality=92)

    finally:
        if os.path.exists(temp_html):
            os.remove(temp_html)


def render_list_to_image(description, code, out_path, mode):
    """按手机宽度渲染尺码列表，并裁掉视口中的空白区域。"""
    temp_html = f"temp_{code}.html"

    try:
        driver = get_driver(mode)
        driver.set_window_size(MOBILE_VIEWPORT_WIDTH, MOBILE_INITIAL_HEIGHT)

        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(build_list_html(description, mode))

        driver.get(f"file://{os.path.abspath(temp_html)}")
        time.sleep(1)

        content_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
        driver.set_window_size(
            MOBILE_VIEWPORT_WIDTH,
            max(int(content_height) + 40, 200)
        )
        time.sleep(0.5)

        box = driver.execute_script(CONTENT_BOX_JS)
        if not box:
            raise NoSizeTableError("Description渲染后没有可见内容")

        left, top, right, bottom = box
        im = Image.open(BytesIO(driver.get_screenshot_as_png()))

        margin = 4
        im = im.crop((
            max(0, int(left) - margin),
            max(0, int(top) - margin),
            min(im.width, int(right) + margin + 1),
            min(im.height, int(bottom) + margin + 1)
        ))
        im.convert("RGB").save(out_path, "JPEG", quality=92)

    finally:
        if os.path.exists(temp_html):
            os.remove(temp_html)


def render_description(description, code, out_path, mode, table_title=None):
    """按渲染模式出图，失败时抛异常"""
    if mode == MODE_TABLE:
        render_table_to_image(description, code, out_path, table_title)
    elif mode == MODE_STYLED:
        render_styled_to_image(description, code, out_path)
    else:
        render_list_to_image(description, code, out_path, mode)


def render_with_retry(description, code, out_path, mode, attempts=3,
                      table_title=None):
    """出图，偶发失败时重试。返回True成功/False失败

    只重试"可能是偶发"的失败(浏览器崩溃、超时、截图失败)。
    Description里压根没有尺码表属于数据问题，重试多少次都一样，
    直接判定失败——全量跑几千个商品时这个区分能省掉大量无效等待。
    """
    for attempt in range(1, attempts + 1):
        try:
            render_description(description, code, out_path, mode, table_title)
            return True

        except NoSizeTableError as e:
            print(f"该Code的尺码信息有误，请确认: {code} ({e})")
            return False

        except Exception as e:
            if attempt < attempts:
                print(f"出图失败，第{attempt}次重试: {code} ({type(e).__name__}: {e})")
                # 浏览器可能已经崩了，丢掉实例让下次重新拉起
                drop_driver()
                time.sleep(2 * attempt)
            else:
                print(f"出图失败({attempts}次均失败): {code} ({type(e).__name__}: {e})")

    return False


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
    ret, info = qiniu_put_file(token, qiniu_path, local_file_path)

    if info.status_code != 200:
        raise Exception(f"七牛云上传失败: {info}")

    # 用七牛返回的hash(etag)，和列出已有图片时的取值保持一致，
    # 否则同一个文件走不同路径会得到不同的URL
    content_hash = (ret or {}).get('hash')
    if not content_hash:
        with open(local_file_path, 'rb') as f:
            content_hash = hashlib.md5(f.read()).hexdigest()

    return build_image_url(qiniu_path, content_hash)


def upload_with_retry(local_file_path, qiniu_path, attempts=3):
    """上传，失败时重试。上传失败基本都是网络问题，值得重试"""
    for attempt in range(1, attempts + 1):
        try:
            return upload_to_qiniu(local_file_path, qiniu_path)
        except Exception as e:
            if attempt >= attempts:
                raise
            print(f"上传失败，第{attempt}次重试: {qiniu_path} ({type(e).__name__}: {e})")
            time.sleep(2 * attempt)


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
        table_title = get_table_title(brand_name)
        print(f"开始处理文件: {excel_file}")
        print(f"品牌名称: {brand_name}  渲染模式: {mode}"
              f"{'  (复用已有图片)' if skip_existing else ''}")

        df = pd.read_excel(excel_file)
        if 'Code' not in df.columns or 'Description' not in df.columns:
            raise ValueError("Excel必须包含'Code'和'Description'列")
        if 'sizeToImg' not in df.columns:
            df['sizeToImg'] = ''

        existing_urls = list_existing_images(brand_name) if skip_existing else {}

        stats = {'existing_used': 0, 'new_created': 0, 'failed': 0, 'errors': 0}
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

                        if render_with_retry(str(description), current_code,
                                             temp_img_path, mode,
                                             table_title=table_title):
                            current_url = upload_with_retry(temp_img_path, qiniu_path)
                            uploaded_urls.append(current_url)
                            os.remove(temp_img_path)

                            stats['new_created'] += 1
                            print(f"已处理: {current_code} ({stats['new_created']})")
                        else:
                            stats['failed'] += 1

                    previous_code = current_code

                df.at[index, 'sizeToImg'] = current_url

            except Exception as e:
                stats['errors'] += 1
                print(f"处理第 {index + 1} 行时出错: {e}")
                continue

        # 出图都做完了，浏览器可以关了
        drop_driver()

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
        print(f"出图失败: {stats['failed']}")
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

    finally:
        # 出错时也要关掉，否则会残留Chrome进程
        drop_driver()


if __name__ == "__main__":
    try:
        excel_file, brand_name, color_size_flag, skip_existing = parse_args()
        process_excel(excel_file, brand_name, color_size_flag, skip_existing)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
