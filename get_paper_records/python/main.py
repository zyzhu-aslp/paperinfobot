import json

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *
import os

from pathlib import Path


# SDK 使用说明: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-side-sdk/python--sdk/preparations-before-development
# 以下示例代码默认根据文档示例值填充，如果存在代码问题，请在 API 调试台填上相关必要参数后再复制代码使用

YOUR_APP_ID = "cli_a92951258938dbce"
YOUR_APP_SECRET = "BZHl00goIcwrFp8D2bzlefTSYun5IU0V"
# 复制该 Demo 后, 需要将 "YOUR_APP_ID", "YOUR_APP_SECRET" 替换为自己应用的 APP_ID, APP_SECRET.
def main():
    
    table_id_dict = {
        "会议投稿": "tbll47YBcaXU7pw4",
        "会议成果": "tbl0i3cUUApY0ugH",
        "期刊投稿": "tblcsuI4mEeUhy76",
        "期刊成果": "tblDCe9WTKLrQeps",
        "竞赛汇总": "tblS4UsF8J9I24NX"
    }
    
    input_table_name = input("请输入表格名称（会议投稿、会议成果、期刊投稿、期刊成果、竞赛汇总）: ")
    if input_table_name not in table_id_dict:
        print("无效的表格名称，请输入以下选项之一：会议投稿、会议成果、期刊投稿、期刊成果、竞赛汇总")
        return
    TABLE_ID = table_id_dict[input_table_name]
    
    # 创建client
    client = lark.Client.builder() \
        .app_id(YOUR_APP_ID) \
        .app_secret(YOUR_APP_SECRET) \
        .log_level(lark.LogLevel.INFO) \
        .build()

    # 构造请求对象
    request: ListAppTableRecordRequest = ListAppTableRecordRequest.builder() \
        .app_token("FjJmws4FVi0nXmkwaEbc5iZdn8g") \
        .table_id(TABLE_ID) \
        .page_size(500) \
        .build()

    # 发起请求
    response: ListAppTableRecordResponse = client.bitable.v1.app_table_record.list(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.bitable.v1.app_table_record.list failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return

    # 处理业务结果
    # lark.logger.info(lark.JSON.marshal(response.data, indent=4))

    # 将完整响应写入 JSON 文件
    output_file = Path("../") / f"{input_table_name}_records.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json.loads(response.raw.content), f, ensure_ascii=False, indent=4)

    lark.logger.info(f"响应已写入文件: {output_file}")


if __name__ == "__main__":
    main()