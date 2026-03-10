# get_paper_records Pipeline 说明

本目录提供了一套从飞书多维表格拉取数据，到导出指定格式结果的自动化流程。

统一入口脚本位于 [get_paper_records/python/pipeline.sh](get_paper_records/python/pipeline.sh)。

## 功能概览

根据 `table_name` 的不同，脚本会自动选择对应处理链路：

- `会议投稿`、`期刊投稿`
	先抓取飞书表格数据，再标准化时间字段，再转换为 CSL JSON，最后导出 PDF 和 DOCX。
- `会议成果`、`期刊成果`
	先抓取飞书表格数据，跳过时间标准化，直接转换为 CSL JSON，最后导出 PDF 和 DOCX。
- `竞赛汇总`
	先抓取飞书表格数据，再导出竞赛成果的中英文文本。

## 目录说明

- [get_paper_records/python](get_paper_records/python)
	核心脚本目录。
- [get_paper_records/csl](get_paper_records/csl)
	论文类流程生成的 CSL JSON 文件输出目录。
- [get_paper_records/export_md](get_paper_records/export_md)
	论文类流程生成的 Markdown 输出目录。
- [get_paper_records/file_output](get_paper_records/file_output)
	论文类流程生成的 PDF、DOCX 输出目录。
- [get_paper_records/awards](get_paper_records/awards)
	竞赛汇总流程的中英文文本输出目录。
- [get_paper_records/record](get_paper_records/record)
	第一步抓取到的原始记录输出目录。

## 脚本职责

- [get_paper_records/python/main_multi_page.py](get_paper_records/python/main_multi_page.py)
	根据表名从飞书多维表格拉取完整记录，输出为 `../record/<table_name>_mp_records.json`。
- [get_paper_records/python/time_format_change.py](get_paper_records/python/time_format_change.py)
	仅用于投稿类数据，原地修改 JSON 中的时间字段格式。
- [get_paper_records/python/csl_json.py](get_paper_records/python/csl_json.py)
	将论文类 JSON 转换为 CSL JSON，并输出到 [get_paper_records/csl](get_paper_records/csl)。
- [get_paper_records/python/generate_export_md.py](get_paper_records/python/generate_export_md.py)
	根据 CSL JSON 生成 pandoc 使用的 Markdown 文件。
- [get_paper_records/python/csljson2pdfdocx.sh](get_paper_records/python/csljson2pdfdocx.sh)
	调用 pandoc，将 CSL JSON 进一步导出为 PDF 和 DOCX。
- [get_paper_records/python/challenge_string.py](get_paper_records/python/challenge_string.py)
	将竞赛汇总 JSON 导出为中英文奖项文本。
- [get_paper_records/python/pipeline.sh](get_paper_records/python/pipeline.sh)
	总控脚本，负责按 `table_name` 串联整个流程。

## 环境依赖

运行前请确保以下环境可用：

- Python 3
- `requests`、`lark_oapi` 等 Python 依赖
- `pandoc`
- `xelatex`

说明：

- 只有论文类导出流程依赖 `pandoc` 和 `xelatex`。
- `竞赛汇总` 仅依赖 Python 脚本本身，不需要 `pandoc`。

如果使用 Conda 或虚拟环境，请先激活对应环境再执行脚本。

## 使用方法

先进入脚本目录：

```bash
cd get_paper_records/python
```

如首次使用，可先赋予执行权限：

```bash
chmod +x pipeline.sh
chmod +x csljson2pdfdocx.sh
```

然后执行总控脚本，并传入一个表名：

```bash
bash pipeline.sh 会议投稿
```

论文类流程还支持传入第二个参数指定引用样式，例如：

```bash
bash pipeline.sh 会议成果 ieee
```

可选表名如下：

- `会议投稿`
- `会议成果`
- `期刊投稿`
- `期刊成果`
- `竞赛汇总`

示例：

```bash
bash pipeline.sh 会议成果
bash pipeline.sh 会议成果 acm
bash pipeline.sh 会议成果 apa
bash pipeline.sh 期刊投稿
bash pipeline.sh 竞赛汇总
```

如果不传参数，脚本会使用 [get_paper_records/python/pipeline.sh](get_paper_records/python/pipeline.sh) 中设置的默认值：

```bash
table_name="${1:-会议成果}"
```

