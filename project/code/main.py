import lark_oapi as lark
import os
import sys
from typing import Dict, Any
import requests
import tempfile
import urllib.parse

# === input params start
app_id = os.getenv("APP_ID")        # app_id, required, 应用 ID
# 应用唯一标识，创建应用后获得。有关app_id 的详细介绍。请参考通用参数https://open.feishu.cn/document/ukTMukTMukTM/uYTM5UjL2ETO14iNxkTN/terminology。
app_secret = os.getenv("APP_SECRET")  # app_secret, required, 应用密钥
# 应用秘钥，创建应用后获得。有关 app_secret 的详细介绍，请参考https://open.feishu.cn/document/ukTMukTMukTM/uYTM5UjL2ETO14iNxkTN/terminology。
# === input params end

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

def generate_file_from_parameter(parameter: str) -> tuple[str, str, str]:
    """根据参数生成文件（需要用户自行实现）
    
    Args:
        parameter: 用户输入的参数字符串
        
    Returns:
        tuple[str, str, str]: (文件路径, 文件名, 文件类型)
        
    Note:
        此函数需要用户根据实际项目需求自行实现。
        参考文档中未提供此信息。
    """
    # 这里需要用户根据自己的项目实现文件生成功能
    # 示例：根据参数生成一个临时文件
    try:
        # 获取文件类型（从参数中解析或默认）
        file_type = "txt"  # 默认为txt，实际应根据需求调整
        if ".pdf" in parameter.lower():
            file_type = "pdf"
        elif ".docx" in parameter.lower():
            file_type = "docx"
            
        # 生成文件名
        file_name = f"generated_file_{hash(parameter)}.{file_type}"
        
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, file_name)
        
        # 写入文件内容（示例：将参数写入文件）
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Generated from parameter: {parameter}\n")
            f.write("This is a sample file content.\n")
            f.write("Please implement your own file generation logic.\n")
            
        print(f"Generated file: {file_path}")
        return file_path, file_name, file_type
        
    except Exception as e:
        error_msg = f"generate file error: {str(e)}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        raise

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
            
        # 解析消息内容
        content = json.loads(message.content)
        text = content.get("text", "").strip()
        
        # 获取发送者和会话信息
        sender_id = message.sender.sender_id
        chat_id = message.chat_id
        
        print(f"Received message from {sender_id.open_id}: {text}")
        
        # 获取 tenant_access_token
        tenant_access_token, err = get_tenant_access_token(app_id, app_secret)
        if err:
            print(f"Error getting tenant_access_token: {err}", file=sys.stderr)
            return
            
        # 生成文件（需要用户自行实现具体逻辑）
        try:
            file_path, file_name, file_type = generate_file_from_parameter(text)
        except Exception as e:
            print(f"Error generating file: {e}", file=sys.stderr)
            
            # 发送错误消息
            send_error_message(tenant_access_token, chat_id, "生成文件失败，请检查参数格式")
            return
            
        try:
            # 上传文件到飞书
            file_key = upload_file_to_feishu(tenant_access_token, file_path, file_name, file_type)
            
            # 发送文件消息
            send_file_message(tenant_access_token, chat_id, "chat_id", file_key)
            
            print(f"Successfully sent file to chat: {chat_id}")
            
        except Exception as e:
            print(f"Error sending file: {e}", file=sys.stderr)
            
            # 发送错误消息
            send_error_message(tenant_access_token, chat_id, "发送文件失败，请稍后重试")
            
        finally:
            # 清理临时文件
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Cleaned up temporary file: {file_path}")
            except Exception as cleanup_err:
                print(f"Warning: failed to cleanup temporary file: {cleanup_err}")
                
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
        
        content = {
            "text": error_text
        }
        
        payload = {
            "receive_id": chat_id,
            "content": json.dumps(content),
            "msg_type": "text"
        }
        
        print(f"Sending error message: {error_text}")
        response = requests.post(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if result.get("code", 0) != 0:
            print(f"ERROR: failed to send error message: {result.get('msg', 'unknown error')}", file=sys.stderr)
            
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