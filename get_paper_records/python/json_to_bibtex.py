
import json
import re
import argparse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
import time

def fetch_arxiv_abstract(arxiv_id: str) -> str:
    """Fetch abstract from ArXiv API."""
    if not arxiv_id:
        return ""
    match = re.search(r'(\d{4}\.\d{5,})(v\d+)?', arxiv_id)
    if not match:
        return ""
    core_id = match.group(1)

    url = f"http://export.arxiv.org/api/query?id_list={core_id}"
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
            root = ET.fromstring(data)
            namespace = {"arxiv": "http://www.w3.org/2005/Atom"}
            summary = root.find("arxiv:entry/arxiv:summary", namespace)
            if summary is not None:
                return summary.text.strip().replace("\n", " ")
    except urllib.error.HTTPError as e:
        # Specifically handle HTTP 429 Too Many Requests
        if e.code == 429:
            print(f"Rate limit hit for {arxiv_id}. Waiting and retrying...")
            time.sleep(2) # Wait 5 seconds before retrying
            return fetch_arxiv_abstract(arxiv_id) # Retry the request
        print(f"Failed to fetch abstract for {arxiv_id}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred for {arxiv_id}: {e}")
    return ""

def generate_bibtex_key(author: str, year: str, title: str) -> str:
    """Generate a BibTeX key from author, year, and title."""
    if not author or not year or not title or year == "YYYY":
        return "UnknownKey"
    first_author_surname = author.split(",")[0].strip().split(" ")[-1]
    year_part = year.strip()
    title_first_word = re.sub(r"[^a-zA-Z]", "", title.split(" ")[0]).lower()
    return f"{first_author_surname}{year_part}{title_first_word}"

def format_authors(authors_list):
    """Format authors from list to 'Last, First and ...' string."""
    if not authors_list or not isinstance(authors_list, list):
        return ""
    
    author_text = authors_list[0].get("text", "")
    authors = [a.strip() for a in author_text.split(',')]
    formatted_authors = []
    for author_group in authors:
        names = author_group.split(' and ')
        for name in names:
            name = name.strip()
            parts = name.split()
            if len(parts) >= 2:
                first_name = " ".join(parts[:-1])
                last_name = parts[-1]
                formatted_authors.append(f"{last_name}, {first_name}")
            elif name:
                formatted_authors.append(name)
    return " and ".join(formatted_authors)

def get_field_value(field):
    """Extracts the value from a potentially complex field."""
    if not field:
        return ""
    if isinstance(field, str):
        return field.strip()
    if isinstance(field, list) and field:
        if isinstance(field[0], (str, int, float)):
            return str(field[0]).strip()
        if isinstance(field[0], dict):
            return field[0].get('text', '').strip()
    if isinstance(field, dict):
        return field.get('link', field.get('text', '')).strip()
    return str(field).strip()

def extract_year(fields: dict) -> str:
    """Extract year from multiple possible fields."""
    year_val = get_field_value(fields.get("年份"))
    if year_val and year_val.isdigit() and len(year_val) == 4:
        return year_val

    search_fields = ["DOI", "EI 检索号", " EI 检索号", "论文avxiv链接"]
    for key in search_fields:
        value = get_field_value(fields.get(key))
        if value:
            match = re.search(r'(19|20)\d{2}', value)
            if match:
                return match.group(0)
    
    return "YYYY"


# ── 英文月份名 -> 数字 ──────────────────────────────────────────
_MONTH_NAME_TO_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _parse_conference_time(fields: dict) -> str:
    """
    会议成果：用「年份」+「会议时间」起始日期拼出 YYYY-MM-DD。

    会议时间样例（不含年份）：
      "12月2日-5日"  "2月23日-3月2日"  "4 月 24 日–28 日"
    取范围的起始月+起始日，与年份合并。
    """
    year_raw = fields.get("年份")
    if isinstance(year_raw, list) and year_raw:
        year = int(year_raw[0])
    elif isinstance(year_raw, (int, float)):
        year = int(year_raw)
    else:
        year_str = get_field_value(year_raw)
        if year_str and year_str.isdigit():
            year = int(year_str)
        else:
            return ""

    meeting_text = get_field_value(fields.get("会议时间"))
    if not meeting_text:
        return f"{year:04d}-01-01"

    # 匹配起始月和起始日：「X月Y日」允许数字和"月/日"之间有空格
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日', meeting_text)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        return f"{year:04d}-{month:02d}-{day:02d}"

    return f"{year:04d}-01-01"


