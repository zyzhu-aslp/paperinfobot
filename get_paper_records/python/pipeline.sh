#!/bin/bash

set -euo pipefail

# 获取脚本所在目录和项目根目录路径，确保后续文件操作的正确性。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 可直接修改默认值，也可以在命令行传入作为第一个参数覆盖。
# 支持的值：会议投稿、会议成果、期刊投稿、期刊成果、竞赛汇总
table_name="${1:-会议成果}"
style_name="${2:-ieee}"
record_json="../record/${table_name}_mp_records.json"

# 校验 table_name 是否属于预设范围，避免后续脚本拿到无效参数。
validate_table_name() {
  case "$1" in
    "会议投稿"|"会议成果"|"期刊投稿"|"期刊成果"|"竞赛汇总")
      ;;
    *)
      echo "无效的 table_name: $1"
      echo "可选值: 会议投稿, 会议成果, 期刊投稿, 期刊成果, 竞赛汇总"
      exit 1
      ;;
  esac
}

# 检查生成论文 PDF 所需的两个核心工具 pandoc 和 xelatex 是否已经安装在系统中
# 论文导出链路依赖 pandoc 和 xelatex；竞赛链路不需要。
ensure_publication_dependencies() {
  if ! command -v pandoc >/dev/null 2>&1; then
    echo "未找到 pandoc，请先安装 pandoc。"
    exit 1
  fi

  if ! command -v xelatex >/dev/null 2>&1; then
    echo "未找到 xelatex，请先安装 TeX 发行版以生成 PDF。"
    exit 1
  fi
}

# 第一步：从飞书多维表格抓取数据，生成 ../record/<table_name>_mp_records.json。
run_fetch() {
  echo "[1/5] 拉取表格数据: $table_name"
  python main_multi_page.py --table_name "$table_name"
}

# 投稿类记录中的时间字段需要先标准化，成果类可跳过。
run_time_conversion_if_needed() {
  if [ "$table_name" = "会议投稿" ] || [ "$table_name" = "期刊投稿" ]; then
    echo "[2/5] 处理投稿类时间字段"
    python time_format_change.py -input_json "$record_json"
  fi
}

# 论文类链路：JSON -> CSL JSON -> PDF/DOCX。
run_publication_export() {
  local csl_json_name="${table_name}_mp_records_csl.json"

  ensure_publication_dependencies

  echo "[3/5] 生成 CSL JSON"
  python csl_json.py -i "$record_json"

  echo "[4/5] 导出 PDF 和 DOCX，样式: $style_name"
  bash csljson2pdfdocx.sh "$csl_json_name" "$style_name"
}

# 竞赛类链路：导出中英文奖项文本。
run_challenge_export() {
  local awards_dir="../awards"
  mkdir -p "$awards_dir"

  echo "[2/2] 导出竞赛中英文结果"
  python challenge_string.py \
    -input_json "$record_json" \
    -output_cn "$awards_dir/awards_cn.txt" \
    -output_en "$awards_dir/awards_en.txt"
}

# 导出为 BibTeX 格式
run_bibtex_export() {
  local bibtex_dir="../bibtex"
  mkdir -p "$bibtex_dir"
  local output_bib="$bibtex_dir/${table_name}.bib"
  local type

  if [[ "$table_name" == "会议成果" ]]; then
    type="conference"
  elif [[ "$table_name" == "期刊成果" ]]; then
    type="journal"
  else
    # 对于不支持的类型，静默返回
    return
  fi

  echo "[5/5] 导出 BibTeX 文件..."
  python json_to_bibtex.py \
    --type "$type" \
    -input_json "$record_json" \
    -output_bib "$output_bib"
}

# 根据 table_name 选择对应流程入口。
main() {
  validate_table_name "$table_name"

  cd "$SCRIPT_DIR"

  case "$table_name" in
    "会议投稿"|"期刊投稿")
      run_fetch
      run_time_conversion_if_needed
      run_publication_export
      ;;
    "会议成果"|"期刊成果")
      run_fetch
      run_publication_export
      run_bibtex_export
      ;;
    "竞赛汇总")
      run_fetch
      run_challenge_export
      ;;
  esac

  echo "流程完成。"
}

main