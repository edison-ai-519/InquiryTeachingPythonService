# 双工作台授权隔离架构设计

## 目标

一个账号可被授权访问教师工作台、研学基地工作台或两者。两个工作台的会话、阶段产物、对话、文件、草案提案、导出和检索上下文必须严格隔离；流程、Agent 配置、知识源与图谱基础设施可以共享，但每次调用只能使用当前工作台获准的能力和知识权限。

## 范围与验收标准

1. 后端是工作台身份与访问范围的唯一可信来源；浏览器本地存储和请求参数只能表达用户已获授权的当前工作台，不能扩大权限。
2. 未获得某工作台授权的用户不能列出、创建、读取或修改该工作台会话，也不能访问其派生资源。
3. 任一会话的角色固定，流程、主导师、可选专家和知识检索均与会话角色一致。
4. 所有以 `session_id` 访问的接口通过同一个会话访问服务校验用户和工作台，跨工作台请求统一返回 404。
5. 同时具备两个授权的用户可切换工作台；切换取消进行中的请求并清空工作台相关前端状态。
6. 教师与研学界面、对话和导出使用对应业务文案。

## 授权模型

新增 `user_workspace_roles` 表：

```text
user_id            用户 ID
role_category      teacher | study_travel
created_at         授权创建时间
PRIMARY KEY (user_id, role_category)
```

`users.user_role` 保留为兼容字段和默认工作台。新用户默认获授 `teacher`；已有用户迁移时依据 `user_role` 写入对应授权。管理员可在现有用户管理入口或受保护的管理接口授予或撤销工作台角色，但不得撤销用户最后一个角色。`/api/auth/me` 返回：

```json
{
  "user_role": "teacher",
  "workspace_roles": ["teacher", "study_travel"]
}
```

## 工作台上下文与访问控制

定义固定角色集合及两个服务：

- `resolve_workspace_role(user, requested_role)`：验证请求角色格式，并确认其在 `user_workspace_roles` 中；缺省时使用 `user.user_role`。未授权返回 403。
- `get_owned_workspace_session(db, session_id, user, requested_role=None)`：查询会话归属；若传入角色与 `sessions.role_category` 不一致或用户无对应角色授权，返回 404。成功时返回会话及其不可伪造的角色。

需要角色参数的列表和创建接口使用 `resolve_workspace_role`；会话 ID 接口使用 `get_owned_workspace_session`。聊天、阶段推进及异步保存不得重新根据 `user.user_role` 推断角色，必须使用已验证会话的 `role_category`。

## 资源边界

| 资源 | 隔离规则 |
| --- | --- |
| 流程 | `flow.role_category` 必须与请求工作台相同；创建与切换流程均校验。 |
| 会话及阶段产物 | 创建时写入工作台；查询阶段产物同时按会话角色过滤。 |
| 消息、文件、草案提案、回滚、RAG、导出 | 经统一会话访问服务取得工作台角色；不接受单独伪造的角色字段。 |
| Agent | 主导师按会话角色选择；专家列表和专家选择必须匹配该角色。 |
| 知识权限 | 以会话角色和已验证专家 ID 查询 `curriculum_source_agent_permissions`。 |
| 图谱 | 图谱数据可共享；发起查询时使用会话角色验证专家，图谱上下文不可跨会话复用。 |

## API 约定

- `GET /api/auth/me` 增加 `workspace_roles`。
- `GET /api/flows`、`GET /api/experts`、`GET /api/sessions` 接收 `role_category`，由授权服务验证后过滤。
- `POST /api/sessions` 仍接收 `role_category`，但服务端以授权上下文验证角色和流程一致性。
- 所有会话 ID 路径允许可选的 `role_category` 用于显式工作台上下文；服务端不以该字段决定会话角色，只用于拒绝错配请求。
- `ChatRequest` 不携带可用于决定权限的角色字段。

## 前端行为

应用初始化后以 `/api/auth/me` 返回的 `workspace_roles` 建立可切换列表。当前工作台只在本地保存为偏好，启动时若该偏好已失去授权，则回退到后端默认角色。请求层将当前工作台传给列表和会话 ID 接口；遇到 403 或 404 时清理工作台状态并显示无权访问或资源不存在。

专家、流程、会话和草案在切换时一次性重新获取；进行中的聊天请求由 `AbortController` 取消。教师文案使用“教学方案/教师/主导师”，研学文案使用“研学方案/基地人员/研学主导师”，导出文件名同步区分。

## 数据迁移与兼容

迁移创建授权表并为现有用户补写一条由 `users.user_role` 决定的授权记录；空值或非法值回退为 `teacher`。已有会话保持当前 `role_category`，但启动迁移补齐会话拥有者缺少的对应授权，避免历史会话突然不可访问。为 `sessions(owner_user_id, role_category, updated_at)` 和授权表建立索引。

## 测试

后端集成测试覆盖：单角色用户被拒绝进入另一工作台；双角色用户可进入两者但跨角色会话 ID 被拒绝；错误流程、专家和知识权限被拒绝；聊天、文件、草案、导出、回滚及图谱均继承会话角色。前端类型检查覆盖工作台授权响应，组件测试或端到端测试覆盖无授权时隐藏切换入口、切换时状态清理和角色化文案。
