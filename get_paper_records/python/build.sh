#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ "$#" -lt 1 ]; then
  echo "用法: ./build.sh <csl_json文件名>"
  echo "示例: ./build.sh 会议成果_mp_records_csl.json"
  exit 1
fi

CSL_JSON_NAME="$1"
CSL_JSON_PATH="$PROJECT_DIR/csl/$CSL_JSON_NAME"

if [ ! -f "$CSL_JSON_PATH" ]; then
  echo "未找到文件: $CSL_JSON_PATH"
  exit 1
fi

OUT_DIR="$PROJECT_DIR/md_output"
mkdir -p "$OUT_DIR"

STEM="${CSL_JSON_NAME%.json}"

echo "Generating export markdown..."
EXPORT_MD="$(python "$SCRIPT_DIR/generate_export_md.py" "$CSL_JSON_NAME")"

echo "Generating PDF..."
pandoc "$EXPORT_MD" \
  --citeproc \
  --pdf-engine=xelatex \
  -V mainfont="Times New Roman" \
  -V CJKmainfont="PingFang SC" \
  -o "$OUT_DIR/${STEM}_ieee.pdf"

echo "Generating Word..."
pandoc "$EXPORT_MD" \
  --citeproc \
  -o "$OUT_DIR/${STEM}_ieee.docx"

echo "Done."
echo "Markdown: $EXPORT_MD"
echo "PDF: $OUT_DIR/${STEM}_ieee.pdf"
echo "Word: $OUT_DIR/${STEM}_ieee.docx"