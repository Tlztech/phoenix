# Patagonia 日本官网商品爬虫

爬取 `https://www.patagonia.jp/shop/womens` 等类别页，展开客户端渲染的商品列表，
解析每个商品的 JSON-LD / HTML，展开颜色和尺码变体，输出与参考文件
`Patagonia-V8.2.xlsx` 相同的 19 列数据到 Excel。

> **别和 `../patagonia_store_stock/` 搞混**：那个项目输入的是**已知 SKU 清单**，
> 只查价格和门店库存；本项目是按**类别页全量抓取**商品主数据，不需要预先给 SKU。
> 两者面对的反爬也不同（那边是 Scrapling 隐身浏览器，这边是 Akamai + 真实 Chrome）。

---

## 一、反爬机制说明

`patagonia.jp` 在 `/shop/*` 和 `/product/*` 路径前面部署了 **Akamai Bot Manager**。
对没有有效 `_abck` 传感器 cookie 的请求，这些路径一律返回硬性 `404`
（`Server: AkamaiNetStorage`，10 字节正文）。实测下列方式都拿不到该 cookie、全部被 404：

- HTTP 伪装请求（curl_cffi / requests）
- Scrapling 隐身浏览器（camoufox）
- 由 Playwright **启动**的 Chrome（`navigator.webdriver === true`）

只有营销首页 `/home/`、`sitemap.xml`、`robots.txt` 不受限。

**本项目采用的可靠方案：**

1. **用命令行启动真实的 Google Chrome**（带远程调试端口 + 独立 profile）。命令行启动的
   Chrome，`navigator.webdriver === false`，这点和 Playwright 启动的不同。
2. **通过 CDP 挂载**到这个 Chrome，复用它已有的浏览器上下文，让 cookie 贯穿整个抓取过程。
3. **先在 `/home/` 热身**（停留 + 滚动），让 Akamai 传感器运行并通过验证；之后所有
   `/shop/*` 和 `/product/*` 请求都会返回 `200`。

整个流程由程序**全自动完成**，你不需要手动开浏览器——它会自己启动 Chrome、热身、然后开始爬。

> 说明：Akamai 判定的是「自动化行为」而非 IP，所以在日本正常的家庭/办公网络下可以正常工作
> （被标记的数据中心 / VPN 出口 IP 可能不行）。

---

## 二、工程结构

```
patagonia_catalog/
├─ main.py                     入口脚本（python main.py 运行）
├─ input_url.txt               要爬取的类别页 URL（每行一个，可编辑）
├─ requirements.txt            依赖清单
├─ pyproject.toml              项目/打包配置
├─ README.md                   本说明文件
├─ 部署说明.md                  Windows 定时任务 + 自动断点续跑的部署步骤
├─ 会话记录.md                  开发/排查记录（反爬怎么破的、各字段怎么核对的）
├─ .gitignore
├─ Patagonia-V8.2.xlsx         参考数据（用于核对字段是否正确）
├─ Patagonia-女装url.xlsx       商品 URL 工作簿示例（配合 --url-file 使用）
├─ windows-deploy/             Windows 无人值守部署脚本
│  ├─ install.bat / install_task.ps1   注册「每 10 分钟检查一次」的计划任务
│  ├─ monitor.ps1                      监控脚本：被限流停了就等 30 分钟自动续跑
│  └─ stop.bat / stop.ps1              停止并卸载计划任务
├─ output/                     输出目录（自动创建；含最新结果、_part 部分结果、.checkpoint 断点）
│  └─ history/                 历次运行的旧结果自动归档到这里

├─ .chrome-profile/            Chrome 专用 profile（自动创建，保存热身后的会话，勿手动删）
└─ src/patagonia_scraper/      源码包
   ├─ cli.py                   命令行参数解析与主流程
   ├─ fetcher.py               CDP 挂载 Chrome、热身、并发抓取
   ├─ scraper.py               类别页发现商品、逐商品解析、生成数据行、断点续爬
   ├─ checkpoint.py            断点记录（已完成商品落盘、续爬时跳过）
   ├─ parser.py                JSON-LD / HTML 解析、字段清洗、图片处理
   ├─ generic_parser.py        兜底解析器（主解析失败时使用）
   ├─ models.py                数据模型（ProductRow / ColorVariant 等）、输出列定义
   ├─ excel.py                 Excel 写出（表头样式、列宽、文件名时间戳）
   └─ constants.py             默认类别 URL、输出列常量
```

> `.chrome-profile/` 和 `output/` 会自动生成，且已在 `.gitignore` 中忽略，**部署时不需要拷贝**。

---

