# 双工作台授权隔离 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让教师与研学基地工作台由后端授权控制，并对会话及全部派生资源实施强制隔离。

**Architecture:** 新增用户—工作台授权关系和统一的工作台访问服务。列表与创建请求先验证用户角色授权；所有会话 ID 路径从已验证会话取得角色，再以该角色限定流程、Agent、草案、文件、导出、对话及知识检索。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、Vue 3、TypeScript、pytest。

**Spec:** `docs/superpowers/specs/2026-10-12-workspace-authorization-isolation-design.md`

## Global Constraints

- 工作台角色仅允许 `teacher` 与 `study_travel`。
- 后端是角色授权和会话角色的唯一可信来源。
- 工作台不匹配的会话 ID 路径统一返回 404；未经授权的工作台列表/创建请求返回 403。
- 保留现有用户和会话数据：迁移后每个用户至少拥有一个角色授权。
- 不引入新第三方依赖。

## Review Focus

- 旧会话拥有者在迁移后是否得到对应角色授权并保持可访问。
- 双角色用户是否仍会通过省略或篡改 `role_category` 访问另一工作台会话。
- 聊天异步保存是否使用会话角色，而非登录用户默认角色。
- 研学会话是否仍能选到教师专家，或检索到教师专用知识源。
- 前端角色偏好失效时是否回退至后端授权角色并清空旧工作台状态。

---

### Task 1: 工作台授权模型与迁移

**Files:**
- Modify: `app/db/models.py`
- Modify: `app/db/migrations.py`
- Modify: `app/services/auth_service.py`
- Modify: `app/schemas.py`
- Test: `tests/test_workspace_authorization.py`

**Interfaces:**
- Produces: `UserWorkspaceRoleModel(user_id, role_category, created_at)` 和 `workspace_roles_for_user(db, user) -> list[str]`。

- [ ] **Step 1: 写入失败测试**

为默认注册用户只获授 `teacher`、`serialize_user()` 返回 `workspace_roles`、已有 `study_travel` 用户得到研学授权编写测试。

- [ ] **Step 2: 运行失败测试**

Run: `pytest tests/test_workspace_authorization.py -q`
Expected: FAIL，因为授权模型和返回字段不存在。

- [ ] **Step 3: 实现授权模型与兼容迁移**

新增复合主键授权模型；在启动迁移中创建表、从 `users.user_role` 回填授权、补齐现有会话拥有者的角色授权，并建立查询索引。注册用户创建教师授权；`serialize_user` 返回排序后的 `workspace_roles`。

- [ ] **Step 4: 运行测试并提交**

Run: `pytest tests/test_workspace_authorization.py -q`
Expected: PASS。

Commit: `feat: add workspace role authorization`

### Task 2: 统一授权与会话访问边界

**Files:**
- Modify: `app/services/session_access_service.py`
- Modify: `app/api/sessions.py`
- Modify: `app/api/flows.py`
- Test: `tests/test_workspace_authorization.py`

**Interfaces:**
- Consumes: `workspace_roles_for_user`。
- Produces: `resolve_workspace_role(db, user, requested_role)` 与 `get_owned_workspace_session(db, session_id, user, requested_role=None)`。

- [ ] **Step 1: 写入失败测试**

覆盖未授权角色列会话和创建会话返回 403；流程角色与请求角色不一致返回 400；双角色用户以错配角色读取会话返回 404；草案、消息、回滚、确认阶段和删除会话均拒绝错配角色。

- [ ] **Step 2: 运行失败测试**

Run: `pytest tests/test_workspace_authorization.py -q`
Expected: FAIL，现有服务只校验用户归属。

- [ ] **Step 3: 实现统一边界**

将 `get_owned_session` 替换为角色感知版本；会话 API 的每个 `session_id` 路径都接受可选角色上下文并调用该服务。创建会话从已验证角色写入会话，校验 `flow.role_category`；列表和流程接口先调用 `resolve_workspace_role`。

- [ ] **Step 4: 运行测试并提交**

Run: `pytest tests/test_workspace_authorization.py -q`
Expected: PASS。

Commit: `feat: enforce workspace boundaries for sessions`

### Task 3: Agent、聊天、知识权限和派生资源隔离

**Files:**
- Modify: `app/agents/registry.py`
- Modify: `app/api/agents.py`
- Modify: `app/api/chat.py`
- Modify: `app/api/session_files.py`
- Modify: `app/api/export.py`
- Modify: `app/api/knowledge.py`
- Modify: `app/services/context_service.py`
- Test: `tests/test_workspace_authorization.py`

**Interfaces:**
- Consumes: 任务 2 的会话访问服务与固定会话角色。

- [ ] **Step 1: 写入失败测试**

覆盖专家列表按角色过滤；聊天拒绝不同角色专家；草案生成主导师以会话角色选择；文件、导出和图谱候选请求拒绝角色错配；上下文只读取会话角色的阶段产物。

- [ ] **Step 2: 运行失败测试**

Run: `pytest tests/test_workspace_authorization.py -q`
Expected: FAIL，专家列表和聊天仍跨角色。

- [ ] **Step 3: 实现能力边界**

`AgentRegistry.experts()` 与 `selectable_expert()` 接收角色；专家 API 验证授权后过滤。聊天、文件、导出、图谱请求均经角色感知会话访问服务；聊天和异步保存从会话角色选择导师、专家、阶段产物和知识权限。上下文及导出使用角色化业务文案。

- [ ] **Step 4: 运行测试并提交**

Run: `pytest tests/test_workspace_authorization.py -q`
Expected: PASS。

Commit: `feat: isolate workspace agents and resources`

### Task 4: 前端授权工作台与全接口上下文

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/AppHeader.vue`
- Modify: `frontend/src/components/WorkspaceSidebar.vue`
- Modify: `frontend/src/components/DraftEditor.vue`
- Modify: `frontend/src/components/DraftReviewOverlay.vue`

**Interfaces:**
- Consumes: `AuthUser.workspace_roles` 和全部会话接口的可选 `role_category`。

- [ ] **Step 1: 写入失败类型检查或组件测试**

为授权角色数组、当前工作台选择和研学文案编写最小前端测试；若当前工程未配置组件测试，则以 `vue-tsc --noEmit` 证明旧类型不能满足新响应。

- [ ] **Step 2: 运行失败检查**

Run: `npm --prefix frontend run build`
Expected: FAIL 或类型缺失，直至前端适配新授权响应。

- [ ] **Step 3: 实现前端上下文**

从后端授权初始化工作台，隐藏未授权切换按钮；把当前角色传给所有会话、文件、草案、聊天、回滚、导出和图谱调用。切换时中止流式请求、清空会话相关状态并重新加载流程、专家、会话；按角色更新标题、空态和导出文件名。

- [ ] **Step 4: 运行构建并提交**

Run: `npm --prefix frontend run build`
Expected: PASS。

Commit: `feat: enforce authorized workspace switching`

### Task 5: 完整回归验证

**Files:**
- Modify: `tests/test_workspace_authorization.py`

- [ ] **Step 1: 扩充跨工作台回归测试**

用单角色和双角色测试客户端覆盖会话列表、创建、读取、聊天、文件、草案、回滚、导出、图谱、流程、专家及知识权限的正反路径。

- [ ] **Step 2: 运行后端测试**

Run: `pytest tests/test_workspace_authorization.py tests/test_dual_role.py tests/test_dual_role_draft.py -q`
Expected: PASS。

- [ ] **Step 3: 运行前端构建并提交**

Run: `npm --prefix frontend run build`
Expected: PASS。

Commit: `test: cover workspace authorization isolation`
