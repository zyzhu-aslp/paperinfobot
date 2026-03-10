import argparse
import datetime
import json
from pathlib import Path

import requests

crossref_cache = {}


def build_issued(year):
    if isinstance(year, bool):
        return None
    if isinstance(year, int):
        return {"date-parts": [[year]]}
    if isinstance(year, str) and year.isdigit():
        return {"date-parts": [[int(year)]]}
    return None


# 对于缺失或格式错误的年份字段，直接删除，避免生成无效的 issued 字段导致后续处理出错。
def sanitize_csl_entry(csl):
    issued = csl.get("issued")
    if not issued:
        return csl

    try:
        year = issued["date-parts"][0][0]
    except (KeyError, IndexError, TypeError):
        csl.pop("issued", None)
        return csl

    if not build_issued(year):
        csl.pop("issued", None)

    return csl


# 判断是否需要调用 Crossref 补全，仅在关键字段缺失时才补全，避免每条记录都联网查询。
def needs_crossref_enrichment(csl):
    if not csl.get("DOI"):
        return True
    if not csl.get("author"):
        return True
    if not csl.get("container-title"):
        return True
    if not csl.get("issued"):
        return True
    return False



def query_crossref(doi=None, title=None):
    key = doi or title
    if key in crossref_cache:
        return crossref_cache[key]

    headers = {
        "User-Agent": "paper-metadata-bot (mailto:your_email@example.com)"
    }

    try:
        if doi:
            url = f"https://api.crossref.org/works/{doi}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                meta = r.json()["message"]
                crossref_cache[key] = meta
                return meta

        if title:
            url = "https://api.crossref.org/works"
            params = {"query.title": title, "rows": 1}
            r = requests.get(url, params=params, headers=headers, timeout=10)
            items = r.json()["message"]["items"]
            if items:
                meta = items[0]
                crossref_cache[key] = meta
                return meta
    except:
        pass

    return None

def enrich_from_crossref(csl, meta):

    # DOI
    if not csl.get("DOI") and "DOI" in meta:
        csl["DOI"] = meta["DOI"]

    # 期刊 / 会议
    if not csl.get("container-title") and "container-title" in meta:
        csl["container-title"] = meta["container-title"][0]

    # publisher
    if not csl.get("publisher") and "publisher" in meta:
        csl["publisher"] = meta["publisher"]

    # 类型
    if "type" in meta:
        csl["type"] = meta["type"]

    # 页码
    if "page" in meta and not csl.get("page"):
        csl["page"] = meta["page"]

    # volume
    if "volume" in meta and not csl.get("volume"):
        csl["volume"] = meta["volume"]

    # 年份
    if "issued" in meta and meta["issued"]["date-parts"]:
        year = meta["issued"]["date-parts"][0][0]
        issued = build_issued(year)
        if issued:
            csl["issued"] = issued

    # ⭐ 作者补全
    if (not csl.get("author") or len(csl["author"]) == 0) and "author" in meta:
        authors = []
        for a in meta["author"]:
            authors.append({
                "family": a.get("family", ""),
                "given": a.get("given", "")
            })
        csl["author"] = authors

    return csl

def safe_get_text(value):
    """
    统一解析各种飞书字段格式
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("text") or value.get("link") or ""
    if isinstance(value, list):
        if len(value) == 0:
            return ""
        v = value[0]
        if isinstance(v, dict):
            return v.get("text") or v.get("link") or ""
        return str(v)
    return ""


def parse_authors(author_field):
    """
    作者字符串 -> CSL author
    """
    text = safe_get_text(author_field)
    if text == "":
        return []

    authors = []
    for name in text.split(","):
        name = name.strip()
        parts = name.split()

        if len(parts) == 1:
            family = parts[0]
            given = ""
        else:
            family = parts[-1]
            given = " ".join(parts[:-1])

        authors.append({
            "family": family,
            "given": given
        })

    return authors


def parse_year(fields):
    time_fields = ["年份", "时间", "会议举办时间"]

    for key in time_fields:
        if key in fields:
            value = fields[key]
            if isinstance(value, list):
                value = value[0]

            try:
                year = datetime.datetime.fromtimestamp(value / 1000).year
                return year
            except:
                pass

    return ""


def get_title(fields):
    if "论文名称" in fields:
        return safe_get_text(fields["论文名称"])
    if "投稿信息" in fields:
        return safe_get_text(fields["投稿信息"])
    if "会议成果" in fields:
        return safe_get_text(fields["会议成果"])
    return ""


def get_container(fields):
    if "期刊名称" in fields:
        return safe_get_text(fields["期刊名称"])
    if "期刊全称" in fields:
        return safe_get_text(fields["期刊全称"])
    if "会议名称" in fields:
        return safe_get_text(fields["会议名称"])
    if "会议全称" in fields:
        return safe_get_text(fields["会议全称"])
    return ""


def get_type(fields):
    if "期刊名称" in fields or "期刊全称" in fields:
        return "article-journal"
    return "paper-conference"


def build_output_file(input_path):
    output_dir = Path("../csl")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{input_path.stem}_csl.json"


def convert(input_file):
    input_path = Path(input_file)
    output_file = build_output_file(input_path)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    output = []

    for item in data["data"]["items"]:
        fields = item["fields"]

        title = get_title(fields)
        year = parse_year(fields)
        container = get_container(fields)

        DOI = fields.get("DOI", "")
        if DOI:
            DOI = DOI.lower()

        URL = ""

        if "论文avxiv链接" in fields:
            URL = safe_get_text(fields["论文avxiv链接"])
        elif isinstance(fields.get("公众号链接"), dict):
            URL = fields["公众号链接"].get("link", "")
        elif isinstance(fields.get("公众号链接"), str):
            URL = fields["公众号链接"]

        page = fields.get("页码", "")
        volume = fields.get("卷号", "")

        # 先生成基础 CSL
        csl = {
            "DOI": DOI,
            "URL": URL,
            "author": parse_authors(fields.get("作者列表")),
            "container-title": container,
            "id": item["record_id"],
            "page": page,
            "publisher": "",
            "title": title,
            "title-short": title.split(":")[0] if title else "",
            "type": get_type(fields),
            "volume": volume
        }

        issued = build_issued(year)
        if issued:
            csl["issued"] = issued

        # 仅在关键字段缺失时才调用 Crossref 补全，避免每条记录都联网查询。
        if needs_crossref_enrichment(csl):
            crossref_meta = query_crossref(
                doi=DOI if DOI else None,
                title=title if not DOI else None
            )

            if crossref_meta:
                csl = enrich_from_crossref(csl, crossref_meta)

        csl = sanitize_csl_entry(csl)
        output.append(csl)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("CSL JSON 已生成:", output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将飞书导出的 JSON 转换为 CSL JSON")
    parser.add_argument("--input_file", "-i", default="../会议成果_mp_records.json", help="输入 JSON 文件路径")
    args = parser.parse_args()
    convert(args.input_file)