## 三、安装

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium   # 仅在没有安装 Google Chrome 时才需要
```

必须安装 **Google Chrome**（程序用真实 Chrome，而不是自带的 Chromium，因为 Akamai 对真实
Chrome 更宽容）。Windows 下会自动检测 Chrome 路径；如检测不到可用 `--chrome-path` 指定。

---

## 四、部署到其他电脑

项目是自包含的。部署到一台全新的 Windows 电脑步骤如下：

1. **安装 Python 3.10+** —— <https://www.python.org/downloads/>（安装时勾选
   "Add python.exe to PATH"）。验证：`python --version`。
2. **安装 Google Chrome** —— <https://www.google.com/chrome/>。这是程序驱动、用来通过
   Akamai 的浏览器，**必须安装**。
3. **拷贝工程目录**到新电脑（或 `git clone`）。只需源码即可，`.chrome-profile/` 和
   `output/` 会自动重建，不用拷。
4. **安装依赖**（在工程目录内执行）：

   ```powershell
   python -m pip install -r requirements.txt
   ```

   如果目标电脑**没有** Google Chrome 又无法安装，则执行
   `python -m playwright install chromium`，并在运行时用 `--chrome-path` 指向该 Chromium；
   否则优先用 Chrome。
5. **按需编辑 `input_url.txt`**，改成你要爬的类别。
6. **运行**（在工程目录内）：

   ```powershell
   python main.py
   ```

目标电脑注意事项：

- 需要能访问 `www.patagonia.jp` 的外网。
- **每台电脑首次运行较慢**：会创建 `.chrome-profile/` 并热身 Akamai 会话；之后的运行会复用该
  profile，更快。
- 运行中会弹出一个 Chrome 窗口，这是正常的（默认有头模式对 Akamai 更稳），**运行期间不要关它**。
- Chrome 装在非标准位置时，用 `--chrome-path "C:\路径\chrome.exe"` 指定。

> 想让它**无人值守地跑**（注册 Windows 计划任务，被 Akamai 限流停了就等 30 分钟自动续跑，
> 直到全部抓完）：见 [部署说明.md](部署说明.md)，脚本在 `windows-deploy/`。

---

## 五、运行方式

### 1. 默认方式（读 `input_url.txt`）

```powershell
python main.py
```

无需任何参数。要爬的类别 URL 从 `input_url.txt` 读取（每行一个，空行和 `#` 开头的注释会被忽略）。
结果写入 `output/` 目录（自动创建），文件名为 `patagonia_output_YYYYMMDDHHMMSS.xlsx`。

`input_url.txt` 默认内容：

```
https://www.patagonia.jp/shop/womens
```

想爬多个类别，就在文件里每行加一个 URL（多个类别之间的商品会自动去重）。

### 2. 临时指定单个类别 URL（覆盖 input_url.txt）

```powershell
python main.py --url https://www.patagonia.jp/shop/womens/tops/t-shirts
```

### 3. 从商品 URL 工作簿抓取（定点验证用）

```powershell
python main.py --url-file Patagonia-女装url.xlsx --max-products 10
```

### 4. 先小批量试跑

```powershell
python main.py --max-products 20     # 只爬前 20 个商品
```

---

## 六、并发参数

程序在**同一个已热身的浏览器上下文里开多个标签页（tab）并发抓取**，这些 tab 共享同一颗
Akamai `_abck` cookie，所以并发不需要重复热身。

```powershell
python main.py                     # 默认并发 3
python main.py --concurrency 5     # 小批量想更快时可以提到 5
```

- `--concurrency N`：并发抓取的商品页数量（额外标签页数）。**默认 `3`**。
- **全量抓取（几百个商品）建议保持 3**：并发越高，持续请求速率越快，越容易把 IP 触发 Akamai 限流
  （实测并发 5 跑 588 个商品时中途被限流）。小批量（几十个）可临时提到 5 提速。
- **不要设太高**（如 5 以上/20+）：并发过大容易被 Akamai 重新判定为机器人，触发限流甚至 404。
- 万一中途被限流：程序会自动重试 + 熔断降速；实在扛不住会保留断点、退出，等一会儿重跑同样命令即可续爬。
- 类别页「发现商品 URL」阶段是一次性把整页商品捞出来的，不受并发影响；并发只作用于之后逐个抓取商品详情。

---

## 七、断点续爬与中途保存（重要）

抓取过程中如果被 Akamai 临时挡住（出现 not found / 404），程序会**自动回首页重新热身并重试**；
即使真的中断（比如手动关掉运行窗口），也**不会丢数据**，因为：

