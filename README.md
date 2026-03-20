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

### `sizeToimage/`

与尺码表图片处理相关的脚本目录，包含新图与旧图两套流程。

### `tianmao_dewu/`

与天猫、得物相关的数据处理脚本目录。

### `ToTMimage/`

图片上传相关脚本目录。

## 使用建议

每个子目录都是一个相对独立的小工具。进入对应目录后，再查看该目录下的 `README.md`、`main.py`、`.bat` 或 `.ps1` 文件即可开始使用。
