# 主导师与可选领域专家架构指南

## 设计目标

本项目不再把教学阶段与固定专家绑定。`main_tutor` 是唯一负责流程推进、阶段引导、总结和草案操作的 Agent；领域专家只在教师显式选择的单次请求中提供专业建议。

这种组织方式把“教学流程责任”和“专业咨询能力”分开：阶段变化只改变主导师收到的阶段目标，不改变对话主体；增加或调整专业角色时也不需要修改流程定义。

## 注册与提示词

注册表位于 `app/agents/config/agents.yaml`。每个 Agent 包含：

- `id`
- `kind`: `main` 或 `expert`
- `name`
- `role`
- `description`
- `capabilities`
- `prompt_file`
- `selectable`

角色正文独立保存在 `app/agents/prompts/`。注册表加载时会检查 ID 重复、角色类型、唯一主导师、可选择状态、提示词路径和空文件。可通过 `AGENT_CONFIG_PATH` 指向另一份 YAML；提示词仍必须位于项目 Agent 目录内，避免读取越界。

## 请求路由

`POST /api/sessions/{session_id}/chat` 的优先级：

1. 系统阶段动作；
2. 请求中显式传入的 `expert_id`；
3. 主导师草案生成或局部编辑；
4. 主导师普通引导。

专家选择不写入用户、会话或独立 conversation 状态。合法专家只产生 `expert_advice` 回复；不传 `expert_id` 时产生 `main_tutor` 回复。专家消息与主导师消息进入同一会话历史，因此后续主导师能够引用先前建议。

旧的 `stage_expert` 消息仅用于历史兼容，不再新增。

## 文件级 RAG 授权

Agent YAML 不保存知识库归属。管理员先上传文件，系统完成解析、切片和向量化，新文件此时的 `allowed_expert_ids` 为空。之后管理员通过 `PUT /api/curriculum/files/permissions` 为一个文件选择零到多个专家。

权限表为 `curriculum_source_agent_permissions`，主键是 `(source, agent_id)`，文件删除时级联删除授权。`agent_id` 由 YAML 注册表校验，只允许 `kind=expert` 且 `selectable=true` 的角色。

检索隔离发生在候选召回之前：

- BM25 的 SQL 查询只加载获权 `source` 的片段；
- Chroma 查询用单文件等值或多文件 `$in` 的 `where` 条件；
- 向量不可用而降级 BM25 时仍使用相同文件范围；
- 无获权文件时跳过课程 RAG，不创建召回审计；
- 主导师与草案路径始终跳过课程 RAG。

会话内由教师上传的普通参考资料属于会话共享上下文，不受课程知识文件授权约束。

## 迁移与交换格式

首次创建权限迁移标记时，现有物理课标授权给 `physics_teacher_agent`，数学课标授权给 `mathematics_teacher_agent`。迁移使用独立标记保证管理员后来撤销权限时不会被重新添加，现有片段与向量保持不变。

知识库导出版本为 2，每个 source 带 `allowed_expert_ids`。版本 2 导入会先验证全部文件、片段、校验和与专家 ID，再写入数据；任何校验失败均回滚。版本 1 继续支持，但导入文件默认未授权。

## 扩展新专家

1. 在 `app/agents/prompts/experts/` 新建角色提示词。
2. 在 `agents.yaml` 注册唯一 ID，设置 `kind: expert` 与 `selectable: true`。
3. 通过 `/api/experts` 确认前端可见。
4. 由管理员在知识库界面按文件授权。
5. 添加能力边界、非法配置和检索隔离测试。

第一版所有 Agent 共用当前 LLM 配置。未来如需为专家配置不同知识库或模型，应继续保持文件权限是数据库事实源，避免把动态授权写回 YAML。
