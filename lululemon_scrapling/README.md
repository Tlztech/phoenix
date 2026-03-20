# lululemon Scrapling

使用 Python + Scrapling 抓取 lululemon 日本站分类页与商品详情页数据，并导出为 Excel。

## 功能

1. 从分类页或搜索页读取种子 URL
2. 自动翻页并收集商品详情页 URL
3. 导出商品 URL 清单到 `lululemon_url_YYYYMMDDHHMMSS.xlsx`
4. 导出商品明细到 `lululemon_output_YYYYMMDDHHMMSS.xlsx`
5. 抓取失败的商品 URL 会写入 `lululemon_cannotopenurl_YYYYMMDDHHMMSS.xlsx`
6. 分类页打开失败时会写入 `lululemon_error_YYYYMMDDHHMMSS.txt`
7. 支持 checkpoint 断点续跑，缓存保存在 `.lululemon_cache/`

## 输出字段

导出的商品明细 Excel 包含以下列：

`type`  
`title`  
`model`  
`u_model`  
`url`  
`brand`  
`color`  
`size`  
`msrp`  
`discounted_price`  
`stock_status`  
`quantity`

说明：

- `type` 来自商品详情页面包屑导航的第一级分类链接英文路径，例如 `/ja-jp/c/men` 对应 `men`
- `brand` 固定为 `lululemon`
- `model` 优先取商品数据里的 productID，兜底取 `SKU:` 或 URL
- `u_model` 从商品图片 URL 中提取
- `stock_status` 输出 `in-stock`、`low-stock`、`out-of-stock`
- `quantity` 当前映射为 `in-stock -> 6`、`low-stock -> 3`、`out-of-stock -> 0`

## 安装

```bash
pip install -r lululemon_scrapling/requirements.txt
```

## 用法

默认读取 `lululemon_url.txt` 中的种子 URL：

```bash
python lululemon_scrapling/main.py
```

只跑 1 个分类页，并抓取前 5 个商品做测试：

```bash
python lululemon_scrapling/main.py --seed-limit 1 --detail-limit 5
```

指定自定义分类页 URL：

```bash
python lululemon_scrapling/main.py --seed-url "https://www.lululemon.co.jp/ja-jp/c/men" --seed-url "https://www.lululemon.co.jp/ja-jp/c/women/tops"
```

指定输出目录：

```bash
python lululemon_scrapling/main.py --output-dir ./outputs
```

## 在当前机器上运行

如果 `python` 不在 `PATH` 中，可以直接运行：

```bat
run_scraper.cmd
```

快速联调：

```bat
run_scraper.cmd --seed-limit 1 --detail-limit 5 --no-resume
```

## 定时任务

可以通过 Windows 计划任务每周自动运行。当前项目配套的 `run_scraper.ps1` 支持：

- 自动把每次结果归档到 `scheduled_runs/时间戳/`
- 运行失败时在 `alerts/` 下生成提醒文件

## 解析逻辑

- 分类页通过 HTML 中的商品链接与 `see-more-button` 翻页链接采集商品 URL
- 商品详情优先解析 `digitalData.product.push({...})`
- 如果主数据不存在，则回退到 JSON-LD
- `type` 优先从 JSON-LD 的 `BreadcrumbList` 读取，兜底再从页面 breadcrumb HTML 提取
