# 项目结构与运行架构

## 核心目录

```text
app/
├── agents/
│   ├── config/agents.yaml          # 主导师与五位可选领域专家注册表
│   ├── prompts/main_tutor.md       # 主导师角色提示词
│   ├── prompts/experts/*.md        # 各领域专家独立角色提示词
│   ├── models.py
│   ├── prompt_loader.py
│   ├── registry.py
│   └── service.py
├── api/
│   ├── agents.py                   # GET /api/experts
│   ├── auth.py
│   ├── chat.py                     # 主导师、单次专家咨询和草案能力
│   ├── curriculum.py               # 知识文件、权限、检索审计、导入导出
│   ├── flows.py
│   ├── session_files.py
│   └── sessions.py
├── db/
│   ├── database.py
│   ├── migrations.py
│   └── models.py
├── services/
│   ├── curriculum_knowledge_service.py
│   ├── curriculum_permission_service.py
│   ├── curriculum_vector_service.py
│   ├── rag_service.py
│   ├── prompt_service.py
│   └── draft_*.py
└── workflow/flows.py               # 仅保存阶段、目标和展示说明

frontend/src/
├── App.vue                         # 单次专家选择与文件权限配置界面
├── api.ts
├── types.ts
└── style.css
```

## Agent 执行关系

教学流程只有一个持续运行的主导师 `main_tutor`。当前阶段的完整 `direction` 会动态注入主导师提示词，因此流程阶段不绑定固定 Agent。

教师可在一次请求中传入 `expert_id`，临时咨询以下专家：

- `insect_agent`
- `nature_agent`
- `mathematics_teacher_agent`
- `safety_agent`
- `physics_teacher_agent`

执行优先级固定为：系统阶段动作、显式专家咨询、主导师草案能力、主导师普通引导。专家回答后不保留选择状态，也不追加主导师二次回复。

## 课程知识库权限

`curriculum_sources` 保存文件状态，`curriculum_chunks` 保存片段，`curriculum_source_agent_permissions` 保存文件与专家的多对多授权。新上传文件默认没有授权；管理员可以之后整体替换某个文件的专家列表。

专家检索链路：

```text
expert_id
→ 查询获权 source
→ SQL 在评分前过滤 BM25 片段
→ Chroma 使用 source where 条件过滤向量候选
→ 融合与重排
→ 注入专家提示词并写入 RAG 审计
```

主导师和草案能力不查询课程知识库。会话内普通参考资料仍对主导师和全部专家共享。

## 主要数据表

| 表 | 用途 |
| --- | --- |
| `users` / `auth_sessions` | 用户与登录会话 |
| `sessions` / `stage_outputs` | 教学会话、流程游标和阶段草案 |
| `messages` / `chat_turns` | 共享消息历史与回滚单元 |
| `session_files` | 会话级共享参考资料 |
| `curriculum_sources` | 课程知识文件与向量状态 |
| `curriculum_chunks` | 本地知识片段 |
| `curriculum_source_agent_permissions` | 文件级专家检索授权 |
| `rag_records` | 专家、授权来源、命中来源和评分审计 |

旧数据库中的 `users.chat_mode`、`app_settings` 和 `agent_conversations` 可以继续保留，但运行时不再读取或写入；新数据库不会创建这些旧结构。历史 `stage_expert` 消息仍兼容显示。

## API 摘要

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/experts` | 获取五位可选专家 |
| POST | `/api/sessions/{session_id}/chat` | 主导师或本轮专家对话 |
| POST | `/api/sessions/{session_id}/chat/{request_id}/cancel` | 中断当前请求 |
| GET/POST/DELETE | `/api/curriculum/files` | 查看、上传和删除知识文件 |
| PUT | `/api/curriculum/files/permissions` | 整体替换文件的专家权限 |
| GET | `/api/curriculum/retrievals` | 查看隔离检索审计 |
| GET/POST | `/api/curriculum/export`、`/api/curriculum/import` | v2 权限化导出与 v1/v2 导入 |

Agent 注册表默认路径是 `app/agents/config/agents.yaml`，可通过 `AGENT_CONFIG_PATH` 覆盖。
