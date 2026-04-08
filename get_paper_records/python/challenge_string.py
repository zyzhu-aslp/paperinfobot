import json
import re
import argparse
from pathlib import Path


def split_lines(text: str):
    if not text:
        return []
    return [x.strip() for x in str(text).splitlines() if x.strip()]


def norm(s: str):
    return re.sub(r"\s+", "", s or "").lower()


def parse_awards(award_raw: str):
    """
    把名次/奖项字段解析为 [(label, award), ...]
    """
    text = " ".join(split_lines(award_raw))
    if not text:
        return []

    pattern = re.compile(
        r"((?:Track|Task)\s*\d*)\s*[:：]\s*(.+?)(?=\s+(?:Track|Task)\s*\d*\s*[:：]|$)",
        re.IGNORECASE,
    )
    pairs = [(m.group(1).strip(), m.group(2).strip()) for m in pattern.finditer(text)]
    if pairs:
        return pairs

    m = re.match(r"^\s*([^:：]+)\s*[:：]\s*(.+?)\s*$", text)
    if m:
        return [(m.group(1).strip(), m.group(2).strip())]
    return [(None, text.strip())]


def split_track_entries(text: str):
    lines = split_lines(text)
    if len(lines) > 1:
        return lines
    if not lines:
        return []
    one = lines[0]
    parts = re.split(r"(?=(?:Track|Task)\s*\d+\s*[:：])", one, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]
    return parts if len(parts) > 1 else lines


def pick_track(label, track_lines, idx, total_awards):
    if not track_lines:
        return "未注明"
    if label:
        nl = norm(label)
        for t in track_lines:
            if nl and nl in norm(t):
                return t
    if len(track_lines) == total_awards and idx < len(track_lines):
        return track_lines[idx]
    return track_lines[0]


def format_year(time_raw: str):
    t = (time_raw or "").strip()
    if not t:
        return "未知时间"
    m = re.search(r"(19|20)\d{2}", t)
    if m:
        return f"{m.group(0)}年"
    return t if "年" in t else f"{t}年"


def clean_track_name(text: str):
    s = (text or "").strip()
    if not s:
        return s
    # 去掉前缀标签，如 Track 1: / Task2：
    s = re.sub(r"^\s*(?:Track|Task)\s*\d*\s*[:：\-]?\s*", "", s, flags=re.IGNORECASE)
    # 去掉残留的 Track/Task 单词
    s = re.sub(r"\b(?:Track|Task)\b\s*\d*", "", s, flags=re.IGNORECASE)
    # 清理多余空白和标点
    s = re.sub(r"\s{2,}", " ", s).strip(" :-：")
    return s


def format_bilingual(en: str, cn: str, en_default: str, cn_default: str):
    en_v = (en or "").strip() or en_default
    cn_v = (cn or "").strip() or cn_default
    return f"{en_v}（{cn_v}）"


def num_to_cn(n: int):
    mapping = {
        1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
        6: "六", 7: "七", 8: "八", 9: "九", 10: "十"
    }
    return mapping.get(n, str(n))


def format_award_text(award: str):
    # 改为保留原始奖项/名次表达，仅做基础清理
    a = (award or "").strip().rstrip("。")
    return a or "未知奖项"


def is_unknown_track(en_track: str, cn_track: str) -> bool:
    en = (en_track or "").strip().lower()
    cn = (cn_track or "").strip().lower()

    unknown_tokens = {
        "", "unknown", "track unknown", "unavailable", "n/a", "none",
        "未注明", "未知", "无", "暂无"
    }

    # 两侧都属于“未知/未填写”时，视为赛道未注明，直接省略
    return en in unknown_tokens and cn in unknown_tokens


def first_non_empty(*vals):
    for v in vals:
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def format_year_token(time_raw: str):
    t = (time_raw or "").strip()
    if not t:
        return ""
    m = re.search(r"(19|20)\d{2}", t)
    return m.group(0) if m else t.replace("年", "").strip()


def format_pair(en: str, cn: str):
    en_v = (en or "").strip()
    cn_v = (cn or "").strip()
    if en_v and cn_v:
        return f"{en_v}（{cn_v}）"
    return en_v or cn_v


def extract_conf_name(fields: dict) -> str:
    """
    仅从 fields['绑定会议'][*]['text'] 提取会议名；
    没有则返回空字符串。
    """
    conf_list = fields.get("绑定会议") or []
    if not isinstance(conf_list, list):
        return ""

    for conf in conf_list:
        if not isinstance(conf, dict):
            continue
        text = str(conf.get("text") or "").strip()
        if text:
            return text
    return ""


def rank_to_cn(n: int) -> str:
    if n == 1:
        return "冠军"
    if n == 2:
        return "亚军"
    if n == 3:
        return "季军"
    return f"第{num_to_cn(n)}名"


