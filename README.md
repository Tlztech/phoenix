# phoenix

一个用于存放多个日常工具脚本的小型工具仓库。

## 目录说明

### `lululemon_scrapling/`

抓取 lululemon 日本站分类页与商品详情页数据，并导出 Excel。

- 主程序：`lululemon_scrapling/main.py`
- 依赖：`lululemon_scrapling/requirements.txt`
- Windows 启动：`lululemon_scrapling/run_scraper.cmd`
- Windows 定时任务入口：`lululemon_scrapling/run_scraper.ps1`
- 项目说明：`lululemon_scrapling/README.md`

### `patagonia_store_stock/`

按 **SKU** 抓取 patagonia.jp 的**价格**和**各门店库存状况**（ストアの在庫状況），输出 Excel。
输入是一份已知的 SKU 清单，用于查价 / 查门店有没有货。

- 主程序：`patagonia_store_stock/main.py`
- 输入：`patagonia_store_stock/items.xlsx`（`sku` 列）
- 依赖：`patagonia_store_stock/requirements.txt`
- 项目说明：`patagonia_store_stock/README.md`

### `patagonia_catalog/`

按**类别页**全量抓取 patagonia.jp 的商品，展开颜色 / 尺码变体，输出 19 列商品主数据。
和上面那个不是一回事：这个是「把整个类别的商品都爬下来」，不需要预先给 SKU。

- 主程序：`patagonia_catalog/main.py`（源码在 `src/patagonia_scraper/`）
- 输入：`patagonia_catalog/input_url.txt`（类别页 URL，每行一个）
- 依赖：`patagonia_catalog/requirements.txt`
- Windows 定时任务 + 自动续跑：`patagonia_catalog/windows-deploy/`、`部署说明.md`
- 项目说明：`patagonia_catalog/README.md`
- 开发/排查记录：`patagonia_catalog/会话记录.md`

> 两个 patagonia 项目的反爬手段不同：`patagonia_store_stock` 用 Scrapling 隐身浏览器，
> `patagonia_catalog` 面对的是 Akamai Bot Manager，必须用命令行启动的真实 Chrome + CDP 挂载。
> 两者都需要**有头模式**运行，执行期间会弹出浏览器窗口，请勿关闭。

### `sizeToimage/`

与尺码表图片处理相关的脚本目录，包含新图与旧图两套流程。

### `tianmao_dewu/`

与天猫、得物相关的数据处理脚本目录。

### `ToTMimage/`

图片上传相关脚本目录。

## 使用建议

每个子目录都是一个相对独立的小工具。进入对应目录后，再查看该目录下的 `README.md`、`main.py`、`.bat` 或 `.ps1` 文件即可开始使用。
