import lark_oapi as lark
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from typing import Dict, Any
import requests


app_id = "cli_a925122983799cd5"  # 应用唯一标识，创建应用后获得。有关app_id 的详细介绍。请参考通用参数https://open.feishu.cn/document/ukTMukTMukTM/uYTM5UjL2ETO14iNxkTN/terminology。
app_secret = "tXSg54dSRqZ0gtfCnpbRYgOAc5torHf5"  # 应用秘钥，创建应用后获得。有关 app_secret 的详细介绍，请参考https://open.feishu.cn/document/ukTMukTMukTM/uYTM5UjL2ETO14iNxkTN/terminology。

REPO_DIR = Path(__file__).resolve().parents[2]
PIPELINE_DIR = REPO_DIR / "get_paper_records" / "python"
FILE_OUTPUT_DIR = REPO_DIR / "get_paper_records" / "file_output"
AWARDS_DIR = REPO_DIR / "get_paper_records" / "awards"
PIPELINE_TIMEOUT_SECONDS = 60000
PROGRESS_NOTIFY_INTERVAL_SECONDS = 60

VALID_TABLE_NAMES = ["会议投稿", "会议成果", "期刊投稿", "期刊成果", "竞赛汇总"]
VALID_STYLES = ["ieee", "acm", "apa", "mla", "chicago", "nature"]
MESSAGE_DEDUP_TTL_SECONDS = 24 * 60 * 60
processed_message_ids: dict[str, float] = {}
processed_message_ids_lock = threading.Lock()


def build_subprocess_env() -> dict[str, str]:
    """为 pipeline 构造更稳定的子进程环境。

    机器人进程启动时的 PATH 可能与用户终端不同，这里显式补入常见的
    Python、pandoc、TeX 路径，避免 pipeline 中找不到 python/pandoc/xelatex。
    """
    env = os.environ.copy()
    path_entries = env.get("PATH", "").split(os.pathsep) if env.get("PATH") else []

    candidate_dirs = [
        str(Path(sys.executable).resolve().parent),
        "/opt/anaconda3/bin",
        "/Library/TeX/texbin",
        "/usr/local/bin",
        "/opt/homebrew/bin",
    ]

    for directory in candidate_dirs:
        if directory and directory not in path_entries and Path(directory).exists():
            path_entries.append(directory)

    env["PATH"] = os.pathsep.join(path_entries)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def mark_message_if_new(message_id: str) -> bool:
    """为消息做幂等去重。

    飞书文档说明接收消息事件可能会重复推送，因此这里使用 message_id
    做去重；同一 message_id 只处理一次。
    """
    now = time.time()
    expired_before = now - MESSAGE_DEDUP_TTL_SECONDS

    with processed_message_ids_lock:
        expired_ids = [mid for mid, ts in processed_message_ids.items() if ts < expired_before]
        for mid in expired_ids:
            processed_message_ids.pop(mid, None)

        if message_id in processed_message_ids:
            return False

        processed_message_ids[message_id] = now
        return True

def get_tenant_access_token(app_id: str, app_secret: str) -> tuple[str, Exception]:
    """获取 tenant_access_token

    Args:
        app_id: 应用ID
        app_secret: 应用密钥

    Returns:
        Tuple[str, Exception]: (access_token, error)
    """
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    try:
        print(f"POST: {url}")
        print(f"Request body: {json.dumps(payload)}")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        print(f"Response: {json.dumps(result)}")

        if result.get("code", 0) != 0:
            error_msg = f"failed to get tenant_access_token: {result.get('msg', 'unknown error')}"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            return "", Exception(error_msg)

        return result["tenant_access_token"], None

    except Exception as e:
        error_msg = f"getting tenant_access_token error: {str(e)}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"ERROR Response: {e.response.text}", file=sys.stderr)
        return "", e

def upload_file_to_feishu(tenant_access_token: str, file_path: str, file_name: str, file_type: str) -> str:
    """上传文件到飞书

    Args:
        tenant_access_token: 租户访问令牌
        file_path: 本地文件路径
        file_name: 文件名
        file_type: 文件类型（pdf/docx/text）

    Returns:
        str: 文件的file_key
    """
    # 根据文件类型设置type参数
    type_map = {
        "pdf": "pdf",
        "docx": "doc",
        "txt": "stream"
    }
    file_type_param = type_map.get(file_type.lower(), "stream")
    
    url = f"https://open.feishu.cn/open-apis/im/v1/files"
    headers = {
        "Authorization": f"Bearer {tenant_access_token}"
    }
    
    try:
        with open(file_path, 'rb') as f:
            files = {
                'file': (file_name, f, 'application/octet-stream')
            }
            data = {
                'file_type': file_type_param,
                'file_name': file_name
            }
            
            print(f"Uploading file: {file_name} to {url}")
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            print(f"Upload response: {json.dumps(result)}")
            
            if result.get("code", 0) != 0:
                error_msg = f"failed to upload file: {result.get('msg', 'unknown error')}"
                print(f"ERROR: {error_msg}", file=sys.stderr)
                raise Exception(error_msg)
            
            return result["data"]["file_key"]
            
    except Exception as e:
        error_msg = f"upload file error: {str(e)}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        raise

