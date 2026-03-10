import json
import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path


# 仅将“像时间戳”的数字转换，避免把“年份: 2024”误转
SEC_MIN = 946684800        # 2000-01-01 UTC
SEC_MAX = 4102444800       # 2100-01-01 UTC
MS_MIN = SEC_MIN * 1000
MS_MAX = SEC_MAX * 1000


def _to_number_if_numeric_string(value):
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return int(s)
    return value


def _is_unix_ts_seconds(x: float) -> bool:
    return SEC_MIN <= x <= SEC_MAX


def _is_unix_ts_milliseconds(x: float) -> bool:
    return MS_MIN <= x <= MS_MAX


def to_bj_time_str_if_timestamp(value):
    """
    若 value 是 Unix 秒/毫秒时间戳，则转北京时间字符串；否则原样返回。
    """
    if value is None:
        return value

    value = _to_number_if_numeric_string(value)
    if not isinstance(value, (int, float)):
        return value

    ts = float(value)
    if _is_unix_ts_milliseconds(ts):
        ts /= 1000.0
    elif not _is_unix_ts_seconds(ts):
        return value

    dt_bj = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(ZoneInfo("Asia/Shanghai"))
    # return dt_bj.strftime("%Y-%m-%d %H:%M:%S")
    return dt_bj.strftime("%Y-%m-%d")


def convert_all_timestamps(obj):
    """
    递归处理 dict/list，默认尝试转换所有字段值中的时间戳。
    """
    if isinstance(obj, dict):
        return {k: convert_all_timestamps(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_all_timestamps(x) for x in obj]
    return to_bj_time_str_if_timestamp(obj)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-input_json",
        # default="../期刊投稿_mp_records.json",
        default="../会议投稿_mp_records.json",
        help="输入 JSON 文件路径（将被原地覆盖）"
    )
    args = parser.parse_args()

    in_path = Path(args.input_json)

    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    converted = convert_all_timestamps(data)

    # 原地覆盖
    with in_path.open("w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, indent=4)

    print(f"转换完成（原地覆盖）：{in_path}")


if __name__ == "__main__":
    main()