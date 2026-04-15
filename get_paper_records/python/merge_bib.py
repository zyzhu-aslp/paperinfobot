
import re
import argparse
from pathlib import Path


def parse_bib_file(file_path):
    """解析 .bib 文件，返回条目字符串列表。"""
    content = Path(file_path).read_text(encoding="utf-8")
    raw_entries = re.split(r'\n\s*(?=@\w+{)', content)
    return [entry.strip() for entry in raw_entries if entry.strip()]


def extract_time_from_entry(entry_text):
    """
    从 BibTeX 条目里提取 time 字段（YYYY-MM-DD）用于排序。
    若无 time 字段，则降级使用 year。
    返回可直接比较的字符串：有 time 返回 "YYYY-MM-DD"，仅有 year 返回 "YYYY-00-00"，
    都没有返回 "0000-00-00"（排到最后）。
    """
    m = re.search(r'time\s*=\s*\{(\d{4}-\d{2}-\d{2})\}', entry_text)
    if m:
        return m.group(1)

    m = re.search(r'year\s*=\s*[{"]?(\d{4})', entry_text)
    if m:
        return f"{m.group(1)}-00-00"

    return "0000-00-00"


def main():
    parser = argparse.ArgumentParser(description="Merge and sort BibTeX files.")
    parser.add_argument('--inputs', nargs='+', default=["../bibtex/会议成果.bib", "../bibtex/期刊成果.bib"], help="List of input .bib files.")
    parser.add_argument('--output', default="../bibtex/成果.bib", help="Path to the output merged .bib file.")
    args = parser.parse_args()

    all_items = []
    for input_file in args.inputs:
        try:
            entries = parse_bib_file(input_file)
            for entry in entries:
                sort_key = extract_time_from_entry(entry)
                # 清除已有的 selected 字段，后面重新按排名添加
                cleaned_entry = re.sub(r'\s*selected\s*=\s*\{.*?\},?\s*\n', '', entry, flags=re.IGNORECASE)
                all_items.append({'sort_key': sort_key, 'entry': cleaned_entry})
        except FileNotFoundError:
            print(f"Warning: Input file not found: {input_file}")

    # 按 time (YYYY-MM-DD) 降序排列
    all_items.sort(key=lambda x: x['sort_key'], reverse=True)

    final_bib_entries = []
    for i, item in enumerate(all_items):
        entry_text = item['entry']
        
        # Find the position of the last closing brace
        last_brace_pos = entry_text.rfind('}')
        if last_brace_pos == -1:
            final_bib_entries.append(entry_text) # Append as is if malformed
            continue

        core_content = entry_text[:last_brace_pos].strip()

        # Ensure the last real field has a comma
        if core_content and not core_content.endswith(','):
            core_content += ','

        if i < 20:
            # Add the 'selected' field for the top 20
            modified_entry = core_content + "\n  selected     = {true}\n}"
        else:
            modified_entry = core_content + "\n}"
        
        # Clean up any double commas that might have been created
        modified_entry = modified_entry.replace(',,', ',')
        final_bib_entries.append(modified_entry)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(final_bib_entries), encoding="utf-8")

    print(f"Successfully merged {len(all_items)} entries into {output_path.resolve()}")

if __name__ == "__main__":
    main()
