import argparse
import json
from pathlib import Path

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *


# SDK 使用说明: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-side-sdk/python--sdk/preparations-before-development
# 以下示例代码默认根据文档示例值填充，如果存在代码问题，请在 API 调试台填上相关必要参数后再复制代码使用

YOUR_APP_ID = "cli_a92951258938dbce"
YOUR_APP_SECRET = "BZHl00goIcwrFp8D2bzlefTSYun5IU0V"


def main(table_name):
    table_id_dict = {
        "会议投稿": "tbll47YBcaXU7pw4",
        "会议成果": "tbl0i3cUUApY0ugH",
        "期刊投稿": "tblcsuI4mEeUhy76",
        "期刊成果": "tblDCe9WTKLrQeps",
        "竞赛汇总": "tblS4UsF8J9I24NX"
    }

    if table_name not in table_id_dict:
        print("无效的表格名称，请输入以下选项之一：会议投稿、会议成果、期刊投稿、期刊成果、竞赛汇总")
        return

    table_id = table_id_dict[table_name]

    # 创建 client
    client = lark.Client.builder() \
        .app_id(YOUR_APP_ID) \
        .app_secret(YOUR_APP_SECRET) \
        .log_level(lark.LogLevel.INFO) \
        .build()

    all_items = []
    page_token = None

    while True:
        req_builder = ListAppTableRecordRequest.builder() \
            .app_token("FjJmws4FVi0nXmkwaEbc5iZdn8g") \
            .table_id(table_id) \
            .page_size(500)

        if page_token:
            req_builder = req_builder.page_token(page_token)

        request: ListAppTableRecordRequest = req_builder.build()

        # 发起请求
        response: ListAppTableRecordResponse = client.bitable.v1.app_table_record.list(request)

        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.bitable.v1.app_table_record.list failed, code: {response.code}, msg: {response.msg}, "
                f"log_id: {response.get_log_id()}, resp: \n"
                f"{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}"
            )
            return

        # 用 raw.content 解析，便于直接拿到 has_more/page_token/items
        raw_obj = json.loads(response.raw.content)
        data_obj = raw_obj.get("data", {})

        all_items.extend(data_obj.get("items", []))

        has_more = data_obj.get("has_more", False)
        page_token = data_obj.get("page_token")

        if not has_more or not page_token:
            break

    # 汇总输出
    output_obj = {
        "code": 0,
        "msg": "success",
        "data": {
            "items": all_items,
            "total": len(all_items),
            "has_more": False
        }
    }

    output_dir = Path("../record")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{table_name}_mp_records.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_obj, f, ensure_ascii=False, indent=4)

    lark.logger.info(f"共获取 {len(all_items)} 条记录，已写入文件: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="导出多维表格记录")
    parser.add_argument(
        "--table_name",
        "-tn",
        default="会议成果",
        choices=["会议投稿", "会议成果", "期刊投稿", "期刊成果", "竞赛汇总"],
        help="表格名称"
    )
    args = parser.parse_args()
    main(args.table_name)