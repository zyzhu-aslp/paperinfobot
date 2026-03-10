#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ "$#" -lt 1 ]; then
  echo "用法: ./csljson2pdfdocx.sh <csl_json文件名> [style]"
  echo "示例: ./csljson2pdfdocx.sh 会议成果_mp_records_csl.json ieee"
  echo "可选样式: ieee, acm, apa, mla, chicago, nature"
  exit 1
fi

CSL_JSON_NAME="$1"
STYLE_NAME="${2:-ieee}"
CSL_JSON_PATH="$PROJECT_DIR/csl/$CSL_JSON_NAME"

if [ ! -f "$CSL_JSON_PATH" ]; then
  echo "未找到文件: $CSL_JSON_PATH"
  exit 1
fi

OUT_DIR="$PROJECT_DIR/file_output"
mkdir -p "$OUT_DIR"

STEM="${CSL_JSON_NAME%.json}"
OUTPUT_STEM="${STEM}_${STYLE_NAME}"

echo "Sanitizing CSL JSON..."
python - "$CSL_JSON_PATH" <<'PY'
import json
import sys
from pathlib import Path


def valid_year(year):
  if isinstance(year, bool):
    return False
  if isinstance(year, int):
    return True
  if isinstance(year, str) and year.isdigit():
    return True
  return False


path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))

for item in data:
  issued = item.get("issued")
  if not issued:
    continue
  try:
    year = issued["date-parts"][0][0]
  except (KeyError, IndexError, TypeError):
    item.pop("issued", None)
    continue
  if not valid_year(year):
    item.pop("issued", None)
    continue
  if isinstance(year, str):
    item["issued"]["date-parts"][0][0] = int(year)

path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
PY

echo "Generating export markdown..."
EXPORT_MD="$(python "$SCRIPT_DIR/generate_export_md.py" "$CSL_JSON_NAME" --style "$STYLE_NAME")"

echo "Generating PDF..."
pandoc "$EXPORT_MD" \
  --citeproc \
  --pdf-engine=xelatex \
  -V mainfont="Times New Roman" \
  -V CJKmainfont="PingFang SC" \
  -o "$OUT_DIR/${OUTPUT_STEM}.pdf"

echo "Generating Word..."
pandoc "$EXPORT_MD" \
  --citeproc \
  -o "$OUT_DIR/${OUTPUT_STEM}.docx"

echo "Done."
echo "Markdown: $EXPORT_MD"
echo "PDF: $OUT_DIR/${OUTPUT_STEM}.pdf"
echo "Word: $OUT_DIR/${OUTPUT_STEM}.docx"