def award_to_cn(award: str) -> str:
    a = (award or "").strip().rstrip("。.")

    # 英文名次 -> 中文
    def repl_en_rank(m):
        n = int(m.group(1))
        return rank_to_cn(n)

    a = re.sub(r"\b(\d+)(st|nd|rd|th)\b", repl_en_rank, a, flags=re.IGNORECASE)

    # 中文前三名统一为 冠亚季军
    a = a.replace("第一名", "冠军").replace("第二名", "亚军").replace("第三名", "季军")

    # 若仍有“第4名/第4”这类，统一成“第x名”
    def repl_cn_rank(m):
        raw = m.group(1)
        if raw.isdigit():
            return rank_to_cn(int(raw))
        # 已是中文数字时：一二三也转冠亚季，其余保留第x名
        cn_map = {"一": 1, "二": 2, "三": 3}
        if raw in cn_map:
            return rank_to_cn(cn_map[raw])
        return f"第{raw}名"

    a = re.sub(r"第\s*([0-9一二三四五六七八九十]+)\s*名?", repl_cn_rank, a)

    a = re.sub(r"\b(place|rank|ranking)\b", "", a, flags=re.IGNORECASE)
    a = re.sub(r"\s+", "", a)
    a = re.sub(r"(奖项|奖)$", "", a)

    return a or "未知名次"


def award_to_en(award: str) -> str:
    a = (award or "").strip().rstrip("。.")
    a = re.sub(r"\s+", " ", a)
    return a or "Unknown"


def is_unknown_text(s: str) -> bool:
    t = (s or "").strip().lower()
    return t in {"", "unknown", "track unknown", "unavailable", "n/a", "none", "未注明", "未知", "无", "暂无"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-input_json",
        default="/Users/zyzhu/folder/实验室成果管理系统/lark-samples-main/get_paper_records/竞赛汇总_mp_records.json",
        help="导出的 JSON 文件路径",
    )
    parser.add_argument(
        "-output_cn",
        default="../awards_cn.txt",
        help="中文输出文件路径",
    )
    parser.add_argument(
        "-output_en",
        default="../awards_en.txt",
        help="英文输出文件路径",
    )
    args = parser.parse_args()

    with open(args.input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("data", {}).get("items", [])
    # 按时间倒序排序
    items.sort(
        key=lambda item: format_year_token(str(item.get("fields", {}).get("时间", ""))),
        reverse=True,
    )
    results_cn = []
    results_en = []

    for item in items:
        fields = item.get("fields", {})

        award_pairs = parse_awards(fields.get("名次/奖项", ""))
        if not award_pairs:
            continue

        year = format_year_token(str(fields.get("时间", "")))
        year_cn = f"{year}年" if year and not year.endswith("年") else year
        conf_name = extract_conf_name(fields)

        comp_cn = first_non_empty(fields.get("竞赛名称-中文"), "未知竞赛")
        comp_en = first_non_empty(fields.get("竞赛名称-英文"), "Unknown Challenge")

        track_lines_cn = split_track_entries(fields.get("赛道-中文") or "")
        track_lines_en = split_track_entries(fields.get("赛道-英文") or "")

        for i, (label, award) in enumerate(award_pairs):
            raw_track_cn = pick_track(label, track_lines_cn, i, len(award_pairs)).strip()
            raw_track_en = pick_track(label, track_lines_en, i, len(award_pairs)).strip()

            track_cn = clean_track_name(raw_track_cn)
            track_en = clean_track_name(raw_track_en)

            award_cn = award_to_cn(award)
            award_en = award_to_en(award)

            # 中文：比赛名+赛道名+名次之间不加空格
            cn_prefix = []
            if conf_name:
                cn_prefix.append(conf_name)
            if year_cn:
                cn_prefix.append(year_cn)

            track_cn_show = track_cn if not is_unknown_text(track_cn) else ""
            if track_cn_show:
                track_cn_show = track_cn_show if track_cn_show.endswith("赛道") else f"{track_cn_show}赛道"

            cn_core = f"{comp_cn}{track_cn_show}{award_cn}"
            cn_line = " ".join(cn_prefix + [cn_core]) if cn_prefix else cn_core
            results_cn.append(cn_line)

            # 英文：正常空格分隔
            en_parts = []
            if conf_name:
                en_parts.append(conf_name)
            if year:
                en_parts.append(year)
            en_parts.append(comp_en)

            track_en_show = track_en if not is_unknown_text(track_en) else ""
            if track_en_show:
                en_parts.append(track_en_show)

            en_parts.append(award_en)
            results_en.append(" ".join(en_parts))

    out_cn = Path(args.output_cn)
    out_en = Path(args.output_en)
    out_cn.write_text("\n".join(results_cn), encoding="utf-8")
    out_en.write_text("\n".join(results_en), encoding="utf-8")
    print(f"中文已导出 {len(results_cn)} 行到: {out_cn.resolve()}")
    print(f"英文已导出 {len(results_en)} 行到: {out_en.resolve()}")


if __name__ == "__main__":
    main()