def _parse_journal_time(fields: dict) -> str:
    """
    期刊成果：解析「发表时间」字段为 YYYY-MM-DD。

    常见格式：
      "23 July 2024"          -> 2024-07-23
      "June 2022"             -> 2022-06-01  （无日，默认 01）
      "2024-09"               -> 2024-09-01  （无日，默认 01）
      " 09 August 2024"       -> 2024-08-09  （前后有空格）
      "January  2018"         -> 2018-01-01  （多余空格）
    """
    raw = (fields.get("发表时间") or "").strip()
    if not raw:
        return ""

    # 格式 1：YYYY-MM（如 "2024-09"）
    m = re.match(r'^(\d{4})-(\d{1,2})$', raw)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-01"

    # 格式 2：DD Month YYYY（如 "23 July 2024"）
    m = re.match(r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$', raw)
    if m:
        day = int(m.group(1))
        month = _MONTH_NAME_TO_NUM.get(m.group(2).lower(), 0)
        year = int(m.group(3))
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # 格式 3：Month YYYY（如 "June 2022"）
    m = re.match(r'^([A-Za-z]+)\s+(\d{4})$', raw)
    if m:
        month = _MONTH_NAME_TO_NUM.get(m.group(1).lower(), 0)
        year = int(m.group(2))
        if month:
            return f"{year:04d}-{month:02d}-01"

    # 兜底：尝试从字符串里提取四位年份
    m = re.search(r'(19|20)\d{2}', raw)
    if m:
        return f"{m.group(0)}-01-01"

    return ""

def main():
    parser = argparse.ArgumentParser(description="Convert JSON records to BibTeX format.")
    # parser.add_argument("-input_json", default="../record/会议成果_mp_records.json", help="Path to the input JSON file.")
    # parser.add_argument("-output_bib", default="../bibtex/会议成果.bib", help="Path to the output BibTeX file.")
    # parser.add_argument("--type", choices=['journal', 'conference'], default='conference', help="Type of the publication.")
    parser.add_argument("-input_json", default="../record/期刊成果_mp_records.json", help="Path to the input JSON file.")
    parser.add_argument("-output_bib", default="../bibtex/期刊成果.bib", help="Path to the output BibTeX file.")
    parser.add_argument("--type", choices=['journal', 'conference'], default='journal', help="Type of the publication.")
    args = parser.parse_args()

    with open(args.input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("data", {}).get("items", [])
    items.sort(key=lambda item: extract_year(item.get("fields", {})), reverse=True)

    bibtex_entries = []
    valid_entries_count = 0
    for item in items:
        fields = item.get("fields", {})
        
        title = get_field_value(fields.get("投稿信息")) or get_field_value(fields.get("论文名称"))
        authors = format_authors(fields.get("作者列表"))
        year = extract_year(fields)

        pub_type = 'booktitle' if args.type == 'conference' else 'journal'
        pub_title_key = "会议简称" if args.type == 'conference' else "期刊名称"
        publication_title = get_field_value(fields.get(pub_title_key))

        if not all([title, authors, year != "YYYY", publication_title]):
            continue

        key = generate_bibtex_key(authors, year, title)
        
        # 根据成果类型选择 BibTeX 条目类型：
        # - 会议：@inproceedings
        # - 期刊：@article
        entry_type = "inproceedings" if args.type == "conference" else "article"
        entry = [f"@{entry_type}{{{key},"]
        entry.append(f"  title        = {{{title}}},")
        entry.append(f"  author       = {{{authors}}},")
        entry.append(f"  {pub_type:<12} = {{{publication_title}}},")
        entry.append(f"  year         = {{{year}}},")

        # 生成精确到日的 time 字段，供合并排序使用
        if args.type == 'conference':
            time_val = _parse_conference_time(fields)
        else:
            time_val = _parse_journal_time(fields)
        if time_val:
            entry.append(f"  time         = {{{time_val}}},")

        # --- Optional fields ---
        map_key = "conference" if args.type == 'conference' else "journal"
        optional_fields_map = {
            "journal": {
                "abbr": "期刊简称", "code": "开源项目链接", "demo": "DEMO页面链接",
                "website": "公众号链接", "video": "视频链接", "slides": "Slides 链接", "poster": "Poster 链接",
                "award": "奖项", "award_name": "自定义奖项", "arxiv": "论文avxiv链接"
            },
            "conference": {
                "abbr": "会议简称", "code": "开源项目链接", "demo": "DEMO页面链接",
                "website": "公众号链接", "video": "视频链接", "slides": "Slides 链接", "poster": "Poster 链接",
                "award": "论文奖项", "award_name": "自定义奖项", "arxiv": "论文avxiv链接"
            }
        }

        for bib_key, json_key in optional_fields_map[map_key].items():
            value = get_field_value(fields.get(json_key))
            if value:
                if bib_key == 'arxiv':
                    arxiv_id_match = re.search(r'(\d{4}\.\d{5,})', value)
                    if arxiv_id_match:
                        arxiv_id = arxiv_id_match.group(1)
                        entry.append(f"  arxiv        = {{{arxiv_id}}},")
                        abstract = fetch_arxiv_abstract(arxiv_id)
                        if abstract:
                            entry.append(f"  abstract     = {{{abstract}}},")
                        time.sleep(0.5) # Add a 1-second delay after each API call
                else:
                    entry.append(f"  {bib_key:<12} = {{{value}}},")

        if fields.get("显示Bib"):
            entry.append(f"  bibtex_show  = {{true}},")
        
        if valid_entries_count < 20:
            entry.append(f"  selected     = {{true}},")
        
        preview_list = fields.get("预览图")
        if preview_list and isinstance(preview_list, list):
            preview_file = preview_list[0].get('name')
            if preview_file:
                entry.append(f"  preview      = {{{preview_file}}},")

        if entry[-1].endswith(','):
            entry[-1] = entry[-1][:-1]

        entry.append("}")
        bibtex_entries.append("\n".join(entry))
        valid_entries_count += 1

    output_path = Path(args.output_bib)
    output_path.write_text("\n\n".join(bibtex_entries), encoding="utf-8")
    
    print(f"Successfully converted {len(bibtex_entries)} entries to {output_path.resolve()}")

if __name__ == "__main__":
    main()
