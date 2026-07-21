# patagonia_store_stock

按 SKU 抓取 patagonia.jp（巴塔哥尼亚日本官方在线商店）的**价格**和
**门店库存状况（ストアの在庫状況 / 各门店库存）**，并输出到 Excel。

> **别和 `../patagonia_catalog/` 搞混**：本项目输入的是**已知的 SKU 清单**，
> 查的是价格和门店库存；`patagonia_catalog` 是按**类别页全量抓取**商品主数据
> （19 列，含图片、材质、尺寸表等），不需要预先给 SKU。两者用途不同，代码也独立。

## 处理流程

1. 读取 `items.xlsx` 的 `sku` 列（SKU 格式：`{商品编号}-{颜色}-{尺码}`，例如 `60421-EDBL-18M`）。
2. 用 `https://www.patagonia.jp/search?q={商品编号}` 检索，获取商品详情页 URL。
3. 在商品页通过 URL 参数 + 点击 swatch 选择**颜色**，点击单选按钮选择**尺码**。
4. 获取所选颜色·尺码对应的**价格**。
5. 点击「ストアの在庫状況（门店库存状况）」按钮，抓取弹出的各**门店名**及其
   **库存状态**（あり=有货 / わずか=少量 / なし=无货）。
6. 将结果输出到 Excel（`sku url color size price shop1 stock1 shop2 stock2 ...`）。

## 使用的库

- **[Scrapling](https://github.com/D4Vinci/Scrapling)** `[fetchers]` —— 隐身浏览器
  （基于 Camoufox）。patagonia.jp 会对疑似爬虫返回限流/失败页（"Sit tight" /
  SPA-sitefailover），普通 HTTP 请求拿不到真实页面。本工具用 Scrapling 的
  `StealthySession` 并以**有头模式（显示浏览器窗口）**运行来绕过检测。
- **openpyxl** —— Excel 读写。

> 反爬要点：必须 `headless=False`（有头模式）。先访问 `/home/` 给会话「热身」。
> 收到失败页时重启会话并重试。注意它**不是 Cloudflare**，因此 `solve_cloudflare` 无效。
> 实测无头模式即使热身也会被拦截，所以必须有头运行（会弹出浏览器窗口）。

## 环境准备

```powershell
# 虚拟环境（也可直接复用兄弟项目 lululemon_scrapling 的 .venv）
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 首次需要下载 Scrapling 使用的浏览器
scrapling install
```

## 运行

```powershell
# 先用几条测试（会弹出浏览器窗口）
python main.py --limit 2 --no-resume

# 全量（items.xlsx 中的所有 SKU）
python main.py
```

运行过程中进度会保存到 `.patagonia_cache/progress.json`。中途中断后再次运行会
**从断点继续**（想从头重跑请加 `--no-resume`）。

### 主要参数

| 参数 | 说明 |
| --- | --- |
| `--input PATH` | 输入 Excel（默认 `items.xlsx`，需包含 `sku` 列） |
| `--output-dir DIR` | 输出目录（默认：脚本所在文件夹） |
| `--limit N` | 只处理前 N 条（用于调试） |
| `--no-resume` | 忽略缓存，从头开始 |
| `--headless` | 以无头模式运行（**容易被拦截，不推荐**） |

## 输出

生成 `patagonia_output_{时间戳}.xlsx`，列结构如下：

```
sku  product_name  url  color  color_name  size  price  note  shop1 stock1 shop2 stock2 ...
```

- `color` 是 SKU 中的颜色代码（如 `EDBL`），`color_name` 是颜色全称（如 `Eddy Blue`）。
- `price` 为含税价格（数值，日元）。
- `shopN` / `stockN` 为门店名和库存状态（`あり` / `わずか` / `なし`）。
  各商品的门店数量不同，所以列数会按所有行中的最大门店数自动扩展。
- `note` 用于补充说明，如「检索不到商品」「尺码缺货无法选择」等。

## 注意事项

- 每条 SKU 约需 20～40 秒（为规避反爬而加入的等待，以及真实浏览器操作所致）。
- 由于以有头模式运行，执行期间会弹出浏览器窗口，请勿关闭。
- 尺码命名差异：SKU 用连字符（如 `L-XL`），而网站可能用斜杠（如 `L/XL`）。
  程序已自动兼容这两种写法。
- 「ストアの在庫状況」由第三方服务 Locally 加载，抓取的是直营店
  （`パタゴニア ◯◯`）的库存。
