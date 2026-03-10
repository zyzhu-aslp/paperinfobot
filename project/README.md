# 飞书成果导出机器人

## 功能介绍

本项目是一个飞书企业自建应用机器人，已经接入 [get_paper_records/python/pipeline.sh](get_paper_records/python/pipeline.sh) 成果导出流程。用户在飞书中发送表名和引用样式后，机器人会自动执行导出，并将生成的 PDF、DOCX 或 TXT 文件回传到当前会话。

## 环境要求

- Python 3.7+
- 飞书开发者账号
- 企业自建应用权限
- `pandoc`
- `xelatex`

## 前置准备

### 1. 创建企业自建应用

1. 登录[飞书开发者后台](https://open.feishu.cn/app)
2. 创建**企业自建应用**，填写应用名称和描述
3. 在**测试企业和人员**页面创建测试企业并关联应用
4. 切换至应用的**测试版本**进行开发调试

### 2. 配置应用能力与权限

1. 在应用详情页的**应用能力**中添加**机器人**功能
2. 在**权限管理**页面开通以下权限：
   - `im:message.p2p_msg:readonly`：读取用户发给机器人的单聊消息
   - `im:message:send_as_bot`：以应用身份发送消息
   - `im:resource`：上传文件资源

### 3. 配置事件订阅

1. 在**开发配置 > 事件与回调**页面，配置**事件订阅**
2. 添加**接收消息事件**（`im.message.receive_v1`）
3. 选择**使用长连接接收事件**

## 安装与部署

### 安装依赖

```bash
pip install lark-oapi requests
```

### 本地运行

```bash
python main.py
```

### 生产环境部署

1. 将服务部署到可稳定运行 Python、pandoc、xelatex 的服务器
2. 配置服务器 IP 到飞书应用的 IP 白名单
3. 使用 systemd、supervisor 等进程管理工具托管服务
4. 确保服务进程的 `PATH` 中包含 Python、pandoc 和 xelatex

## 使用说明

### 用户使用流程

1. 在飞书中搜索机器人名称并发起单聊
2. 发送表名，或表名加样式
3. 等待机器人执行 pipeline 并返回文件

### 支持的表名

- `会议投稿`
- `会议成果`
- `期刊投稿`
- `期刊成果`
- `竞赛汇总`

### 支持的引用样式

- `ieee`
- `acm`
- `nature`

说明：

- 如果不传样式，默认使用 `ieee`
- 样式参数只对论文类表名生效
- `竞赛汇总` 返回的是 TXT 文件，不返回 PDF 或 DOCX

### 支持的消息格式

以下格式都可以：

```text
会议成果
会议成果 acm
表名=会议投稿 样式=apa
请导出期刊成果，样式 ieee
竞赛汇总
```

### 返回结果

- `会议投稿`、`会议成果`、`期刊投稿`、`期刊成果`：返回 2 个文件，分别是 PDF 和 DOCX
- `竞赛汇总`：返回 2 个文件，分别是中文 TXT 和英文 TXT

## 代码结构说明

### 主要功能模块

- `do_p2_im_message_receive_v1`：处理飞书消息事件
- `parse_user_request`：从用户文本中提取表名和样式
- `run_export_pipeline`：调用 `get_paper_records/python/pipeline.sh`
- `upload_file_to_feishu`：上传生成文件到飞书
- `send_file_message`：回传文件消息
- `send_text_message`：回传状态文本或错误提示

### 机器人与 pipeline 的关系

```text
飞书消息 -> 解析表名/样式 -> pipeline.sh -> 生成文件 -> 上传到飞书 -> 回传给用户
```

## 常见问题

### 1. 机器人无法接收消息

- 检查应用是否已发布且可用范围包含目标用户
- 确认事件订阅配置正确，长连接是否正常连接

### 2. 文件发送失败

- 检查文件大小是否超过限制（普通文件 ≤ 200MB）
- 确认 `im:resource` 权限已正确申请

### 3. 导出 pipeline 执行失败

- 检查 [get_paper_records/python/pipeline.sh](get_paper_records/python/pipeline.sh) 是否可在本地正常执行
- 检查 Python 环境中是否已安装 `requests`、`lark_oapi`
- 论文类流程还需要确保机器上已安装 `pandoc` 和 `xelatex`
- 若服务进程环境与登录 shell 不一致，需确认 `PATH` 是否包含 `/opt/anaconda3/bin` 与 `/Library/TeX/texbin`

### 4. 权限相关错误

- 检查应用权限是否已全部申请并通过审核
- 确认应用已发布到正式环境

## 相关文档

- [飞书开放平台文档](https://open.feishu.cn/document/home)
- [机器人能力介绍](https://go.feishu.cn/s/6dFbxHpwQ02)
- [消息发送接口](https://go.feishu.cn/s/61BYfgpwE01)
- [文件上传接口](https://go.feishu.cn/s/63soQp6Og0s)
- [get_paper_records/readme.md](get_paper_records/readme.md)

## 注意事项

- 开发环境建议使用测试企业，避免影响生产环境
- 处理大量并发请求时需注意飞书 API 的频控策略
- 机器人当前会同步执行 pipeline，单次导出时间较长时，用户需要等待几秒到几十秒
- 若后续并发量增加，建议将 pipeline 执行改为异步任务队列