def send_file_message(tenant_access_token: str, receive_id: str, receive_id_type: str, file_key: str) -> Dict[str, Any]:
    """发送文件消息

    Args:
        tenant_access_token: 租户访问令牌
        receive_id: 接收者ID
        receive_id_type: 接收者ID类型（open_id/chat_id等）
        file_key: 文件key

    Returns:
        Dict[str, Any]: 发送结果
    """
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {
        "receive_id_type": receive_id_type
    }
    headers = {
        "Authorization": f"Bearer {tenant_access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    # 构建文件消息内容
    content = {
        "file_key": file_key
    }
    
    payload = {
        "receive_id": receive_id,
        "content": json.dumps(content),
        "msg_type": "file"
    }
    
    try:
        print(f"POST: {url}")
        print(f"Params: {params}")
        print(f"Request body: {json.dumps(payload)}")
        
        response = requests.post(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"Response: {json.dumps(result)}")
        
        if result.get("code", 0) != 0:
            error_msg = f"failed to send file message: {result.get('msg', 'unknown error')}"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            raise Exception(error_msg)
            
        return result
        
    except Exception as e:
        error_msg = f"send file message error: {str(e)}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"ERROR Response: {e.response.text}", file=sys.stderr)
        raise

def send_text_message(tenant_access_token: str, chat_id: str, text: str) -> None:
    """发送文本消息。"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {
        "receive_id_type": "chat_id"
    }
    headers = {
        "Authorization": f"Bearer {tenant_access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "receive_id": chat_id,
        "content": json.dumps({"text": text}, ensure_ascii=False),
        "msg_type": "text"
    }

    response = requests.post(url, params=params, headers=headers, json=payload)
    response.raise_for_status()

    result = response.json()
    if result.get("code", 0) != 0:
        raise Exception(f"failed to send text message: {result.get('msg', 'unknown error')}")


def parse_user_request(parameter: str) -> tuple[str, str]:
    """从用户文本中提取表名和样式。

    支持示例：
    - 会议成果
    - 会议成果 acm
    - 表名=会议成果 样式=apa
    - 请导出会议投稿，样式 ieee
    """
    text = parameter.strip()
    if not text:
        raise ValueError("消息内容为空")

    table_name = next((name for name in VALID_TABLE_NAMES if name in text), None)
    if not table_name:
        raise ValueError(
            "未识别到有效表名。可选值：会议投稿、会议成果、期刊投稿、期刊成果、竞赛汇总"
        )

    style_name = "ieee"
    style_match = re.search(r"(?:样式|style)\s*[:=：]?\s*(ieee|acm|apa|mla|chicago|nature)", text, re.IGNORECASE)
    if style_match:
        style_name = style_match.group(1).lower()
    else:
        # 大写也支持
        lowered = text.lower()
        for candidate in VALID_STYLES:
            if candidate in lowered:
                style_name = candidate
                break

    return table_name, style_name


def run_export_pipeline(table_name: str, style_name: str) -> list[tuple[Path, str]]:
    """执行成果导出 pipeline，并返回要发送的文件列表。"""
    command = ["bash", "pipeline.sh", table_name, style_name]
    print(f"Running pipeline command: {command} in {PIPELINE_DIR}")

    result = subprocess.run(
        command,
        cwd=str(PIPELINE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=build_subprocess_env(),
        timeout=PIPELINE_TIMEOUT_SECONDS,
        check=False,
    )

    if result.stdout:
        print(f"Pipeline stdout:\n{result.stdout}")
    if result.stderr:
        print(f"Pipeline stderr:\n{result.stderr}", file=sys.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"pipeline 执行失败，退出码: {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    if table_name == "竞赛汇总":
        files = [
            (AWARDS_DIR / "awards_cn.txt", "txt"),
            (AWARDS_DIR / "awards_en.txt", "txt"),
        ]
    else:
        stem = f"{table_name}_mp_records_csl_{style_name}"
        files = [
            (FILE_OUTPUT_DIR / f"{stem}.pdf", "pdf"),
            (FILE_OUTPUT_DIR / f"{stem}.docx", "docx"),
        ]

    missing_files = [str(path) for path, _ in files if not path.exists()]
    if missing_files:
        raise FileNotFoundError(f"pipeline 已执行，但未找到输出文件: {', '.join(missing_files)}")

    return files


def send_progress_updates(
    tenant_access_token: str,
    chat_id: str,
    table_name: str,
    style_name: str,
    stop_event: threading.Event,
) -> None:
    """在后台任务执行期间定期发送进度提示。"""
    while not stop_event.wait(PROGRESS_NOTIFY_INTERVAL_SECONDS):
        try:
            if table_name == "竞赛汇总":
                text = f"任务仍在处理中：{table_name}，请稍候"
            else:
                text = f"任务仍在处理中：{table_name}，引用样式 {style_name}，等待时间约为5-10分钟，请稍候"
            send_text_message(tenant_access_token, chat_id, text)
        except Exception as e:
            print(f"Error sending progress notification: {e}", file=sys.stderr)


def process_export_request(tenant_access_token: str, chat_id: str, table_name: str, style_name: str) -> None:
    """在后台线程中执行导出请求并回传文件。"""
    progress_stop_event = threading.Event()
    progress_worker = threading.Thread(
        target=send_progress_updates,
        args=(tenant_access_token, chat_id, table_name, style_name, progress_stop_event),
        daemon=True,
        name=f"progress-{chat_id}",
    )
    progress_worker.start()

    try:
        generated_files = run_export_pipeline(table_name, style_name)

        for file_path, file_type in generated_files:
            file_key = upload_file_to_feishu(tenant_access_token, str(file_path), file_path.name, file_type)
            send_file_message(tenant_access_token, chat_id, "chat_id", file_key)

        send_text_message(tenant_access_token, chat_id, "处理完成，请查收文件")

        print(f"Successfully sent files to chat: {chat_id}")

    except Exception as e:
        print(f"Error running pipeline or sending files: {e}", file=sys.stderr)
        try:
            tenant_access_token, err = get_tenant_access_token(app_id, app_secret)
            if not err:
                send_error_message(tenant_access_token, chat_id, "导出失败，请检查表名或样式，稍后重试")
        except Exception as notify_err:
            print(f"Error sending failure notification: {notify_err}", file=sys.stderr)
    finally:
        progress_stop_event.set()

def do_p2_im_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """处理接收消息事件
    
    Args:
        data: 消息事件数据
    """
    print(f'[ do_p2_im_message_receive_v1 access ], data: {lark.JSON.marshal(data, indent=4)}')
    
    try:
        # 获取消息内容
        message = data.event.message
        if not message:
            print("No message in event", file=sys.stderr)
            return
            
        # 只处理文本消息
        if message.message_type != "text":
            print(f"Ignore non-text message type: {message.message_type}")
            return

        message_id = message.message_id
        if not message_id:
            print("No message_id in event", file=sys.stderr)
            return

        if not mark_message_if_new(message_id):
            print(f"Skip duplicated message: {message_id}")
            return
            
        # 解析消息内容
        content = json.loads(message.content)
        text = content.get("text", "").strip()
        
        # 根据飞书事件结构，sender 位于 event 下，而不是 message 下。
        sender = data.event.sender
        if not sender or not sender.sender_id:
            print("No sender information in event", file=sys.stderr)
            return

        sender_id = sender.sender_id
        chat_id = message.chat_id

        sender_open_id = getattr(sender_id, "open_id", "unknown_open_id")
        print(f"Received message from {sender_open_id}: {text}")

        # 解析用户请求并执行成果导出 pipeline
        try:
            table_name, style_name = parse_user_request(text)
        except Exception as e:
            print(f"Error parsing request: {e}", file=sys.stderr)
            tenant_access_token, err = get_tenant_access_token(app_id, app_secret)
            if err:
                print(f"Error getting tenant_access_token: {err}", file=sys.stderr)
                return
            send_error_message(
                tenant_access_token,
                chat_id,
                "参数格式错误。示例：会议成果 acm；或 表名=会议投稿 样式=ieee"
            )
            return

        tenant_access_token, err = get_tenant_access_token(app_id, app_secret)
        if err:
            print(f"Error getting tenant_access_token: {err}", file=sys.stderr)
            return

        send_text_message(tenant_access_token, chat_id, "任务已接收，正在后台处理，引用格式导出任务等待时间可能较久，请稍候...")

        worker = threading.Thread(
            target=process_export_request,
            args=(tenant_access_token, chat_id, table_name, style_name),
            daemon=True,
            name=f"export-{message_id}",
        )
        worker.start()
        print(f"Started background worker {worker.name} for message: {message_id}")
                
    except Exception as e:
        print(f"Error processing message event: {e}", file=sys.stderr)

def send_error_message(tenant_access_token: str, chat_id: str, error_text: str) -> None:
    """发送错误消息
    
    Args:
        tenant_access_token: 租户访问令牌
        chat_id: 会话ID
        error_text: 错误文本
    """
    try:
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {
            "receive_id_type": "chat_id"
        }
        headers = {
            "Authorization": f"Bearer {tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        send_text_message(tenant_access_token, chat_id, error_text)
            
    except Exception as e:
        print(f"ERROR: send error message failed: {e}", file=sys.stderr)

# 注册事件处理器
event_handler = lark.EventDispatcherHandler.builder(app_id, app_secret) \
    .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1) \
    .build()

def main():
    """主函数"""
    print("Starting Feishu bot...")
    cli = lark.ws.Client(app_id, app_secret,
                         event_handler=event_handler, log_level=lark.LogLevel.DEBUG)
    cli.start()

if __name__ == "__main__":
    main()