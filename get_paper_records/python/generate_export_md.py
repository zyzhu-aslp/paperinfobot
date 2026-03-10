import argparse
from pathlib import Path


STYLE_MAP = {
  "ieee": "ieee.csl",
  "acm": "acm-sig-proceedings.csl",
  "apa": "apa.csl",
  "mla": "modern-language-association.csl",
  "chicago": "chicago-author-date.csl",
  "nature": "nature.csl",
}


def resolve_csl_file(repo_dir, style_name):
  style_key = style_name.lower()
  style_file_name = STYLE_MAP.get(style_key)
  if not style_file_name:
    supported = ", ".join(STYLE_MAP.keys())
    raise ValueError(f"不支持的样式类型: {style_name}。可选值: {supported}")

  csl_file = (repo_dir / "styles-master" / style_file_name).resolve()
  if not csl_file.exists():
    raise FileNotFoundError(f"未找到 CSL 样式文件: {csl_file}")

  return csl_file, style_key


def build_export_md(csl_json_name, style_name):
  script_dir = Path(__file__).resolve().parent
  project_dir = script_dir.parent
  repo_dir = project_dir.parent

  csl_json = (project_dir / "csl" / csl_json_name).resolve()
  if not csl_json.exists():
    raise FileNotFoundError(f"未找到 CSL JSON 文件: {csl_json}")

  csl_file, style_key = resolve_csl_file(repo_dir, style_name)

  export_dir = project_dir / "export_md"
  export_dir.mkdir(parents=True, exist_ok=True)
  export_md = export_dir / f"{csl_json.stem}_{style_key}_export.md"

  content = f"""---
title: 实验室论文成果
nocite: |
  @*
bibliography: {csl_json}
csl: {csl_file}
---

# Publications

::: {{#refs}}
:::
"""

  export_md.write_text(content, encoding="utf-8")
  print(export_md)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="根据 CSL JSON 生成 Pandoc 用的 Markdown 文件")
  parser.add_argument("csl_json_name", help="get_paper_records/csl 目录下的 CSL JSON 文件名")
  parser.add_argument(
    "--style",
    "-s",
    default="ieee",
    choices=sorted(STYLE_MAP.keys()),
    help="引用样式类型"
  )
  args = parser.parse_args()
  build_export_md(args.csl_json_name, args.style)