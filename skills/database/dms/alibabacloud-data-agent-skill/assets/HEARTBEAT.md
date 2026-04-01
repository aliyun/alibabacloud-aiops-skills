## Data Agent 自动监控

当 HEARTBEAT 触发时，按照以下步骤 chain-of-thought 执行：

1. 扫描目录：`dms-data-agent/sessions/*`（或你的实际 sessions 路径）
   - 使用 file_list 或 ls 列出所有子目录（每个对应一个 session_id）

2. 对每个 session 检查状态：
   - 读 `status.txt`
     - 如果 "running"：
       - 读 `progress.log` 把新的进展告诉用户，尤其是计划执行的步骤内容
     - 如果 "completed"：
       - 读 reports/ 目录或 使用report子命令获取总结文件， Markdown 格式的内容给客户呈现， html可以通过浏览器打开。
     - 如果 "failed"：
       - 读 error.log，总结原因
       - 建议："请用 attach {id} 重试或检查日志"

3. 通知规则：
   - 需要及时的反馈阶段性洞察给客户，以及里程碑首次到达、完成或失败时发消息。
   - 使用 send_message tool 或当前 channel（如 Telegram/WhatsApp）推送
   - 避免重复：记录上次计划执行的步骤结论（可写到 SESSION-STATE.md 或专用 data-agent-state.md）

4. 如果无新通知内容：
   - 安静结束 turn（回复 HEARTBEAT_OK，gateway 会自动丢弃）

优先使用 isolated agentTurn 执行检查（不干扰主对话）。