这意味着下面这条命令会默认处理 `会议成果`：

```bash
bash pipeline.sh
```

## 可选引用样式

论文类导出目前支持以下主流样式：

- `ieee`
- `acm`
- `apa`
- `mla`
- `chicago`
- `nature`

对应的 CSL 文件位于 `styles-master` 目录：

- `ieee` -> `ieee.csl`
- `acm` -> `acm-sig-proceedings.csl`
- `apa` -> `apa.csl`
- `mla` -> `modern-language-association.csl`
- `chicago` -> `chicago-author-date.csl`
- `nature` -> `nature.csl`

说明：

- 如果不传样式参数，默认使用 `ieee`。
- 样式参数只对论文类流程生效，对 `竞赛汇总` 无影响。

## 执行流程

### 1. 投稿类流程

适用表名：`会议投稿`、`期刊投稿`

执行顺序：

1. 运行 [get_paper_records/python/main_multi_page.py](get_paper_records/python/main_multi_page.py)
2. 运行 [get_paper_records/python/time_format_change.py](get_paper_records/python/time_format_change.py)
3. 运行 [get_paper_records/python/csl_json.py](get_paper_records/python/csl_json.py)
4. 运行 [get_paper_records/python/csljson2pdfdocx.sh](get_paper_records/python/csljson2pdfdocx.sh)

对应中间文件和输出文件：

- 原始记录 JSON：`get_paper_records/record/<table_name>_mp_records.json`
- CSL JSON：`get_paper_records/csl/<table_name>_mp_records_csl.json`
- Markdown：`get_paper_records/export_md/<table_name>_mp_records_csl_<style>_export.md`
- PDF：`get_paper_records/file_output/<table_name>_mp_records_csl_<style>.pdf`
- DOCX：`get_paper_records/file_output/<table_name>_mp_records_csl_<style>.docx`

### 2. 成果类流程

适用表名：`会议成果`、`期刊成果`

执行顺序：

1. 运行 [get_paper_records/python/main_multi_page.py](get_paper_records/python/main_multi_page.py)
2. 跳过时间格式处理
3. 运行 [get_paper_records/python/csl_json.py](get_paper_records/python/csl_json.py)
4. 运行 [get_paper_records/python/csljson2pdfdocx.sh](get_paper_records/python/csljson2pdfdocx.sh)

输出文件位置与投稿类一致。

### 3. 竞赛类流程

适用表名：`竞赛汇总`

执行顺序：

1. 运行 [get_paper_records/python/main_multi_page.py](get_paper_records/python/main_multi_page.py)
2. 运行 [get_paper_records/python/challenge_string.py](get_paper_records/python/challenge_string.py)

输出文件：

- [get_paper_records/awards/awards_cn.txt](get_paper_records/awards/awards_cn.txt)
- [get_paper_records/awards/awards_en.txt](get_paper_records/awards/awards_en.txt)

## 产物命名规则

论文类流程的命名规则如下：

- 输入记录文件：`record/<table_name>_mp_records.json`
- CSL 文件：`<table_name>_mp_records_csl.json`
- 导出 Markdown：`export_md/<table_name>_mp_records_csl_<style>_export.md`
- PDF：`file_output/<table_name>_mp_records_csl_<style>.pdf`
- DOCX：`file_output/<table_name>_mp_records_csl_<style>.docx`

这样可以保证不同表名的导出结果互不覆盖。

## 常见问题

### 1. 找不到 pandoc

如果出现 `未找到 pandoc`，需要先安装 pandoc。

### 2. 找不到 xelatex

如果出现 `未找到 xelatex`，需要先安装 TeX 发行版，例如 MacTeX。

### 3. 找不到 CSL JSON 或输出文件

请确认当前命令是在 [get_paper_records/python](get_paper_records/python) 目录下执行的。当前脚本大量使用了 `../` 相对路径，脱离该目录运行容易导致文件找不到。

### 4. Word 样式不是自定义模板样式

当前 DOCX 导出未依赖 `reference.docx`，因此会使用 pandoc 默认 Word 样式。

## 推荐命令

论文类：

```bash
cd get_paper_records/python
bash pipeline.sh 会议成果
bash pipeline.sh 会议成果 acm
```

竞赛类：

```bash
cd get_paper_records/python
bash pipeline.sh 竞赛汇总
```
