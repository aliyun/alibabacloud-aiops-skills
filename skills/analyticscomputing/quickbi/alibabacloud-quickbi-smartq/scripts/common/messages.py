# -*- coding: utf-8 -*-
"""Centralized bilingual message dictionary for quickbi-smartq-chat."""

from __future__ import annotations
from typing import Dict

# ═══════════════════════════════════════════════════════════════════
# Message dictionary: key -> {"zh_CN": "...", "en_US": "..."}
# ═══════════════════════════════════════════════════════════════════

MESSAGES: Dict[str, Dict[str, str]] = {

    # ── config_loader messages ─────────────────────────────────────
    "config_workdir_cli": {
        "zh_CN": "[配置] 工作目录: {work_dir} (来源=--workspace-dir 参数)",
        "en_US": "[Config] Working directory: {work_dir} (source=--workspace-dir parameter)",
    },
    "config_workdir_env": {
        "zh_CN": "[配置] 工作目录: {work_dir} (来源=WORKSPACE_DIR 环境变量)",
        "en_US": "[Config] Working directory: {work_dir} (source=WORKSPACE_DIR environment variable)",
    },
    "config_workdir_home": {
        "zh_CN": "[配置] 工作目录: {work_dir} (来源=HOME 兜底, --workspace-dir 和 WORKSPACE_DIR 均未设置)",
        "en_US": "[Config] Working directory: {work_dir} (source=HOME fallback, --workspace-dir and WORKSPACE_DIR are both unset)",
    },
    "config_default_path": {
        "zh_CN": "[配置] 包默认配置路径: {path} (exists={exists})",
        "en_US": "[Config] Package default configuration path: {path} (exists={exists})",
    },
    "config_skill_path": {
        "zh_CN": "[配置] 工作目录级配置路径: {path} (exists={exists})",
        "en_US": "[Config] Working-directory-level configuration path: {path} (exists={exists})",
    },
    "config_global_path": {
        "zh_CN": "[配置] 全局配置路径: {path} (exists={exists})",
        "en_US": "[Config] Global configuration path: {path} (exists={exists})",
    },
    "config_global_skip": {
        "zh_CN": "[配置] save_global_property 为 false，跳过全局配置读取 (path={path})",
        "en_US": "[Config] save_global_property is false; skipping global configuration read (path={path})",
    },
    "config_global_skip_write": {
        "zh_CN": "[配置] save_global_property 为 false，跳过全局配置写入: {key}",
        "en_US": "[Config] save_global_property is false; skipping global configuration write: {key}",
    },
    "config_workdir_missing": {
        "zh_CN": (
            "[配置错误] 工作目录未设置！--workspace-dir 参数和 WORKSPACE_DIR 环境变量均未提供。\n"
            "请通过 --workspace-dir 参数传入用户实际工作目录的绝对路径后重新执行脚本。\n"
            "示例: python script.py ... --workspace-dir '/path/to/workspace'"
        ),
        "en_US": (
            "[Config Error] Working directory not set! Neither --workspace-dir parameter nor WORKSPACE_DIR environment variable is provided.\n"
            "Please pass the absolute path of the user's actual working directory via --workspace-dir and re-run the script.\n"
            "Example: python script.py ... --workspace-dir '/path/to/workspace'"
        ),
    },
    "config_api_creds_detected": {
        "zh_CN": "[配置] 检测到全局配置或工作目录级配置已有 API 凭证，跳过试用凭证填充",
        "en_US": "[Config] Detected API credentials in global or working-directory-level configuration; skipping trial credential injection",
    },
    "config_env_access_token_required": {
        "zh_CN": "use_env_property 为 true 时，必须设置 ACCESS_TOKEN 环境变量",
        "en_US": "When use_env_property is true, the ACCESS_TOKEN environment variable must be set",
    },
    "config_env_access_token_parse_error": {
        "zh_CN": "ACCESS_TOKEN 解析失败：{exc}",
        "en_US": "Failed to parse ACCESS_TOKEN: {exc}",
    },
    "config_env_access_token_missing": {
        "zh_CN": "[config] use_env_property 已开启但未检测到 ACCESS_TOKEN 环境变量，回退使用其他配置层",
        "en_US": "[config] use_env_property is enabled but ACCESS_TOKEN not found, falling back to other config layers",
    },
    "config_trial_welcome": {
        "zh_CN": (
            "============================================================\n"
            "你的超级数据分析师已就绪！\n"
            "只需用自然语言提问，即可智能匹配并分析你的 Excel 文件或 Quick BI 数据集，\n"
            "瞬间发现数据洞察。复杂分析从未如此简单。\n\n"
            "检测到你尚未配置凭证，我们将为你自动注册试用凭证，开启试用期。\n\n"
            "试用到期后，请前往 Quick BI 控制台获取正式凭证：\n"
            "  https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n\n"
            "如需帮助，扫码加入社群获取最新动态：\n"
            "  https://at.umtrack.com/r4Tnme\n"
            "============================================================"
        ),
        "en_US": (
            "============================================================\n"
            "Your super data analyst is ready!\n"
            "Just ask in natural language to intelligently match and analyze your Excel files or Quick BI datasets,\n"
            "and surface insights instantly. Complex analysis has never been this simple.\n\n"
            "We detected that you have not configured credentials yet, so we will automatically register trial credentials for you and start your trial period.\n\n"
            "After the trial expires, please go to the Quick BI console to obtain formal credentials:\n"
            "  https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n\n"
            "If you need help, scan the code to join the community group for the latest updates:\n"
            "  https://at.umtrack.com/r4Tnme\n"
            "============================================================"
        ),
    },
    # ── OpenAPI 业务错误码提示 ─────────────────────────────────
    "error_agent_not_deployed": {
        "zh_CN": "⚠️ 当前站点尚未部署 {service} 智能分析服务，请联系管理员确认服务部署状态。",
        "en_US": "⚠️ The {service} agent service is not deployed on this site. Please contact your administrator to verify the service deployment status.",
    },
    "error_access_forbidden": {
        "zh_CN": "⚠️ 当前工作空间暂不支持此功能。如需使用，请联系管理员开通相关权限。",
        "en_US": "⚠️ This feature is not available in the current workspace. Please contact your administrator to enable access.",
    },
    "error_module_not_purchased": {
        "zh_CN": "⚠️ 尚未购买智能问数模块，请前往 Quick BI 控制台完成模块订购后再试。",
        "en_US": "⚠️ The Smart Q (NL2SQL) module has not been purchased. Please go to the Quick BI console to subscribe before trying again.",
    },
    "error_quota_not_granted": {
        "zh_CN": "⚠️ 您尚未获得该模块的席位授权，请联系组织管理员为您分配使用权限。",
        "en_US": "⚠️ You have not been granted quota authorization for this module. Please contact your administrator to obtain permission.",
    },
    "error_smartq_quota_exhausted": {
        "zh_CN": "⚠️ 智能问数额度已用完。如需继续使用，请前往 Quick BI 控制台购买额外额度。",
        "en_US": "⚠️ The Smart Q query quota has been exhausted. Please go to the Quick BI console to purchase additional quota.",
    },
    "error_token_exhausted": {
        "zh_CN": "⚠️ Token 额度已耗尽。如需继续使用，请前往 Quick BI 控制台购买额外 Token 额度。",
        "en_US": "⚠️ The token quota has been exhausted. Please go to the Quick BI console to purchase additional token quota.",
    },
    "error_explore_quota_exhausted": {
        "zh_CN": "⚠️ 探索版智能问数额度已用完。如需继续使用，请前往 Quick BI 控制台升级或购买额外额度。",
        "en_US": "⚠️ The Smart Q Explore quota has been exhausted. Please go to the Quick BI console to upgrade or purchase additional quota.",
    },
    "error_qreport_exceed_limits": {
        "zh_CN": "⚠️ 组织内免费报告创建次数已用完。如需继续生成报告，请前往 Quick BI 控制台购买报告额度。",
        "en_US": "⚠️ The number of free report creations within the organization has been used up. Please go to the Quick BI console to purchase report quota.",
    },
    "error_qreport_exceed_quota": {
        "zh_CN": "⚠️ 报告并发数已达上限，请稍后再试。如频繁遇到此问题，请联系管理员调整并发配额。",
        "en_US": "⚠️ The maximum number of concurrent report connections has been reached. Please try again later. If this occurs frequently, contact your administrator to adjust the concurrency quota.",
    },
    "error_user_not_in_org": {
        "zh_CN": "⚠️ 当前用户不在组织中，无法使用此功能。请联系组织管理员将您添加到组织。",
        "en_US": "⚠️ The current user is not in the organization and cannot use this feature. Please contact your organization administrator to add you.",
    },
    "error_no_permission": {
        "zh_CN": "⚠️ 您没有操作权限，请联系组织管理员授予相应权限。",
        "en_US": "⚠️ You do not have permission to perform this operation. Please contact your organization administrator to grant the required permissions.",
    },
    "config_trial_expired": {
        "zh_CN": (
            "============================================================\n"
            "SmartQ 超级分析助手已陪伴你一周，我们看到你正在用 AI 发现数据背后的真相——这非常了不起。\n\n"
            "⏰ 试用模式已结束\n"
            "授权到期后，动态分析将暂时暂停。\n\n"
            "💡 其实有更省力的方式\n"
            "目前的「文件模式」还需你手动搬运数据。想让 AI 直接接入你的企业数据资产、自动刷新分析结果？试试全功能版。\n\n"
            "🎁 0 元体验，限时加赠\n"
            "现在就来阿里云，领取额外 30 天全功能体验，解锁企业级安全管控与深度分析引擎，\n"
            "让 AI 洞察更精准、更稳定。点击下方链接领取：\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n\n"
            "💬 点击下方链接加入社群，获取最新动态：\n"
            "https://at.umtrack.com/r4Tnme\n"
            "============================================================"
        ),
        "en_US": (
            "============================================================\n"
            "The SmartQ super analysis assistant has been with you for a week, and we see you are using AI to uncover the truth behind your data - that's impressive.\n\n"
            "⏰ Trial mode has ended\n"
            "After authorization expires, dynamic analysis will be paused for now.\n\n"
            "💡 There is actually an easier way\n"
            "The current \"file mode\" still requires you to move data manually. Want AI to connect directly to your enterprise data assets and automatically refresh analysis results? Try the full feature set now.\n\n"
            "🎁 $0 trial, limited-time bonus\n"
            "Join Alibaba Cloud now to get an extra 30 days of full-feature access, unlocking enterprise-grade security controls and an advanced analysis engine for more accurate and stable AI insights. Click the link below to claim your trial:\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n\n"
            "💬 Click the link below to join the community group for the latest updates:\n"
            "https://at.umtrack.com/r4Tnme\n"
            "============================================================"
        ),
    },
    "config_header_skill": {
        "zh_CN": (
            "# Quick BI 用户配置（此文件不受 skill 包更新影响）\n"
            "# 配置优先级: 本文件 > ~/.qbi/config.yaml > 包 default_config.yaml\n"
            "# 路径: {path}\n\n"
        ),
        "en_US": (
            "# Quick BI user configuration (this file is not affected by skill package updates)\n"
            "# Configuration priority: this file > ~/.qbi/config.yaml > package default_config.yaml\n"
            "# Path: {path}\n\n"
        ),
    },
    "config_header_global": {
        "zh_CN": (
            "# Quick BI 全局配置（所有 skill 共用，不受 skill 包更新影响）\n"
            "# 建议将所有配置 (server_domain, api_key, api_secret, user_token 等) 放在此文件\n\n"
        ),
        "en_US": (
            "# Quick BI global configuration (shared by all skills and not affected by skill package updates)\n"
            "# It is recommended to place all configurations (server_domain, api_key, api_secret, user_token, etc.) in this file\n\n"
        ),
    },
    "config_header_default": {
        "zh_CN": (
            "# Quick BI 默认配置（随 skill 包发布）\n"
            "# 自动注册生成的 user_token 也会写入此处\n\n"
        ),
        "en_US": (
            "# Quick BI default configuration (released with the skill package)\n"
            "# The user_token generated by automatic registration will also be written here\n\n"
        ),
    },

    # ── utils: user registration ───────────────────────────────────
    "reg_add_user_request": {
        "zh_CN": "[用户注册][添加用户] 请求: POST {uri}",
        "en_US": "[User Registration][Add User] Request: POST {uri}",
    },
    "reg_add_user_params": {
        "zh_CN": "[用户注册][添加用户] 参数: {body}",
        "en_US": "[User Registration][Add User] Parameters: {body}",
    },
    "reg_add_user_response": {
        "zh_CN": "[用户注册][添加用户] 响应: {body}",
        "en_US": "[User Registration][Add User] Response: {body}",
    },
    "reg_add_user_exception": {
        "zh_CN": "[用户注册][添加用户] 异常: {exc}",
        "en_US": "[User Registration][Add User] Exception: {exc}",
    },
    "reg_query_request": {
        "zh_CN": "[用户注册][查询用户] 请求: GET {uri}?account={account}",
        "en_US": "[User Registration][Query User] Request: GET {uri}?account={account}",
    },
    "reg_query_response": {
        "zh_CN": "[用户注册][查询用户] 响应: {body}",
        "en_US": "[User Registration][Query User] Response: {body}",
    },
    "reg_query_exception": {
        "zh_CN": "[用户注册][查询用户] 异常: {exc}",
        "en_US": "[User Registration][Query User] Exception: {exc}",
    },
    "reg_token_written": {
        "zh_CN": "[用户注册] user_token 已写入 {path}",
        "en_US": "[User Registration] user_token has been written to {path}",
    },
    "reg_token_write_warn": {
        "zh_CN": "[用户注册] 警告: 无法写入 user_token 到 {path}: {exc}",
        "en_US": "[User Registration] Warning: unable to write user_token to {path}: {exc}",
    },
    "reg_start": {
        "zh_CN": "[用户注册] user_token 未配置，启动自动注册 (accountId={account_id}, accountName={hostname})",
        "en_US": "[User Registration] user_token is not configured; starting automatic registration (accountId={account_id}, accountName={hostname})",
    },
    "reg_found_existing": {
        "zh_CN": "[用户注册] 通过 accountName 找到已有用户, userId={uid}",
        "en_US": "[User Registration] Found an existing user by accountName, userId={uid}",
    },
    "reg_no_existing": {
        "zh_CN": "[用户注册] 未找到已有用户，正在添加 (accountName={hostname}) ...",
        "en_US": "[User Registration] No existing user found; adding now (accountName={hostname}) ...",
    },
    "reg_add_success": {
        "zh_CN": "[用户注册] 添加成功, userId={uid}",
        "en_US": "[User Registration] Added successfully, userId={uid}",
    },
    "reg_already_exists": {
        "zh_CN": "[用户注册] 添加返回已存在 (error code={code})，重新查询 userId ...",
        "en_US": "[User Registration] Add returned already exists (error code={code}), querying userId again ...",
    },
    "reg_query_success": {
        "zh_CN": "[用户注册] 查询成功, userId={uid}",
        "en_US": "[User Registration] Query successful, userId={uid}",
    },
    "reg_retry_suffix": {
        "zh_CN": "[用户注册] 使用后缀名重试 (accountName={name}) ...",
        "en_US": "[User Registration] Retrying with a suffixed name (accountName={name}) ...",
    },
    "reg_retry_success": {
        "zh_CN": "[用户注册] 重试添加成功, userId={uid}",
        "en_US": "[User Registration] Retry add succeeded, userId={uid}",
    },
    "reg_failed": {
        "zh_CN": "自动注册用户失败，请手动在 ~/.qbi/config.yaml 中配置 user_token。",
        "en_US": "Automatic user registration failed. Please configure user_token manually in ~/.qbi/config.yaml.",
    },

    # ── utils: file validation & upload ────────────────────────────
    "util_file_not_found": {
        "zh_CN": "文件不存在：{path}",
        "en_US": "File does not exist: {path}",
    },
    "util_not_valid_file": {
        "zh_CN": "不是有效文件：{path}",
        "en_US": "Not a valid file: {path}",
    },
    "util_unsupported_type": {
        "zh_CN": "不支持的文件类型：{suffix}，仅支持 doc/docx/xls/xlsx/csv",
        "en_US": "Unsupported file type: {suffix}; only doc/docx/xls/xlsx/csv are supported",
    },
    "util_file_too_large": {
        "zh_CN": (
            "当前文件超过5MB限制，您可免费开通 Quick BI 企业试用，"
            "直连企业数据资产直接查询，无文件大小限制。\n"
            "链接：https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
        "en_US": (
            "The current file exceeds the 5MB limit. You can start a free Quick BI enterprise trial "
            "to connect directly to your enterprise data assets for queries with no file size limit.\n"
            "Link: https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
    },
    "util_upload_non_json": {
        "zh_CN": "上传文件接口返回了非 JSON 响应：{text}",
        "en_US": "The upload file API returned a non-JSON response: {text}",
    },
    "util_upload_unexpected": {
        "zh_CN": "上传文件接口返回了意外结构：{result}",
        "en_US": "The upload file API returned an unexpected structure: {result}",
    },
    "util_upload_incomplete": {
        "zh_CN": "上传文件接口未返回完整的文件信息：{result}",
        "en_US": "The upload file API did not return complete file information: {result}",
    },
    "util_resource_format_error": {
        "zh_CN": "资源格式不正确：{item}",
        "en_US": "Incorrect resource format: {item}",
    },
    "util_http_error": {
        "zh_CN": "HTTP {status} {reason} for {method} {uri}\n响应体: {body}",
        "en_US": "HTTP {status} {reason} for {method} {uri}\nResponse body: {body}",
    },

    # ── utils: chart summaries ─────────────────────────────────────
    "util_structured_chart_empty": {
        "zh_CN": "[structuredChart] 空结果",
        "en_US": "[structuredChart] Empty result",
    },
    "util_unstructured_chart_empty": {
        "zh_CN": "[unStructuredChart] 空结果",
        "en_US": "[unStructuredChart] Empty result",
    },
    "util_web_results_count": {
        "zh_CN": "{count} 条网页结果",
        "en_US": "{count} web results",
    },
    "util_kb_results_count": {
        "zh_CN": "{count} 条知识库结果",
        "en_US": "{count} knowledge base results",
    },
    "reg_failed_console_hint": {
        "zh_CN": "可通过 Quick BI 管理控制台获取用户 ID。",
        "en_US": "You can obtain the user ID from the Quick BI admin console.",
    },

    # ── utils: report / polling ────────────────────────────────────
    "util_thinking": {
        "zh_CN": "思考中...",
        "en_US": "Thinking...",
    },
    "util_unknown_error": {
        "zh_CN": "未知错误",
        "en_US": "Unknown error",
    },
    "util_result_generating": {
        "zh_CN": "结果生成中，请耐心等待",
        "en_US": "The result is being generated. Please wait.",
    },
    "util_report_failed": {
        "zh_CN": "报告生成失败：{error}",
        "en_US": "Report generation failed: {error}",
    },
    "util_report_biz_error": {
        "zh_CN": "报告创建失败（错误码: {code}）：{message}",
        "en_US": "Report creation failed (error code: {code}): {message}",
    },
    "util_report_link": {
        "zh_CN": "在线数据报告：[点击查看完整报告]({url})",
        "en_US": "Online data report: [Click to view the full report]({url})",
    },
    "util_report_link_label": {
        "zh_CN": "报告链接",
        "en_US": "Report link",
    },
    "util_report_edit_hint": {
        "zh_CN": "💡 您可以在产品内对报告进行二次编辑和调整",
        "en_US": "💡 You can further edit and refine the report within the product",
    },
    "util_running_task_detected": {
        "zh_CN": "[运行中任务] 检测到当前用户已有运行中的任务",
        "en_US": "[Running Task] Detected that the current user already has a running task",
    },
    "util_running_task_question": {
        "zh_CN": "[运行中任务] 已有任务问题: {question}",
        "en_US": "[Running Task] Existing task question: {question}",
    },
    "util_running_task_chatid": {
        "zh_CN": "[运行中任务] 已有任务 chatId: {chat_id}",
        "en_US": "[Running Task] Existing task chatId: {chat_id}",
    },
    "util_running_task_reuse": {
        "zh_CN": "[运行中任务] 将使用上述 chatId 进行后续轮询",
        "en_US": "[Running Task] The above chatId will be used for subsequent polling",
    },
    "util_poll_timeout": {
        "zh_CN": "轮询超时：已等待 {minutes} 分钟",
        "en_US": "Polling timed out: waited {minutes} minutes",
    },

    # ── utils: function labels ─────────────────────────────────────
    "util_label_thinking": {
        "zh_CN": "思考中",
        "en_US": "Thinking...",
    },
    "util_label_learn": {
        "zh_CN": "文件学习",
        "en_US": "File learning",
    },
    "util_label_refuse": {
        "zh_CN": "拒识",
        "en_US": "Refusal",
    },
    "util_label_main_text": {
        "zh_CN": "规划步骤",
        "en_US": "Planning steps",
    },
    "util_label_interrupt": {
        "zh_CN": "等待确认",
        "en_US": "Waiting for confirmation",
    },
    "util_label_online_search": {
        "zh_CN": "联网搜索结果",
        "en_US": "Online search results",
    },
    "util_label_knowledge_base": {
        "zh_CN": "知识库结果",
        "en_US": "Knowledge base results",
    },

    # ── smartq_stream_query ────────────────────────────────────────
    "smartq_olap_result": {
        "zh_CN": "[取数结果] 图表类型: {chart_type} ({raw_type})",
        "en_US": "[Data Retrieval Result] Chart type: {chart_type} ({raw_type})",
    },
    "smartq_olap_rows": {
        "zh_CN": "[取数结果] 数据行数: {count}",
        "en_US": "[Data Retrieval Result] Row count: {count}",
    },
    "smartq_no_data": {
        "zh_CN": "（无数据）",
        "en_US": "(No data)",
    },
    "smartq_header": {
        "zh_CN": "[小Q问数] 问题: {question}",
        "en_US": "[SmartQ Q&A] Question: {question}",
    },
    "smartq_dataset": {
        "zh_CN": "[小Q问数] 数据集: {cube_id}",
        "en_US": "[SmartQ Q&A] Dataset: {cube_id}",
    },
    "smartq_terminated": {
        "zh_CN": "\n[数据集问数终止] 未能匹配到可用数据集，请参考上方提示选择其他方式。",
        "en_US": "\n[Dataset Q&A Terminated] No available dataset could be matched. Please refer to the prompt above and choose another approach.",
    },
    "smartq_text": {
        "zh_CN": "[文本] {data}",
        "en_US": "[Text] {data}",
    },
    "smartq_related_info": {
        "zh_CN": "\n[关联知识] {data}",
        "en_US": "\n[Related Knowledge] {data}",
    },
    "smartq_reasoning": {
        "zh_CN": "\n[推理过程] {data}",
        "en_US": "\n[Reasoning] {data}",
    },
    "smartq_sql": {
        "zh_CN": "\n[SQL] {data}",
        "en_US": "\n[SQL] {data}",
    },
    "smartq_conclusion": {
        "zh_CN": "\n[结论] {data}",
        "en_US": "\n[Conclusion] {data}",
    },
    "smartq_check": {
        "zh_CN": "\n[校验] {data}",
        "en_US": "\n[Validation] {data}",
    },
    "smartq_error": {
        "zh_CN": "\n[错误] {data}",
        "en_US": "\n[Error] {data}",
    },
    "smartq_summary": {
        "zh_CN": "\n[数据解读] {data}",
        "en_US": "\n[Data Interpretation] {data}",
    },
    "smartq_finish": {
        "zh_CN": "\n[完成] {data}",
        "en_US": "\n[Done] {data}",
    },
    "smartq_stream_failed": {
        "zh_CN": "\n[问数流式请求失败] POST {uri} 调用异常:\n  {exc}",
        "en_US": "\n[Streaming Q&A Request Failed] POST {uri} call exception:\n  {exc}",
    },
    "smartq_end": {
        "zh_CN": "[问数结束] 共生成 {count} 张图表",
        "en_US": "[Q&A Finished] Generated {count} chart(s)",
    },
    "smartq_trace_id": {
        "zh_CN": "[Trace ID] {trace_id}(问题反馈时请提供此 ID)",
        "en_US": "[Trace ID] {trace_id}(please provide this ID when reporting an issue)",
    },
    "smartq_query_saved": {
        "zh_CN": "[查询结果] 已保存到: {path}",
        "en_US": "[Query Result] Saved to: {path}",
    },
    "smartq_query_save_failed": {
        "zh_CN": "[警告] 查询结果保存失败: {exc}",
        "en_US": "[Warning] Failed to save query result: {exc}",
    },
    "smartq_param_parse_error": {
        "zh_CN": "  [param] 无法解析 data JSON",
        "en_US": "  [param] Unable to parse data JSON",
    },
    "smartq_olap_parse_error": {
        "zh_CN": "  [olapResult] 无法解析 data JSON",
        "en_US": "  [olapResult] Unable to parse data JSON",
    },
    "smartq_locale": {
        "zh_CN": "[小Q问数] 语言: {locale}",
        "en_US": "[SmartQ Q&A] Locale: {locale}",
    },
    "smartq_param_info": {
        "zh_CN": "[参数] {data}",
        "en_US": "[Param] {data}",
    },
    "smartq_field_row_count": {
        "zh_CN": "  字段数: {fields}, 数据行数: {rows}",
        "en_US": "  Field count: {fields}, row count: {rows}",
    },
    "smartq_chart_default_title": {
        "zh_CN": "图表",
        "en_US": "Chart",
    },
    "smartq_query_result_default": {
        "zh_CN": "查询结果",
        "en_US": "Query Result",
    },

    # ── file_stream_query ──────────────────────────────────────────
    "file_query_code_generated": {
        "zh_CN": "\n[代码] 分析代码已生成",
        "en_US": "\n[Code] Analysis code generated",
    },
    "file_query_chart_generated": {
        "zh_CN": "\n[图表] 已生成 → {path}",
        "en_US": "\n[Chart] Generated → {path}",
    },
    "file_query_result_groups": {
        "zh_CN": "\n\n[取数结果] 共 {count} 组数据",
        "en_US": "\n\n[Data Retrieval Results] {count} dataset group(s)",
    },
    "file_query_dataset_row": {
        "zh_CN": "  数据集{idx}: {rows} 行, fields={fields}",
        "en_US": "  Dataset{idx}: {rows} rows, fields={fields}",
    },
    "file_query_exec_result": {
        "zh_CN": "\n[执行结果] {data}",
        "en_US": "\n[Execution Result] {data}",
    },
    "file_query_plan": {
        "zh_CN": "\n[分析规划]\n{data}",
        "en_US": "\n[Analysis Plan]\n{data}",
    },
    "file_query_sub_question": {
        "zh_CN": "\n[子问题] {data}",
        "en_US": "\n[Sub-question] {data}",
    },
    "file_query_html_chart": {
        "zh_CN": "\n[HTML 图表] 已保存 → {path}(仅供参考，图表从 result 数据生成)",
        "en_US": "\n[HTML Chart] Saved → {path}(for reference only; charts are generated from result data)",
    },
    "file_query_chart_data": {
        "zh_CN": "\n[图表数据] {count} 组数据",
        "en_US": "\n[Chart Data] {count} dataset group(s)",
    },
    "file_query_unstructured_chart": {
        "zh_CN": "\n[非结构化图表] 已保存 → {path}",
        "en_US": "\n[Unstructured Chart] Saved → {path}",
    },
    "file_query_conclusion": {
        "zh_CN": "\n[结论] {data}",
        "en_US": "\n[Conclusion] {data}",
    },
    "file_query_summary": {
        "zh_CN": "\n[数据解读] {data}",
        "en_US": "\n[Data Interpretation] {data}",
    },
    "file_query_finish": {
        "zh_CN": "\n[完成] {data}",
        "en_US": "\n[Done] {data}",
    },
    "file_query_finish_empty": {
        "zh_CN": "\n[完成]",
        "en_US": "\n[Done]",
    },
    "file_query_error": {
        "zh_CN": "\n[错误] {data}",
        "en_US": "\n[Error] {data}",
    },
    "file_query_check": {
        "zh_CN": "\n[校验] {data}",
        "en_US": "\n[Validation] {data}",
    },
    "file_query_reject": {
        "zh_CN": "\n[拒识] {data}",
        "en_US": "\n[Refusal] {data}",
    },
    "file_query_step": {
        "zh_CN": "\n[步骤] {data}",
        "en_US": "\n[Step] {data}",
    },
    "file_query_sub_step": {
        "zh_CN": "\n[子步骤] {data}",
        "en_US": "\n[Sub-step] {data}",
    },
    "file_query_rewrite": {
        "zh_CN": "\n[问题改写] {data}",
        "en_US": "\n[Question Rewrite] {data}",
    },
    "file_query_python_error": {
        "zh_CN": "\n[Python 错误] {data}",
        "en_US": "\n[Python Error] {data}",
    },
    "file_query_olap_result": {
        "zh_CN": "\n[OLAP 结果] rows={rows}",
        "en_US": "\n[OLAP Result] rows={rows}",
    },
    "file_query_online_search": {
        "zh_CN": "\n[联网搜索] {data}",
        "en_US": "\n[Web Search] {data}",
    },
    "file_query_thinking": {
        "zh_CN": "\n[思考] {data}",
        "en_US": "\n[Thinking] {data}",
    },
    "file_query_schedule": {
        "zh_CN": "\n[调度] {data}",
        "en_US": "\n[Scheduling] {data}",
    },
    "file_query_selector": {
        "zh_CN": "\n[选表] {data}",
        "en_US": "\n[Table Selection] {data}",
    },
    "file_query_system_selector": {
        "zh_CN": "\n[系统选表] {data}",
        "en_US": "\n[System Table Selection] {data}",
    },
    "file_query_react": {
        "zh_CN": "\n[重试代码] {data}",
        "en_US": "\n[Retry Code] {data}",
    },
    "file_query_table_retrieve": {
        "zh_CN": "\n[表召回] {data}",
        "en_US": "\n[Table Recall] {data}",
    },
    "file_query_schema_retrieve": {
        "zh_CN": "\n[Schema 召回] {data}",
        "en_US": "\n[Schema Recall] {data}",
    },
    "file_query_resource_info": {
        "zh_CN": "\n[资源信息] {data}",
        "en_US": "\n[Resource Info] {data}",
    },
    "file_query_file_parse_error": {
        "zh_CN": (
            "\n============================================================\n"
            "⚠️ 数据文件解析失败\n"
            "用于问数的数据文件可能存在格式或内容问题，服务端多次重试未成功。\n\n"
            "💡 建议排查\n"
            "请检查文件是否为标准 Excel/CSV 格式，确认数据完整无损后重新上传。\n\n"
            "💬 如仍无法解决，点击下方链接加入讨论群，联系 Quick BI 产品服务团队获得支持：\n"
            "https://at.umtrack.com/r4Tnme\n"
            "============================================================"
        ),
        "en_US": (
            "\n============================================================\n"
            "⚠️ Failed to parse the data file\n"
            "The data file used for Q&A may have format or content issues, and repeated retries on the server side were unsuccessful.\n\n"
            "💡 Recommended checks\n"
            "Please check whether the file is in standard Excel/CSV format, and confirm the data is complete and undamaged before re-uploading it.\n\n"
            "💬 If the issue still cannot be resolved, click the link below to join the discussion group and contact the Quick BI product service team for support:\n"
            "https://at.umtrack.com/r4Tnme\n"
            "============================================================"
        ),
    },
    "file_query_header": {
        "zh_CN": "[文件问数] fileId={file_id}",
        "en_US": "[File-based Q&A] fileId={file_id}",
    },
    "file_query_userid": {
        "zh_CN": "[文件问数] userId={user_id}",
        "en_US": "[File-based Q&A] userId={user_id}",
    },
    "file_query_question": {
        "zh_CN": "[文件问数] 问题: {question}",
        "en_US": "[File-based Q&A] Question: {question}",
    },
    "file_query_result_summary_data": {
        "zh_CN": "取数结果：共 {count} 组数据",
        "en_US": "Data retrieval results: {count} dataset group(s)",
    },
    "file_query_result_summary_chart": {
        "zh_CN": "生成图表 {count} 张:",
        "en_US": "Generated {count} chart(s):",
    },
    "file_query_result_summary_error": {
        "zh_CN": "错误：{error}",
        "en_US": "Error: {error}",
    },
    "file_query_no_valid_result": {
        "zh_CN": "未获取到有效结果",
        "en_US": "No valid result obtained",
    },
    "file_query_python": {
        "zh_CN": "\n[Python] {data}",
        "en_US": "\n[Python] {data}",
    },
    "file_query_locale": {
        "zh_CN": "[文件问数] 语言: {locale}",
        "en_US": "[File-based Q&A] Locale: {locale}",
    },
    "file_query_chart_link": {
        "zh_CN": "![{title}]({path})",
        "en_US": "![{title}]({path})",
    },
    "file_query_chart_data_raw": {
        "zh_CN": "\n[图表数据] {data}",
        "en_US": "\n[Chart Data] {data}",
    },
    "file_query_sql_block": {
        "zh_CN": "\n[SQL]\n{data}",
        "en_US": "\n[SQL]\n{data}",
    },
    "file_query_exec_result_block": {
        "zh_CN": "\n[执行结果]\n{data}",
        "en_US": "\n[Execution Result]\n{data}",
    },

    # ── cube_resolver ──────────────────────────────────────────────
    "cube_permission_query_failed": {
        "zh_CN": "查询问数数据集权限失败: code={code}, message={message}",
        "en_US": "Failed to query permissions for Q&A datasets: code={code}, message={message}",
    },
    "cube_table_search_failed": {
        "zh_CN": "tableSearch 失败: [{code}] {message}",
        "en_US": "tableSearch failed: [{code}] {message}",
    },
    "cube_smart_select_start": {
        "zh_CN": "[智能选表] 未指定数据集，根据问题自动匹配中 ...",
        "en_US": "[Intelligent Table Selection] No dataset specified. Automatically matching based on the question ...",
    },
    "cube_smart_select_question": {
        "zh_CN": "[智能选表] 问题: {question}",
        "en_US": "[Intelligent Table Selection] Question: {question}",
    },
    "cube_permission_failed": {
        "zh_CN": "[权限查询失败] GET /openapi/v2/smartq/query/llmCubeWithThemeList 调用异常:\n  {exc}",
        "en_US": "[Permission Query Failed] GET /openapi/v2/smartq/query/llmCubeWithThemeList call exception:\n  {exc}",
    },
    "cube_no_permission": {
        "zh_CN": "[权限查询] 该用户没有任何数据集的问数权限",
        "en_US": "[Permission Query] This user does not have Q&A permission for any dataset",
    },
    "cube_no_datasets_promo": {
        "zh_CN": (
            "\n============================================================\n"
            "你当前没有任何可用的问数数据集。\n\n"
            "📂 试试「文件问数」\n"
            "无需任何权限配置，上传 Excel/CSV 文件即可直接分析。\n\n"
            "🚀 0 元体验，限时加赠\n"
            "现在就来阿里云，领取额外 30 天全功能体验，解锁企业级安全管控与深度分析引擎，\n"
            "让 AI 洞察更精准、更稳定。点击下方链接领取：\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n\n"
            "💬 点击下方链接加入社群，获取最新动态：\n"
            "https://at.umtrack.com/r4Tnme\n"
            "============================================================"
        ),
        "en_US": (
            "\n============================================================\n"
            "You currently do not have any available Q&A datasets.\n\n"
            "📂 Try \"file-based Q&A\"\n"
            "No permission setup is required. Upload an Excel/CSV file to analyze it directly.\n\n"
            "🚀 Free trial, limited-time extension\n"
            "Go to Alibaba Cloud now to receive an additional 30-day full-feature trial, unlocking enterprise-grade security controls and the deep analytics engine,\n"
            "making AI insights more accurate and more stable. Click the link below to claim your trial:\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n\n"
            "💬 Click the link below to join the discussion group for the latest updates:\n"
            "https://at.umtrack.com/r4Tnme\n"
            "============================================================"
        ),
    },
    "cube_accessible_count": {
        "zh_CN": "[权限查询] 用户有 {count} 个可用数据集:",
        "en_US": "[Permission Query] User has {count} accessible datasets:",
    },
    "cube_accessible_total": {
        "zh_CN": "  ... 共 {count} 个",
        "en_US": "  ... total {count}",
    },
    "cube_smart_select_trying": {
        "zh_CN": "[智能选表] 正在尝试匹配前 {count} 个相关数据集...",
        "en_US": "[Intelligent Table Selection] Trying to match with top {count} relevant datasets...",
    },
    "cube_smart_select_success": {
        "zh_CN": "[智能选表] 匹配成功 (候选数 {count})",
        "en_US": "[Intelligent Table Selection] Match succeeded (batch size {count} )",
    },
    "cube_smart_select_over_limit": {
        "zh_CN": "[智能选表] 候选数 {count} 超过 API 限制，降级到下一档...",
        "en_US": "[Intelligent Table Selection] Candidate count {count} exceeds the API limit; downgrading to the next batch...",
    },
    "cube_smart_select_failed": {
        "zh_CN": "[智能选表失败] POST /openapi/v2/smartq/tableSearch 调用异常:\n  {exc}",
        "en_US": "[Intelligent Table Selection Failed] POST /openapi/v2/smartq/tableSearch call exception:\n  {exc}",
    },
    "cube_smart_select_matched": {
        "zh_CN": "[智能选表] 匹配到数据集: {cube_id}",
        "en_US": "[Intelligent Table Selection] Matched dataset: {cube_id}",
    },
    "cube_smart_select_others": {
        "zh_CN": "[智能选表] 其他候选: {others}",
        "en_US": "[Intelligent Table Selection] Other candidates: {others}",
    },
    "cube_relevance_fallback": {
        "zh_CN": "[相关性匹配] 智能选表未返回结果，根据问题和数据集名称的相关度选择:",
        "en_US": "[Relevance Match] Intelligent table selection returned no result. Choosing based on relevance between the question and dataset names:",
    },
    "cube_relevance_selected": {
        "zh_CN": "→ 选定",
        "en_US": "→ Selected",
    },
    "cube_relevance_candidate": {
        "zh_CN": "  候选",
        "en_US": "  Candidate",
    },

    # ── cube_name_lookup (no translation reference) ────────────────
    "cube_lookup_empty_name": {
        "zh_CN": "cube-name 参数为空",
        "en_US": "cube-name parameter is empty",
    },
    "cube_lookup_searching": {
        "zh_CN": "[名称直查] 查找数据集: {name}",
        "en_US": "[Name Lookup] Searching for dataset: {name}",
    },
    "cube_lookup_permission_failed": {
        "zh_CN": "[名称直查] 权限查询失败: {exc}",
        "en_US": "[Name Lookup] Permission query failed: {exc}",
    },
    "cube_lookup_no_datasets": {
        "zh_CN": "[名称直查] 用户没有可用数据集",
        "en_US": "[Name Lookup] User has no available datasets",
    },
    "cube_lookup_count": {
        "zh_CN": "[名称直查] 用户共有 {count} 个可用数据集",
        "en_US": "[Name Lookup] User has {count} available dataset(s)",
    },
    "cube_lookup_result": {
        "zh_CN": "[名称直查] 匹配结果: status={status}",
        "en_US": "[Name Lookup] Match result: status={status}",
    },
    "cube_name_lookup_start": {
        "zh_CN": "[名称直查] 尝试按名称匹配数据集: {name}",
        "en_US": "[Name Lookup] Attempting to match dataset by name: {name}",
    },
    "cube_name_lookup_exact": {
        "zh_CN": "[名称直查] 精确匹配到数据集: {cube_name} ({cube_id})",
        "en_US": "[Name Lookup] Exact match found: {cube_name} ({cube_id})",
    },
    "cube_name_lookup_similar": {
        "zh_CN": "[名称直查] 未精确匹配，发现 {count} 个相似候选，继续走智能选表",
        "en_US": "[Name Lookup] No exact match, found {count} similar candidate(s), falling back to intelligent table selection",
    },
    "cube_name_lookup_not_found": {
        "zh_CN": "[名称直查] 未找到名为 '{name}' 的数据集，继续走智能选表",
        "en_US": "[Name Lookup] No dataset named '{name}' found, falling back to intelligent table selection",
    },

    # ── upload_file ────────────────────────────────────────────────
    "upload_file_not_found": {
        "zh_CN": "文件不存在: {path}",
        "en_US": "File does not exist: {path}",
    },
    "upload_unsupported_format": {
        "zh_CN": "不支持的文件格式 .{ext}，仅支持: {allowed}",
        "en_US": "Unsupported file format .{ext}, only supported: {allowed}",
    },
    "upload_size_exceeded": {
        "zh_CN": (
            "当前文件超过5MB限制，您可免费开通 Quick BI 企业试用，"
            "直连企业数据资产直接查询，无文件大小限制。\n"
            "链接：https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
        "en_US": (
            "The current file exceeds the 5MB limit. You can start a free Quick BI enterprise trial "
            "to connect directly to your enterprise data assets for queries with no file size limit.\n"
            "Link: https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
    },
    "upload_request": {
        "zh_CN": "[文件上传] 请求: POST {url}",
        "en_US": "[File Upload] Request: POST {url}",
    },
    "upload_form_params": {
        "zh_CN": "[文件上传] 表单参数: {params}",
        "en_US": "[File Upload] Form parameters: {params}",
    },
    "upload_file_info": {
        "zh_CN": "[文件上传] 文件: name={name}, size={size}KB, contentType={content_type}",
        "en_US": "[File Upload] File: name={name}, size={size}KB, contentType={content_type}",
    },
    "upload_userid": {
        "zh_CN": "[文件上传] userId={user_id}",
        "en_US": "[File Upload] userId={user_id}",
    },
    "upload_uploading": {
        "zh_CN": "[文件上传] 正在上传: {file}",
        "en_US": "[File Upload] Uploading: {file}",
    },
    "upload_success": {
        "zh_CN": "[文件上传] 上传成功, fileId={file_id}",
        "en_US": "[File Upload] Upload succeeded, fileId={file_id}",
    },
    "upload_failed": {
        "zh_CN": "[文件上传] 上传失败: {message}",
        "en_US": "[File Upload] Upload failed: {message}",
    },
    "upload_error_detail": {
        "zh_CN": "[文件上传] 错误详情:",
        "en_US": "[File Upload] Error details:",
    },

    # ── chart_renderer ─────────────────────────────────────────────
    "chart_unit_hundred_million": {
        "zh_CN": "亿",
        "en_US": "100M",
    },
    "chart_unit_ten_thousand": {
        "zh_CN": "万",
        "en_US": "10K",
    },
    "chart_truncation_note": {
        "zh_CN": "显示前 {shown} 条（共 {total} 条）",
        "en_US": "Showing first {shown} items (total {total})",
    },
    "chart_data_comparison": {
        "zh_CN": "数据对比",
        "en_US": "Data Comparison",
    },
    "chart_stacked_bar": {
        "zh_CN": "堆积柱状图",
        "en_US": "Stacked Bar Chart",
    },
    "chart_percent_bar": {
        "zh_CN": "百分比柱状图",
        "en_US": "Percent Bar Chart",
    },
    "chart_stacked_horizontal_bar": {
        "zh_CN": "堆积条形图",
        "en_US": "Stacked Horizontal Bar Chart",
    },
    "chart_percent_horizontal_bar": {
        "zh_CN": "百分比条形图",
        "en_US": "Percent Horizontal Bar Chart",
    },
    "chart_scatter": {
        "zh_CN": "散点图",
        "en_US": "Scatter Plot",
    },
    "chart_bubble": {
        "zh_CN": "气泡图",
        "en_US": "Bubble Chart",
    },
    "chart_combo": {
        "zh_CN": "组合图",
        "en_US": "Combo Chart",
    },
    "chart_pie_other": {
        "zh_CN": "其他",
        "en_US": "Other",
    },
    "chart_no_data": {
        "zh_CN": "（无数据）",
        "en_US": "(No data)",
    },
    "chart_column_default": {
        "zh_CN": "列{idx}",
        "en_US": "Column{idx}",
    },
    "chart_table_truncated": {
        "zh_CN": "（共 {total} 行，仅显示前 50 行）",
        "en_US": "(Total {total} rows, showing only the first 50 rows)",
    },
    "chart_font_using": {
        "zh_CN": "使用中文字体: {font}",
        "en_US": "Using CJK font: {font}",
    },
    "chart_font_not_found": {
        "zh_CN": "警告: 未找到可用中文字体，图表中文可能显示为方框",
        "en_US": "Warning: No CJK font found; Chinese text in charts may appear as boxes",
    },
    "chart_format_value_yi": {
        "zh_CN": "{value:.2f} 亿",
        "en_US": "{value:.2f} 100M",
    },
    "chart_format_value_wan": {
        "zh_CN": "{value:.2f} 万",
        "en_US": "{value:.2f} 10K",
    },
    "chart_font_install_win": {
        "zh_CN": "建议安装: 在 Windows 设置 → 时间和语言 → 语言 → 中文（简体）→ 安装语言包，或手动安装 SimHei / Microsoft YaHei 字体",
        "en_US": "Suggestion: In Windows Settings → Time & Language → Language → Chinese (Simplified) → Install Language Pack, or manually install SimHei / Microsoft YaHei fonts",
    },
    "chart_font_install_mac": {
        "zh_CN": "建议安装: macOS 通常自带 PingFang SC，若缺失请通过字体册安装中文字体",
        "en_US": "Suggestion: macOS usually ships with PingFang SC. If missing, install CJK fonts via Font Book",
    },
    "chart_font_install_linux": {
        "zh_CN": "建议安装: yum install -y google-noto-sans-cjk-sc-fonts && fc-cache -fv",
        "en_US": "Suggestion: yum install -y google-noto-sans-cjk-sc-fonts && fc-cache -fv",
    },

    # ── document_local_parse (no translation reference) ────────────
    "doc_ocr_check_win": {
        "zh_CN": "请从 https://github.com/UB-Mannheim/tesseract/wiki 下载并安装，添加到 PATH",
        "en_US": "Please download and install from https://github.com/UB-Mannheim/tesseract/wiki, then add to PATH",
    },
    "doc_ocr_check_mac": {
        "zh_CN": "运行: brew install tesseract tesseract-lang",
        "en_US": "Run: brew install tesseract tesseract-lang",
    },
    "doc_ocr_check_linux": {
        "zh_CN": "运行: sudo apt install tesseract-ocr tesseract-ocr-chi-sim (Debian/Ubuntu) 或 sudo yum install tesseract (CentOS)",
        "en_US": "Run: sudo apt install tesseract-ocr tesseract-ocr-chi-sim (Debian/Ubuntu) or sudo yum install tesseract (CentOS)",
    },
    "doc_ocr_unavailable": {
        "zh_CN": "[OCR检查] ⚠ Tesseract 未安装或不可用: {msg}",
        "en_US": "[OCR Check] ⚠ Tesseract is not installed or unavailable: {msg}",
    },
    "doc_temp_file_locked": {
        "zh_CN": "[临时文件] 警告: 文件被占用，将在程序退出时删除: {path}",
        "en_US": "[Temp File] Warning: File is locked; it will be deleted on program exit: {path}",
    },
    "doc_scan_skip": {
        "zh_CN": "[扫描] 跳过不支持的文件: {name} ({ext})",
        "en_US": "[Scan] Skipping unsupported file: {name} ({ext})",
    },
    "doc_scan_found": {
        "zh_CN": "[扫描] 在 {path} 中找到 {count} 个支持的文件",
        "en_US": "[Scan] Found {count} supported file(s) in {path}",
    },
    "doc_scan_not_exist": {
        "zh_CN": "[扫描] 路径不存在: {path}",
        "en_US": "[Scan] Path does not exist: {path}",
    },
    "doc_pdf_few_chars": {
        "zh_CN": "[PDF提取] 警告: 本地提取文本较少 ({chars} 字符)，可能是扫描件，尝试 OCR...",
        "en_US": "[PDF Extract] Warning: Local extraction yielded few characters ({chars} chars); may be scanned; trying OCR...",
    },
    "doc_pdf_success": {
        "zh_CN": "[PDF提取] 成功提取 {chars} 字符",
        "en_US": "[PDF Extract] Successfully extracted {chars} characters",
    },
    "doc_pdf_failed": {
        "zh_CN": "[PDF提取] 本地提取失败: {exc}",
        "en_US": "[PDF Extract] Local extraction failed: {exc}",
    },
    "doc_pdf_ocr_fallback": {
        "zh_CN": "[PDF提取] 降级到 OCR 识别...",
        "en_US": "[PDF Extract] Falling back to OCR recognition...",
    },
    "doc_image_ocr_disabled": {
        "zh_CN": "[图片提取] 警告: 图片文件必须使用 OCR 提取，但 use_ocr=False",
        "en_US": "[Image Extract] Warning: Image files require OCR extraction, but use_ocr=False",
    },
    "doc_image_ocr": {
        "zh_CN": "[图片提取] 使用 OCR 识别: {name}",
        "en_US": "[Image Extract] Using OCR recognition: {name}",
    },
    "doc_word_unsupported": {
        "zh_CN": "不支持的 Word 格式: {ext}",
        "en_US": "Unsupported Word format: {ext}",
    },
    "doc_word_success": {
        "zh_CN": "[Word提取] 成功提取 {chars} 字符",
        "en_US": "[Word Extract] Successfully extracted {chars} characters",
    },
    "doc_word_failed": {
        "zh_CN": "[Word提取] 提取失败: {exc}",
        "en_US": "[Word Extract] Extraction failed: {exc}",
    },
    "doc_word_libreoffice": {
        "zh_CN": "[Word提取] 使用 libreoffice: {cmd}",
        "en_US": "[Word Extract] Using libreoffice: {cmd}",
    },
    "doc_word_converted": {
        "zh_CN": "[Word提取] 已将 .doc 转换为 .docx",
        "en_US": "[Word Extract] Converted .doc to .docx",
    },
    "doc_word_convert_failed": {
        "zh_CN": "[Word提取] libreoffice 转换失败: {exc}",
        "en_US": "[Word Extract] libreoffice conversion failed: {exc}",
    },
    "doc_word_no_libreoffice": {
        "zh_CN": "[Word提取] 警告: 未找到 libreoffice，尝试其他方法...",
        "en_US": "[Word Extract] Warning: libreoffice not found; trying other methods...",
    },
    "doc_word_textract_success": {
        "zh_CN": "[Word提取] 使用 textract 提取 {chars} 字符",
        "en_US": "[Word Extract] Extracted {chars} characters using textract",
    },
    "doc_word_no_textract": {
        "zh_CN": "[Word提取] 警告: 未安装 textract，.doc 文件提取受限",
        "en_US": "[Word Extract] Warning: textract not installed; .doc extraction is limited",
    },
    "doc_word_textract_failed": {
        "zh_CN": "[Word提取] textract 提取失败: {exc}",
        "en_US": "[Word Extract] textract extraction failed: {exc}",
    },
    "doc_word_ocr_fallback": {
        "zh_CN": "[Word提取] 降级到 OCR 识别...",
        "en_US": "[Word Extract] Falling back to OCR recognition...",
    },
    "doc_sheet_header": {
        "zh_CN": "### 工作表: {name}",
        "en_US": "### Worksheet: {name}",
    },
    "doc_excel_success": {
        "zh_CN": "[Excel提取] 成功提取 {chars} 字符",
        "en_US": "[Excel Extract] Successfully extracted {chars} characters",
    },
    "doc_excel_failed": {
        "zh_CN": "[Excel提取] 提取失败: {exc}",
        "en_US": "[Excel Extract] Extraction failed: {exc}",
    },
    "doc_excel_unsupported": {
        "zh_CN": "不支持的 Excel 格式: {ext}",
        "en_US": "Unsupported Excel format: {ext}",
    },
    "doc_csv_success": {
        "zh_CN": "[CSV提取] 成功提取 {chars} 字符 (编码: {encoding})",
        "en_US": "[CSV Extract] Successfully extracted {chars} characters (encoding: {encoding})",
    },
    "doc_csv_decode_failed": {
        "zh_CN": "无法解码 CSV 文件，尝试了 utf-8, gbk, gb2312, latin1",
        "en_US": "Unable to decode CSV file; tried utf-8, gbk, gb2312, latin1",
    },
    "doc_csv_failed": {
        "zh_CN": "[CSV提取] 提取失败: {exc}",
        "en_US": "[CSV Extract] Extraction failed: {exc}",
    },
    "doc_ocr_not_installed": {
        "zh_CN": "Tesseract OCR 未安装，无法进行 OCR 识别。请安装后重试，或设置 use_ocr_fallback=False 禁用 OCR 降级。",
        "en_US": "Tesseract OCR is not installed; cannot perform OCR recognition. Please install it and retry, or set use_ocr_fallback=False to disable OCR fallback.",
    },
    "doc_ocr_fallback_start": {
        "zh_CN": "[OCR降级] 使用 Tesseract OCR 本地识别: {name}",
        "en_US": "[OCR Fallback] Using Tesseract OCR for local recognition: {name}",
    },
    "doc_ocr_fallback_failed": {
        "zh_CN": "[OCR降级] OCR 识别失败: {exc}",
        "en_US": "[OCR Fallback] OCR recognition failed: {exc}",
    },
    "doc_ocr_fallback_error": {
        "zh_CN": "OCR 降级失败: {exc}",
        "en_US": "OCR fallback failed: {exc}",
    },
    "doc_ocr_pdf_start": {
        "zh_CN": "[OCR-PDF] 开始逐页 OCR: {name}",
        "en_US": "[OCR-PDF] Starting page-by-page OCR: {name}",
    },
    "doc_ocr_pdf_page_header": {
        "zh_CN": "--- 第 {page} 页 ---",
        "en_US": "--- Page {page} ---",
    },
    "doc_ocr_pdf_page_success": {
        "zh_CN": "[OCR-PDF] 第 {page} 页识别成功: {chars} 字符",
        "en_US": "[OCR-PDF] Page {page} recognized successfully: {chars} characters",
    },
    "doc_ocr_pdf_total": {
        "zh_CN": "[OCR-PDF] 总共识别 {pages} 页，{chars} 字符",
        "en_US": "[OCR-PDF] Total: {pages} page(s) recognized, {chars} characters",
    },
    "doc_ocr_image_start": {
        "zh_CN": "[OCR-图片] 开始识别: {name}",
        "en_US": "[OCR-Image] Starting recognition: {name}",
    },
    "doc_ocr_image_success": {
        "zh_CN": "[OCR-图片] 识别成功: {chars} 字符",
        "en_US": "[OCR-Image] Recognition succeeded: {chars} characters",
    },
    "doc_ocr_image_empty": {
        "zh_CN": "OCR 未能识别到任何文本",
        "en_US": "OCR failed to recognize any text",
    },
    "doc_ocr_other_start": {
        "zh_CN": "[OCR-其他] 尝试转换并识别: {name}",
        "en_US": "[OCR-Other] Attempting to convert and recognize: {name}",
    },
    "doc_ocr_other_libreoffice": {
        "zh_CN": "[OCR-其他] 使用 libreoffice: {cmd}",
        "en_US": "[OCR-Other] Using libreoffice: {cmd}",
    },
    "doc_ocr_other_convert_ok": {
        "zh_CN": "[OCR-其他] 转换成功，开始 OCR",
        "en_US": "[OCR-Other] Conversion succeeded; starting OCR",
    },
    "doc_ocr_other_convert_failed": {
        "zh_CN": "[OCR-其他] 转换失败: {exc}",
        "en_US": "[OCR-Other] Conversion failed: {exc}",
    },
    "doc_ocr_other_no_libreoffice": {
        "zh_CN": "[OCR-其他] 未找到 libreoffice",
        "en_US": "[OCR-Other] libreoffice not found",
    },
    "doc_ocr_other_pymupdf_ok": {
        "zh_CN": "[OCR-其他] PyMuPDF 可以直接打开，使用 PDF OCR",
        "en_US": "[OCR-Other] PyMuPDF can open the file directly; using PDF OCR",
    },
    "doc_ocr_other_pymupdf_failed": {
        "zh_CN": "[OCR-其他] PyMuPDF 也无法打开: {exc}",
        "en_US": "[OCR-Other] PyMuPDF also cannot open the file: {exc}",
    },
    "doc_ocr_other_unsupported": {
        "zh_CN": "无法处理文件类型: {ext}",
        "en_US": "Cannot process file type: {ext}",
    },
    "doc_file_not_found": {
        "zh_CN": "文件不存在: {path}",
        "en_US": "File does not exist: {path}",
    },
    "doc_not_a_file": {
        "zh_CN": "路径不是文件: {path}",
        "en_US": "Path is not a file: {path}",
    },
    "doc_unsupported_format": {
        "zh_CN": "不支持的文件格式: {ext}\n支持的格式: {supported}",
        "en_US": "Unsupported file format: {ext}\nSupported formats: {supported}",
    },
    "doc_extract_file": {
        "zh_CN": "提取文件: {name}",
        "en_US": "Extracting file: {name}",
    },
    "doc_unimplemented_type": {
        "zh_CN": "未实现的文件类型: {ext}",
        "en_US": "Unimplemented file type: {ext}",
    },
    "doc_parallel_start": {
        "zh_CN": "[并行提取] 开始处理 {count} 个文件 (最大并行数: {workers})",
        "en_US": "[Parallel Extract] Starting to process {count} file(s) (max workers: {workers})",
    },
    "doc_parallel_error": {
        "zh_CN": "[错误] 提取失败 {name}: {exc}",
        "en_US": "[Error] Extraction failed for {name}: {exc}",
    },
    "doc_parallel_progress": {
        "zh_CN": "\n[进度] {done}/{total} 完成: {name}",
        "en_US": "\n[Progress] {done}/{total} done: {name}",
    },
    "doc_parallel_done": {
        "zh_CN": "[并行提取] 全部完成，成功处理 {count} 个文件",
        "en_US": "[Parallel Extract] All done; successfully processed {count} file(s)",
    },
    "doc_save_json": {
        "zh_CN": "\n[保存] JSON 结果已保存到: {path}",
        "en_US": "\n[Save] JSON results saved to: {path}",
    },
    "doc_save_count": {
        "zh_CN": "[保存] 共 {count} 个文件的结果",
        "en_US": "[Save] Results for {count} file(s)",
    },
    "doc_no_files": {
        "zh_CN": "[错误] 没有找到可处理的文件",
        "en_US": "[Error] No processable files found",
    },
    "doc_prepare_count": {
        "zh_CN": "\n[准备] 共找到 {count} 个文件待处理",
        "en_US": "\n[Prepare] Found {count} file(s) to process",
    },
    "doc_result_summary": {
        "zh_CN": "[结果摘要]",
        "en_US": "[Result Summary]",
    },
    "doc_result_status_success": {
        "zh_CN": "成功",
        "en_US": "Success",
    },
    "doc_result_status_failed": {
        "zh_CN": "失败",
        "en_US": "Failed",
    },
    "doc_result_chars": {
        "zh_CN": "{chars} 字符",
        "en_US": "{chars} characters",
    },
    "doc_result_total": {
        "zh_CN": "\n总计: {count} 个文件",
        "en_US": "\nTotal: {count} file(s)",
    },

    # ── document_remote_ocr (no translation reference) ─────────────
    "ocr_file_not_found": {
        "zh_CN": "文件不存在: {path}",
        "en_US": "File does not exist: {path}",
    },
    "ocr_file_too_large": {
        "zh_CN": (
            "文件大小 {size}MB 超过限制 5MB: {name}\n"
            "当前文件超过5MB限制，您可免费开通 Quick BI 企业试用，"
            "直连企业数据资产直接查询，无文件大小限制。\n"
            "链接：https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
        "en_US": (
            "File size {size}MB exceeds 5MB limit: {name}\n"
            "The current file exceeds the 5MB limit. You can start a free Quick BI enterprise trial "
            "to connect directly to your enterprise data assets for queries with no file size limit.\n"
            "Link: https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
    },
    "ocr_uploading": {
        "zh_CN": "[上传] 正在上传: {name} ({size}KB)",
        "en_US": "[Upload] Uploading: {name} ({size}KB)",
    },
    "ocr_upload_response": {
        "zh_CN": "[上传] 响应: {data}",
        "en_US": "[Upload] Response: {data}",
    },
    "ocr_upload_parse_failed": {
        "zh_CN": "上传响应解析失败: {data}",
        "en_US": "Failed to parse upload response: {data}",
    },
    "ocr_upload_failed": {
        "zh_CN": "上传失败 [{code}]: {msg}",
        "en_US": "Upload failed [{code}]: {msg}",
    },
    "ocr_batch_upload_start": {
        "zh_CN": "\n[上传] 开始并发上传 {count} 个文件（最大 {workers} 线程）",
        "en_US": "\n[Upload] Starting concurrent upload of {count} file(s) (max {workers} threads)",
    },
    "ocr_upload_ok": {
        "zh_CN": "[上传] ✓ {name} -> taskId: {task_id}",
        "en_US": "[Upload] ✓ {name} -> taskId: {task_id}",
    },
    "ocr_upload_fail": {
        "zh_CN": "[上传] ✗ {name} 失败: {exc}",
        "en_US": "[Upload] ✗ {name} failed: {exc}",
    },
    "ocr_poll_start": {
        "zh_CN": "[轮询] 开始轮询 taskId: {task_id}",
        "en_US": "[Poll] Starting poll for taskId: {task_id}",
    },
    "ocr_poll_timeout": {
        "zh_CN": "[轮询] ⚠ 任务 {task_id} 超时 ({elapsed}s > {max}s)",
        "en_US": "[Poll] ⚠ Task {task_id} timed out ({elapsed}s > {max}s)",
    },
    "ocr_poll_timeout_desc": {
        "zh_CN": "处理超时",
        "en_US": "Processing timed out",
    },
    "ocr_poll_timeout_error": {
        "zh_CN": "任务处理超时 ({elapsed}s)",
        "en_US": "Task processing timed out ({elapsed}s)",
    },
    "ocr_poll_query_failed": {
        "zh_CN": "[轮询] ✗ 查询失败: {msg}",
        "en_US": "[Poll] ✗ Query failed: {msg}",
    },
    "ocr_poll_status": {
        "zh_CN": "[轮询] 任务 {task_id}... 状态: {status} ({desc}) - 已耗时 {elapsed}s",
        "en_US": "[Poll] Task {task_id}... status: {status} ({desc}) - elapsed {elapsed}s",
    },
    "ocr_poll_success": {
        "zh_CN": "[轮询] ✓ 任务 {task_id}... 解析成功",
        "en_US": "[Poll] ✓ Task {task_id}... parsing succeeded",
    },
    "ocr_poll_failed": {
        "zh_CN": "[轮询] ✗ 任务 {task_id}... 解析失败: {error}",
        "en_US": "[Poll] ✗ Task {task_id}... parsing failed: {error}",
    },
    "ocr_poll_not_supported": {
        "zh_CN": "[轮询] ⚠ 任务 {task_id}... 不支持的文件类型",
        "en_US": "[Poll] ⚠ Task {task_id}... unsupported file type",
    },
    "ocr_poll_exception": {
        "zh_CN": "[轮询] ✗ 查询异常: {exc}",
        "en_US": "[Poll] ✗ Query exception: {exc}",
    },
    "ocr_poll_no_valid": {
        "zh_CN": "[轮询] 没有有效的任务需要轮询",
        "en_US": "[Poll] No valid tasks to poll",
    },
    "ocr_poll_parallel_start": {
        "zh_CN": "\n[轮询] 开始并行轮询 {count} 个任务（最大 {workers} 线程）",
        "en_US": "\n[Poll] Starting parallel poll for {count} task(s) (max {workers} threads)",
    },
    "ocr_result_success": {
        "zh_CN": "[结果] ✓ {name}: 识别成功 ({chars} 字符)",
        "en_US": "[Result] ✓ {name}: Recognition succeeded ({chars} characters)",
    },
    "ocr_result_failed": {
        "zh_CN": "[结果] ✗ {name}: {status} - {error}",
        "en_US": "[Result] ✗ {name}: {status} - {error}",
    },
    "ocr_result_exception": {
        "zh_CN": "[结果] ✗ {name} 轮询异常: {exc}",
        "en_US": "[Result] ✗ {name} poll exception: {exc}",
    },
    "ocr_dir_not_found": {
        "zh_CN": "目录不存在: {path}",
        "en_US": "Directory does not exist: {path}",
    },
    "ocr_not_a_dir": {
        "zh_CN": "路径不是目录: {path}",
        "en_US": "Path is not a directory: {path}",
    },
    "ocr_scan_skip_large": {
        "zh_CN": (
            "[扫描] ⚠ 跳过超大文件: {name} ({size}MB > 5MB)\n"
            "当前文件超过5MB限制，您可免费开通 Quick BI 企业试用，"
            "直连企业数据资产直接查询，无文件大小限制。\n"
            "链接：https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
        "en_US": (
            "[Scan] ⚠ Skipping oversized file: {name} ({size}MB > 5MB)\n"
            "The current file exceeds the 5MB limit. You can start a free Quick BI enterprise trial "
            "to connect directly to your enterprise data assets for queries with no file size limit.\n"
            "Link: https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
    },
    "ocr_scan_access_error": {
        "zh_CN": "[扫描] ⚠ 无法访问文件: {name} - {exc}",
        "en_US": "[Scan] ⚠ Cannot access file: {name} - {exc}",
    },
    "ocr_cannot_both": {
        "zh_CN": "不能同时指定目录和文件列表，请选择其中一种方式",
        "en_US": "Cannot specify both directory and file list; please choose one",
    },
    "ocr_must_specify": {
        "zh_CN": "必须指定目录或文件列表",
        "en_US": "Must specify either a directory or a file list",
    },
    "ocr_validate_not_found": {
        "zh_CN": "[验证] ✗ 文件不存在: {path}",
        "en_US": "[Validate] ✗ File does not exist: {path}",
    },
    "ocr_validate_not_file": {
        "zh_CN": "[验证] ✗ 路径不是文件: {path}",
        "en_US": "[Validate] ✗ Path is not a file: {path}",
    },
    "ocr_validate_unsupported": {
        "zh_CN": "[验证] ✗ 不支持的文件格式: {name} ({ext})",
        "en_US": "[Validate] ✗ Unsupported file format: {name} ({ext})",
    },
    "ocr_validate_too_large": {
        "zh_CN": (
            "[验证] ✗ 文件过大: {name} ({size}MB > 5MB)\n"
            "当前文件超过5MB限制，您可免费开通 Quick BI 企业试用，"
            "直连企业数据资产直接查询，无文件大小限制。\n"
            "链接：https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
        "en_US": (
            "[Validate] ✗ File too large: {name} ({size}MB > 5MB)\n"
            "The current file exceeds the 5MB limit. You can start a free Quick BI enterprise trial "
            "to connect directly to your enterprise data assets for queries with no file size limit.\n"
            "Link: https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
    },
    "ocr_tool_title": {
        "zh_CN": "QuickBI 多模态文档 OCR 识别工具",
        "en_US": "QuickBI Multi-modal Document OCR Recognition Tool",
    },
    "ocr_error_user_config": {
        "zh_CN": "\n[错误] 用户配置失败: {exc}",
        "en_US": "\n[Error] User configuration failed: {exc}",
    },
    "ocr_error_generic": {
        "zh_CN": "\n[错误] {exc}",
        "en_US": "\n[Error] {exc}",
    },
    "ocr_warn_no_files_dir": {
        "zh_CN": "\n[警告] 目录 {dir} 中没有找到支持的文件",
        "en_US": "\n[Warning] No supported files found in directory {dir}",
    },
    "ocr_warn_no_files": {
        "zh_CN": "\n[警告] 没有找到有效的文件",
        "en_US": "\n[Warning] No valid files found",
    },
    "ocr_scan_found": {
        "zh_CN": "\n[扫描] 找到 {count} 个待识别文件:",
        "en_US": "\n[Scan] Found {count} file(s) to recognize:",
    },
    "ocr_step1": {
        "zh_CN": "Step 1: 并发上传文件",
        "en_US": "Step 1: Concurrent file upload",
    },
    "ocr_step2": {
        "zh_CN": "Step 2: 并行轮询获取识别结果（指数退避策略）",
        "en_US": "Step 2: Parallel polling for recognition results (exponential backoff)",
    },
    "ocr_save_ok": {
        "zh_CN": "\n[保存] ✓ JSON 结果已保存到: {path}",
        "en_US": "\n[Save] ✓ JSON results saved to: {path}",
    },
    "ocr_final_result": {
        "zh_CN": "最终结果（JSON 格式）",
        "en_US": "Final result (JSON format)",
    },
    "ocr_stats": {
        "zh_CN": "统计: 总计 {total} | 成功 {success} | 失败 {fail}",
        "en_US": "Stats: Total {total} | Success {success} | Failed {fail}",
    },

    # ── generate_excel (no translation reference) ──────────────────
    "excel_sheet_summary": {
        "zh_CN": "汇总",
        "en_US": "Summary",
    },
    "excel_header_group": {
        "zh_CN": "分类组",
        "en_US": "Category Group",
    },
    "excel_header_subtype": {
        "zh_CN": "子类型",
        "en_US": "Subtype",
    },
    "excel_header_file_count": {
        "zh_CN": "文件数量",
        "en_US": "File Count",
    },
    "excel_header_fields": {
        "zh_CN": "提取字段",
        "en_US": "Extracted Fields",
    },
    "excel_scan_time": {
        "zh_CN": "扫描时间",
        "en_US": "Scan Time",
    },
    "excel_total_files": {
        "zh_CN": "文件总数",
        "en_US": "Total Files",
    },
    "excel_save_ok": {
        "zh_CN": "[保存] ✓ Excel 结果已保存到: {path}",
        "en_US": "[Save] ✓ Excel results saved to: {path}",
    },
    "excel_file_not_found": {
        "zh_CN": "文件不存在: {path}",
        "en_US": "File does not exist: {path}",
    },
    "excel_group_other": {
        "zh_CN": "其他",
        "en_US": "Other",
    },

    # ── insight/q_insights ─────────────────────────────────────────
    "insight_excel_no_xlrd": {
        "zh_CN": "[Excel] 缺少 xlrd 依赖，请运行: pip install xlrd",
        "en_US": "[Excel] Missing xlrd dependency. Run: pip install xlrd",
    },
    "insight_excel_open_failed": {
        "zh_CN": "[Excel] 文件打开失败: {exc}",
        "en_US": "[Excel] Failed to open file: {exc}",
    },
    "insight_excel_no_data": {
        "zh_CN": "[Excel] 文件中没有有效数据",
        "en_US": "[Excel] No valid data found in the file",
    },
    "insight_excel_parsed": {
        "zh_CN": "[Excel] 解析完成，共 {sheets} 个 sheet，数据长度: {chars} 字符",
        "en_US": "[Excel] Parsing completed. Total {sheets} sheets, data length: {chars} characters",
    },
    "insight_excel_no_openpyxl": {
        "zh_CN": "[Excel] 缺少 openpyxl 依赖，请运行: pip install openpyxl",
        "en_US": "[Excel] Missing openpyxl dependency. Run: pip install openpyxl",
    },
    "insight_excel_size_exceeded": {
        "zh_CN": (
            "当前文件超过5MB限制（{name}，{size}MB），您可免费开通 Quick BI 企业试用，"
            "直连企业数据资产直接查询，无文件大小限制。\n"
            "链接：https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
        "en_US": (
            "The current file exceeds the 5MB limit ({name}, {size}MB). You can start a free Quick BI enterprise trial "
            "to connect directly to your enterprise data assets for queries with no file size limit.\n"
            "Link: https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205"
        ),
    },
    "insight_excel_not_found": {
        "zh_CN": "[Excel] 文件不存在: {path}",
        "en_US": "[Excel] File does not exist: {path}",
    },
    "insight_excel_parsing": {
        "zh_CN": "[Excel] 正在解析文件: {path}",
        "en_US": "[Excel] Parsing file: {path}",
    },
    "insight_excel_unsupported": {
        "zh_CN": "[Excel] 不支持的文件格式: {ext} 仅支持 .xls 和 .xlsx",
        "en_US": "[Excel] Unsupported file format: {ext} Only .xls and .xlsx are supported",
    },
    "insight_snapshot_poll": {
        "zh_CN": "[快照] 第 {attempt} 次轮询, 状态: {status}",
        "en_US": "[Snapshot] Poll #{attempt}, status: {status}",
    },
    "insight_snapshot_empty": {
        "zh_CN": "[快照] 状态为 success 但 resultMarkdownText 为空",
        "en_US": "[Snapshot] Status is success but resultMarkdownText is empty",
    },
    "insight_snapshot_ok": {
        "zh_CN": "[快照] 快照数据拉取成功，数据长度: {chars} 字符",
        "en_US": "[Snapshot] Snapshot data fetched successfully, data length: {chars} characters",
    },
    "insight_snapshot_failed": {
        "zh_CN": "[快照] 仪表板数据处理失败: {error}",
        "en_US": "[Snapshot] Dashboard data processing failed: {error}",
    },
    "insight_snapshot_failed_contact": {
        "zh_CN": "[快照] 仪表板数据处理失败，请联系产品服务团队。",
        "en_US": "[Snapshot] Dashboard data processing failed. Please contact the product service team.",
    },
    "insight_snapshot_unknown": {
        "zh_CN": "[快照] 未知状态: {status}，原始响应: {response}",
        "en_US": "[Snapshot] Unknown status: {status}; raw response: {response}",
    },
    "insight_snapshot_timeout": {
        "zh_CN": "[快照] 轮询超时 (等待 {seconds} 秒)",
        "en_US": "[Snapshot] Polling timed out (waited {seconds} seconds)",
    },
    "insight_question": {
        "zh_CN": "[小Q解读] 问题: {question}",
        "en_US": "[SmartQ Interpretation] Question: {question}",
    },
    "insight_source_excel": {
        "zh_CN": "[小Q解读] 数据来源: Excel 文件 ({path})",
        "en_US": "[SmartQ Interpretation] Data source: Excel file ({path})",
    },
    "insight_source_snapshot": {
        "zh_CN": "[小Q解读] 数据来源: 仪表板快照 ({works_id})",
        "en_US": "[SmartQ Interpretation] Data source: Dashboard snapshot ({works_id})",
    },
    "insight_snapshot_start": {
        "zh_CN": "[快照] 开始拉取仪表板快照数据...",
        "en_US": "[Snapshot] Starting to fetch dashboard snapshot data...",
    },
    "insight_no_source": {
        "zh_CN": "[小Q解读] 流程终止：必须指定 --excel-file、--dashboard-url 或 --works-id",
        "en_US": "[SmartQ Interpretation] Workflow terminated: you must specify --excel-file, --dashboard-url, or --works-id",
    },
    "insight_no_data": {
        "zh_CN": "[小Q解读] 流程终止：无法获取数据",
        "en_US": "[SmartQ Interpretation] Workflow terminated: unable to retrieve data",
    },
    "insight_source_dashboard_url": {
        "zh_CN": "[小Q解读] 数据来源: 仪表板/门户 URL ({url})",
        "en_US": "[SmartQ Interpretation] Data source: Dashboard / Portal URL ({url})",
    },
    "insight_url_parsing": {
        "zh_CN": "[URL 解析] 正在解析: {url}",
        "en_US": "[URL] Parsing: {url}",
    },
    "insight_url_resolved": {
        "zh_CN": "[URL 解析] 已定位仪表板 pageId={page_id}",
        "en_US": "[URL] Resolved dashboard pageId={page_id}",
    },
    "insight_url_parse_failed": {
        "zh_CN": "[URL 解析] 解析失败: {url}\n错误: {error}",
        "en_US": "[URL] Failed to parse: {url}\nError: {error}",
    },
    "insight_dashboard_locale": {
        "zh_CN": "[数据解读] 语言: {locale}",
        "en_US": "[Data Interpretation] Locale: {locale}",
    },
    "insight_interpretation_error": {
        "zh_CN": "[数据解读] 错误: {data}",
        "en_US": "[Data Interpretation] Error: {data}",
    },
    "insight_interpretation_failed": {
        "zh_CN": "[数据解读] 调用失败: {exc}",
        "en_US": "[Data Interpretation] Invocation failed: {exc}",
    },
    "insight_data_too_large": {
        "zh_CN": (
            "[小Q解读] 数据量超限：当前 {chars} 字符，上限 {limit} 字符。\n"
            "请先根据用户问题对数据进行过滤（只保留相关行和列），将结果另存为新文件后重新调用。\n"
            "若过滤后仍超限，请按行拆分为多份文件分批调用，最后汇总结果。"
        ),
        "en_US": (
            "[SmartQ Interpretation] Data exceeds limit: current {chars} chars, limit {limit} chars.\n"
            "Filter the data based on the user's question (keep only relevant rows and columns), save it as a new file, then re-invoke.\n"
            "If still over the limit after filtering, split the file by rows into multiple parts and invoke in batches; merge the results at the end."
        ),
    },
    "insight_interpretation_question": {
        "zh_CN": "[数据解读] 问题: {question}",
        "en_US": "[Data Interpretation] Question: {question}",
    },
    "insight_reasoning": {
        "zh_CN": "[推理过程]",
        "en_US": "[Reasoning Process]",
    },
    "insight_result": {
        "zh_CN": "[解读结果]",
        "en_US": "[Interpretation Result]",
    },
    "insight_no_result": {
        "zh_CN": "[解读结果] 没有收到任何解读内容",
        "en_US": "[Interpretation Result] No interpretation content was received",
    },
    "insight_done": {
        "zh_CN": "\n[完成] 数据解读完成",
        "en_US": "\n[Done] Data interpretation finished",
    },
    "insight_workflow_done": {
        "zh_CN": "[小Q解读] 解读流程完成",
        "en_US": "[SmartQ Interpretation] Interpretation workflow completed",
    },

    # ── report/create_chat ─────────────────────────────────────────
    "report_create_failed": {
        "zh_CN": "创建会话失败：{exc}",
        "en_US": "Failed to create session: {exc}",
    },
    "report_resources_file_error": {
        "zh_CN": "resources-file 必须是 resources 数组，或包含 resources 字段的 JSON 对象",
        "en_US": "resources-file must be a resources array, or a JSON object containing a resources field",
    },
    "report_resources_json_error": {
        "zh_CN": "resources-json 必须是 resources 数组，或包含 resources 字段的 JSON 对象",
        "en_US": "resources-json must be a resources array, or a JSON object containing a resources field",
    },

    # ── report/generate_report ─────────────────────────────────────
    "report_generate_failed": {
        "zh_CN": "生成报告失败：{exc}",
        "en_US": "Failed to generate report: {exc}",
    },

    # ── report/query_report_result ─────────────────────────────────
    "report_poll_failed": {
        "zh_CN": "轮询失败：{exc}",
        "en_US": "Polling failed: {exc}",
    },

    # ── report/upload_reference_file ───────────────────────────────
    "report_upload_failed": {
        "zh_CN": "上传文件失败：{exc}",
        "en_US": "File upload failed: {exc}",
    },

    # ── trial reminder (atexit milestones) ─────────────────────────
    "trial_reminder_day1": {
        "zh_CN": (
            "开启您的小 Q 超级分析之旅！我们看到您在通过 AI 寻找数据背后的真相，这很了不起。\n"
            "💡 其实，您可以更轻松\n"
            "目前的“文件模式”仍需您手动搬运数据。开通企业试用，直连企业存量数据资产，让分析变得更简单！\n"
            "🚀 限时加码\n"
            "上阿里云，将额外赠送 30 天全功能体验，解锁企业级安全管控与深度分析引擎，让 AI 洞察更准、更稳。\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n"
            "💬 点击下方链接进入交流群，获取最新资讯\n"
            "https://at.umtrack.com/r4Tnme"
        ),
        "en_US": (
            "Start your Super Q Analytics journey! We see you're using AI to uncover truths behind data — that's impressive.\n"
            "💡 Actually, it can be easier\n"
            "The current \"file mode\" still requires manual data handling. Start an enterprise trial to connect directly to your enterprise data assets for simpler analysis!\n"
            "🚀 Limited-time bonus\n"
            "Sign up on Alibaba Cloud for an extra 30-day full-feature experience, unlocking enterprise-grade security and deep analytics engine for more accurate AI insights.\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n"
            "💬 Click the link below to join our community for the latest updates\n"
            "https://at.umtrack.com/r4Tnme"
        ),
    },
    "trial_reminder_progress": {
        "zh_CN": (
            "恭喜！小 Q 超级分析助理已陪伴您 {days} 天，我们看到您在通过 AI 寻找数据背后的真相，这很了不起。\n"
            "💡 其实，您可以更轻松\n"
            "目前的“文件模式”仍需您手动搬运数据。开通企业试用，直连企业存量数据资产，让分析变得更简单！\n"
            "🚀 限时加码\n"
            "上阿里云，将额外赠送 30 天全功能体验，解锁企业级安全管控与深度分析引擎，让 AI 洞察更准、更稳。\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n"
            "💬 点击下方链接进入交流群，获取最新资讯\n"
            "https://at.umtrack.com/r4Tnme"
        ),
        "en_US": (
            "Congratulations! Super Q Analytics has been with you for {days} days. We see you're using AI to uncover truths behind data — that's impressive.\n"
            "💡 Actually, it can be easier\n"
            "The current \"file mode\" still requires manual data handling. Start an enterprise trial to connect directly to your enterprise data assets for simpler analysis!\n"
            "🚀 Limited-time bonus\n"
            "Sign up on Alibaba Cloud for an extra 30-day full-feature experience, unlocking enterprise-grade security and deep analytics engine for more accurate AI insights.\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n"
            "💬 Click the link below to join our community for the latest updates\n"
            "https://at.umtrack.com/r4Tnme"
        ),
    },
    "trial_reminder_expiring": {
        "zh_CN": (
            "小 Q 超级分析助理已陪伴您一个月，我们看到您在通过 AI 寻找数据背后的真相，这很了不起。\n"
            "💡 试用即将到期\n"
            "🚀 限时加码\n"
            "上阿里云，额外赠送 30 天全功能体验，解锁企业级安全管控与深度分析引擎，让 AI 洞察更准、更稳。\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n"
            "💬 点击下方链接进入交流群，获取最新资讯\n"
            "https://at.umtrack.com/r4Tnme"
        ),
        "en_US": (
            "Super Q Analytics has been with you for a month. We see you're using AI to uncover truths behind data — that's impressive.\n"
            "💡 Trial is expiring soon\n"
            "🚀 Limited-time bonus\n"
            "Sign up on Alibaba Cloud for an extra 30-day full-feature experience, unlocking enterprise-grade security and deep analytics engine for more accurate AI insights.\n"
            "https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205\n"
            "💬 Click the link below to join our community for the latest updates\n"
            "https://at.umtrack.com/r4Tnme"
        ),
    },
}

# ═══════════════════════════════════════════════════════════════════
# Locale state & helper functions
# ═══════════════════════════════════════════════════════════════════

_current_locale = "zh_CN"


def set_locale(locale: str):
    """Set the current locale for message output."""
    global _current_locale
    if locale in ("zh_CN", "en_US"):
        _current_locale = locale


def get_locale() -> str:
    """Return the current locale."""
    return _current_locale


def msg(key: str, **kwargs) -> str:
    """Get localized message by key, with optional format arguments."""
    entry = MESSAGES.get(key)
    if entry is None:
        return key
    text = entry.get(_current_locale, entry.get("zh_CN", key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text

