# Day 5 - Agent 路由演进记录

## 当前状态

早期版本曾实现“固定阶段专家 + 主导师”的双层路由，并为阶段专家保存独立 conversation ID。该方案现已由统一主导师与可选领域专家架构取代，不再作为现行运行方式。

当前实现：

- `main_tutor` 负责全部流程阶段、草案和阶段推进。
- 教师可在单次请求中选择昆虫、自然生态、数学、安全伦理或物理专家。
- 专家只产生一条 `expert_advice`，结束后自动回到主导师。
- Agent 使用 `app/agents/config/agents.yaml` 注册，并从独立 Markdown 文件加载角色提示词。
- 课程知识文件由管理员上传后另行配置专家查询权限。
- 旧 `stage_expert` 消息可继续读取，旧聊天模式和 Agent conversation 状态停止使用。

现行实现与验收说明见 `docs/new_agent_architecture_guide.md`。
