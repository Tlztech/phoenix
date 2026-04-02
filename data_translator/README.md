# data_translator

Excel 标题翻译小工程。

## 用法

```powershell
python translate_title_chn.py --input "C:\Users\tlzs\Downloads\MONTBELL_普通款总表.xlsx" --output ".\MONTBELL_普通款总表_TitleChn.xlsx"
```

脚本会：
- 将 `Title` 列中含日文的标题翻译为中文
- 中文或中英混合标题保持原样
- 在 `Title` 右侧写入新的 `TitleChn` 列
- 将在线翻译结果缓存到本地 `title_translation_cache.json`