- **每爬完一个商品就立即落盘**到断点文件 `output/.checkpoint_<任务号>.jsonl`（追加写、崩溃安全）。
- **每完成 5 个商品**（可用 `--flush-every` 调整）就把当前已爬结果写到
  `output/patagonia_output_<任务号>_part.xlsx`（`_part` 表示这是部分结果）。

**续爬**：直接**用同样的命令再跑一次**即可。程序会读断点文件，**跳过已经爬到数据的商品**，
只继续爬剩下的：

```powershell
python main.py              # 第一次；若中途中断……
python main.py              # ……再跑一次同样的命令，自动接续，跳过已完成的
```

- 全部商品爬完后，才会生成正式文件 `patagonia_output_YYYYMMDDHHMMSS.xlsx`，并**自动清理**
  `_part` 和断点文件。
- 未全部完成时，程序退出码为 `1`，并提示「已完成 X/Y，部分结果已保存到 …_part.xlsx，
  重新运行同样命令可续爬」。
- 断点是按「任务」区分的（类别 URL 组合或 `--url-file` 路径决定任务号），不同任务互不干扰。
- 抓取失败（404 等）的商品**不会**记入断点，续爬时会重新尝试。
- 不想续爬、想全部重来：加 `--no-resume`。

### 周期运行如何保证拿到最新数据

如果你是**每隔几天跑一次**来刷新数据，不用担心「任务号不变」会拿到旧数据：

- 上一次**跑完了** → 断点会被删除 → 下一次是全新抓取，拿的是**当天最新数据**。
- 上一次**没跑完**（崩溃/关窗口）→ 断点残留；但断点**超过 24 小时**（`--resume-max-age-hours`，
  默认 24）就会被判为过期，**自动丢弃、从头重抓**。所以隔几天的周期运行永远是全新数据，
  不会把几天前的旧价格/库存混进来。
- 只有在**同一天内**、上一次没跑完时，续爬才会生效（用于崩溃后当天重跑，省时间）。
- 想让**每次都强制全新**（完全不续爬）：在定时命令里加 `--no-resume`。

> `.checkpoint_*.jsonl` 和 `_part.xlsx` 都在 `output/` 下，已被 `.gitignore` 忽略。

### 运行汇总

每次运行结束会打印一段汇总，例如：

```
================ 运行汇总 ================
状态          : 全部完成
用时          : 8分12秒
发现商品URL   : 303 个
成功抓取商品  : 303 个
获取SKU变体行 : 4821 个（去重后）
其中有效SKU   : 4821 个
去除重复行    : 0 个
输出文件      : output\patagonia_output_20260716xxxxxx.xlsx
=========================================
```

- 结果在写出前会**按 SKU 去重**（`模型-颜色-尺码` 相同的行只保留一条），汇总里会显示去掉了多少条。
- 「状态」为「全部完成」时，才会写正式文件并删除 `_part`/断点；未完成时状态会显示 `未完成（X/Y）`，
  输出为 `_part` 文件，退出码为 `1`。
- 这段汇总同时会**写入一个 `.txt` 文件**，放在输出文件旁边、同名加 `_summary` 后缀，例如
  `output/patagonia_output_20260716xxxxxx_summary.txt`（含完成时间戳），方便留存和查看。

### 多次运行的历史文件归档

多次运行时，`output/` 只保留**最新一次**的结果（xlsx + summary）；**之前的历史结果会自动移到
`output/history/`**，不会被删除，也不会堆在 `output/` 里。想保持全部堆在 `output/`、不归档，
加 `--no-archive`。

---

## 八、其他常用参数

| 参数 | 说明 |
|---|---|
| `--input-file <路径>` | 类别 URL 列表文件（默认 `input_url.txt`） |
| `--url <URL>` | 单个类别 URL，覆盖 `--input-file` |
| `--url-file <xlsx>` | 商品 URL 工作簿（单元格里含 `/product/` 链接，按原样使用） |
| `--max-products N` | 最多抓取 N 个商品 |
| `--max-pages N` | 类别页展开的滚动/加载轮次上限 |
| `--concurrency N` | 并发抓取数（默认 3；全量建议 3，小批量可提到 5） |
| `--max-retries N` | 单个商品被 404 时的重试次数（默认 3） |
| `--no-resume` | 忽略断点，全部重新抓取 |
| `--resume-max-age-hours N` | 只续爬 N 小时内的断点，更旧的丢弃并全新重抓（默认 24） |
| `--no-archive` | 不把历史结果移到 `output/history/`，全部留在 `output/` |
| `--flush-every N` | 每完成 N 个商品写一次 `_part` 部分结果（默认 5） |
| `--output <文件>` | 指定完整输出文件路径（仅在全部完成时写） |
| `--output-dir <目录>` | 指定输出目录（默认 `output`） |
| `--chrome-path <路径>` | Chrome 可执行文件路径（自动检测失败时用） |
| `--cdp-url ws://…` | 挂载到你自己已启动并热身好的 Chrome，而不是让程序自己启动 |
| `--remote-port N` | Chrome 远程调试端口（默认 `9222`） |
| `--user-data-dir <目录>` | Chrome profile 目录（默认 `./.chrome-profile`，跨运行复用以保持会话热度） |
| `--proxy <URL>` | 给 Chrome 指定代理（如住宅代理 `http://user:pass@host:port`），可绕过按 IP 的限流 |
| `--no-block-resources` | 下载图片/字体（默认拦截其字节，只取 URL，省流量/加速，走代理时尤其省钱） |
| `--fresh-profile` | 启动前删除 Chrome profile（丢弃卡住/被封的会话，换全新身份重试） |
| `--headless` | 无头模式运行 Chrome（对 Akamai 风险更高；默认有头） |
| `--no-warmup` | 跳过首页热身（仅在 profile 已热身好时用） |
| `--proxy <URL>` | 给 Chrome 指定代理 |
| `--delay-min` / `--delay-max` | 请求之间的随机延迟范围（秒） |
| `-v` / `--verbose` | 输出更详细的日志 |

---

## 九、被 Akamai 拦截怎么办（出现大量 404 / 未发现商品）

如果日志出现 `Got 404 (Akamai block)`、`未发现任何商品 URL`，说明被 Akamai 拦了。程序已会
**自动清 cookie 并重新热身、每个类别重试 3 次**；若仍失败会**保留断点、不写乱结果**，并打印
处置建议。此时按顺序尝试：

1. **等 10~30 分钟再重跑同样命令**。连续跑太多次会触发 IP 临时限流，等一会儿通常自动恢复。
2. **换全新浏览器身份**：`python main.py --fresh-profile`。这会删掉 `.chrome-profile`（可能存了一颗
   坏掉的 `_abck` cookie），用干净会话重来。关命令行/浏览器窗口**不会**清这个 profile，所以这一步很关键。
3. **降低并发**：`python main.py --concurrency 3`（甚至 `--concurrency 1`），更像真人、更不容易被判机器人。
4. **确认是不是 IP 级别**：用你自己的普通 Chrome 手动打开 <https://www.patagonia.jp/shop/womens>。
   如果**人也打不开**，就是 IP 被临时限流，只能等；如果人能打开、只有程序被挡，用第 2、3 步基本能恢复。
5. 别太频繁跑。周期刷新建议间隔久一点（如每天/隔几天一次），并发保持 3~5。

> 被拦时程序**不会破坏已有数据**：断点保留，下次恢复后接着抓；也不会把"0 个商品"当成结果写出去。

---

## 十、输出字段说明

每一行是一个变体记录（一个颜色 + 尺码组合），共 19 列：

`title`（标题）、`model`（型号）、`sku`、`upc_barcode_ean`、`brand`、`size`（尺码）、
`url`、`color`（颜色码）、`msrp`（原价）、`discounted_price`（折扣价）、
`product_main_image`（主图）、`product_other_image`（其他图，换行分隔）、
`dimension`（尺寸表 HTML）、`description`（描述）、`product_spec`、`material`（材质）、
`weight`（重量）、`stock_status`（库存状态）、`quantity`（数量）。

- `product_main_image` 为该颜色主图（`{型号}_{颜色}.jpg`）。
- `product_other_image` 为该颜色的细节图集，通过 Patagonia 的 `Product-AltAssets` 接口逐色获取
  （共享的 `_000_` 生活场景图在前，然后是该颜色自己的细节图，各组按文件名排序）。
- `dimension` 为清洗后的尺寸表格。
- 价格采用参考文件里的日元格式（`¥ 12,320`）。
- 无库存的变体写为 `在庫なし`，数量为 `0`。

### 与参考文件的核对结论

对照 `Patagonia-V8.2.xlsx` 逐字段验证（多批次、15/20/50 个商品）：

- `title`、`model`、`sku`、`brand`、`msrp`、`weight`、`material`、`dimension`、`color`、`size`、
  `product_main_image`、`product_other_image` —— **匹配一致**。
- `stock_status` / `quantity` 是实时数据，本就会随时间变化。
- `description` 直接取自页面 JSON-LD，会跟随网站当前文案（个别商品有空格 / 保养文字等细微漂移）。
- 少数 `msrp` 差异是网站现价变动；少数 `weight` 差异是参考文件本身为空、本程序反而多抓到了。

> 请勿使用本爬虫绕过访问控制或超出网站条款 / robots 规则。
