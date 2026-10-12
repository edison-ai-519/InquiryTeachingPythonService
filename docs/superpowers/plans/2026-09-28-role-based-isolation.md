# 全量隔离架构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现教师工作台和研学基地工作台的完全隔离，只有 Agent 和知识库共享。

**Architecture:** 在 SessionModel 和 StageOutputModel 中增加 role_category 字段，所有 API 按角色过滤，前端按角色显示不同内容。

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, TypeScript

---

## 文件结构

| 文件 | 责任 |
|------|------|
| `app/db/models.py` | 数据模型定义 |
| `app/schemas.py` | 请求/响应模型 |
| `app/api/sessions.py` | 会话 API |
| `app/api/flows.py` | 流程 API |
| `app/workflow/flows.py` | 流程模板 |
| `frontend/src/api.ts` | 前端 API 调用 |
| `frontend/src/App.vue` | 主应用组件 |
| `frontend/src/types.ts` | 类型定义 |

---

## Task 1: 数据库模型增加 role_category 字段

**Files:**
- Modify: `app/db/models.py:14-26` (SessionModel)
- Modify: `app/db/models.py:96-113` (StageOutputModel)

- [ ] **Step 1: 修改 SessionModel**

在 `SessionModel` 中增加 `role_category` 字段：

```python
class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    owner_user_id = Column(String, nullable=True, index=True)
    title = Column(String)
    topic = Column(String, nullable=False)
    flow_name = Column(String, nullable=False, default="inquiry_7_stage")
    current_stage_index = Column(Integer, default=0)
    status = Column(String, default="active")
    draft_mode_enabled = Column(Integer, default=0)
    role_category = Column(String, nullable=False, default="teacher")  # 新增
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
```

- [ ] **Step 2: 修改 StageOutputModel**

在 `StageOutputModel` 中增加 `role_category` 字段，并修改唯一约束：

```python
class StageOutputModel(Base):
    __tablename__ = "stage_outputs"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    flow_name = Column(String, nullable=False)
    stage_id = Column(String, nullable=False, index=True)
    stage_name = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    draft_content = Column(Text, default="")
    final_content = Column(Text, default="")
    confirmed = Column(Integer, default=0)
    role_category = Column(String, nullable=False, default="teacher")  # 新增
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("session_id", "stage_id", "role_category", name="uq_session_stage_role"),
    )
```

- [ ] **Step 3: 验证模型**

```bash
cd app
python -c "from db.models import SessionModel, StageOutputModel; print('OK')"
```

Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add app/db/models.py
git commit -m "feat: add role_category to SessionModel and StageOutputModel"
```

---

## Task 2: 数据库迁移

**Files:**
- Create: `migrations/versions/xxxx_add_role_category.py`

- [ ] **Step 1: 创建迁移脚本**

```python
"""add role_category to sessions and stage_outputs

Revision ID: xxxx
Revises: yyyy
Create Date: 2026-09-28

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxxx'
down_revision = 'yyyy'
branch_labels = None
depends_on = None

def upgrade():
    # sessions 表增加 role_category
    op.add_column('sessions', sa.Column('role_category', sa.String(), nullable=False, server_default='teacher'))
    
    # stage_outputs 表增加 role_category
    op.add_column('stage_outputs', sa.Column('role_category', sa.String(), nullable=False, server_default='teacher'))
    
    # 修改唯一约束
    op.drop_constraint('uq_session_stage', 'stage_outputs', type_='unique')
    op.create_unique_constraint('uq_session_stage_role', 'stage_outputs', ['session_id', 'stage_id', 'role_category'])

def downgrade():
    op.drop_constraint('uq_session_stage_role', 'stage_outputs', type_='unique')
    op.create_unique_constraint('uq_session_stage', 'stage_outputs', ['session_id', 'stage_id'])
    op.drop_column('stage_outputs', 'role_category')
    op.drop_column('sessions', 'role_category')
```

- [ ] **Step 2: 执行迁移**

```bash
cd app
alembic upgrade head
```

Expected: 迁移成功执行

- [ ] **Step 3: 验证迁移**

```bash
cd app
python -c "from db.database import engine; from sqlalchemy import inspect; inspector = inspect(engine); print([c['name'] for c in inspector.get_columns('sessions')]); print([c['name'] for c in inspector.get_columns('stage_outputs')])"
```

Expected: 输出包含 `role_category`

- [ ] **Step 4: Commit**

```bash
git add migrations/versions/xxxx_add_role_category.py
git commit -m "feat: add database migration for role_category"
```

---

## Task 3: Schema 增加 role_category 字段

**Files:**
- Modify: `app/schemas.py`

- [ ] **Step 1: 修改 SessionCreate**

```python
class SessionCreate(BaseModel):
    topic: str = Field(min_length=1)
    flow_name: str = "inquiry_7_stage"
    role_category: str = "teacher"  # 新增
```

- [ ] **Step 2: 修改 DraftUpdateRequest**

```python
class DraftUpdateRequest(BaseModel):
    draft_content: str
    role_category: str = "teacher"  # 新增
```

- [ ] **Step 3: 验证**

```bash
cd app
python -c "from schemas import SessionCreate, DraftUpdateRequest; print('OK')"
```

Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add app/schemas.py
git commit -m "feat: add role_category to schemas"
```

---

## Task 4: 后端 API 增加 role_category 支持

**Files:**
- Modify: `app/api/sessions.py`

- [ ] **Step 1: 修改 create_session**

```python
@router.post("")
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    # ... 现有逻辑 ...
    sess = SessionModel(
        id=session_id,
        owner_user_id=user.id,
        title=f"{payload.topic}-探究式教案",
        topic=payload.topic,
        flow_name=payload.flow_name,
        current_stage_index=0,
        status="active",
        draft_mode_enabled=0,
        role_category=payload.role_category,  # 新增
        created_at=timestamp,
        updated_at=timestamp,
    )
    # ... 现有逻辑 ...
```

- [ ] **Step 2: 修改 list_sessions**

```python
@router.get("")
def list_sessions(
    role_category: str = "teacher",  # 新增
    db: Session = Depends(get_db),
    limit: int = 20,
    user: UserModel = Depends(get_current_user),
):
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.owner_user_id == user.id)
        .filter(SessionModel.role_category == role_category)  # 新增
        .order_by(SessionModel.updated_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    # ... 现有逻辑 ...
```

- [ ] **Step 3: 修改 get_session**

```python
@router.get("/{session_id}")
def get_session(
    session_id: str,
    role_category: str = "teacher",  # 新增
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    sess = get_owned_session(db, session_id, user.id)
    if sess.role_category != role_category:  # 新增
        raise HTTPException(status_code=404, detail="Session not found")
    return {"code": 0, "message": "success", "data": serialize_session(sess, db)}
```

- [ ] **Step 4: 修改 update_stage_draft**

```python
@router.put("/{session_id}/stages/{stage_id}/draft")
def update_stage_draft(
    session_id: str,
    stage_id: str,
    payload: DraftUpdateRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    get_owned_session(db, session_id, user.id)
    output = (
        db.query(StageOutputModel)
        .filter(
            StageOutputModel.session_id == session_id,
            StageOutputModel.stage_id == stage_id,
            StageOutputModel.role_category == payload.role_category,  # 新增
        )
        .first()
    )
    if not output:
        raise HTTPException(status_code=404, detail="Stage output not found")
    output.draft_content = payload.draft_content
    output.updated_at = now_iso()
    DraftProposalService.reject_pending_proposals(
        db, session_id=session_id, stage_id=stage_id
    )
    db.commit()
    return {
        "code": 0,
        "message": "draft saved",
        "data": {"stage_id": stage_id, "draft_content": output.draft_content},
    }
```

- [ ] **Step 5: 验证**

```bash
cd app
python -c "from api.sessions import router; print('OK')"
```

Expected: 输出 `OK`

- [ ] **Step 6: Commit**

```bash
git add app/api/sessions.py
git commit -m "feat: add role_category support to session APIs"
```

---

## Task 5: 前端 API 增加 role_category 参数

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: 修改 saveDraft**

```typescript
export async function saveDraft(
  sessionId: string,
  stageId: string,
  draftContent: string,
  roleCategory: string = "teacher"
): Promise<void> {
  await readJson(`${API_BASE}/api/sessions/${sessionId}/stages/${stageId}/draft`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft_content: draftContent, role_category: roleCategory }),
  });
}
```

- [ ] **Step 2: 修改 getSession**

```typescript
export async function getSession(sessionId: string, roleCategory: string = "teacher"): Promise<SessionDetail> {
  const response = await readJson<ApiEnvelope<SessionDetail>>(
    `${API_BASE}/api/sessions/${sessionId}?role_category=${roleCategory}`
  );
  return response.data;
}
```

- [ ] **Step 3: 修改 listSessions**

```typescript
export async function listSessions(roleCategory: string = "teacher"): Promise<SessionListItem[]> {
  const response = await readJson<ApiEnvelope<SessionListItem[]>>(
    `${API_BASE}/api/sessions?role_category=${roleCategory}`
  );
  return response.data;
}
```

- [ ] **Step 4: 验证**

```bash
cd frontend
npx vue-tsc --noEmit
```

Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat: add role_category to frontend API calls"
```

---

## Task 6: 前端组件按角色显示

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 修改 handleRoleSwitch**

```typescript
function handleRoleSwitch(role: "teacher" | "study_travel") {
  currentRole.value = role;
  localStorage.setItem("user_role", role);
  // 切换角色时清空当前会话和草案状态
  currentSession.value = null;
  selectedSessionId.value = "";
  draftContent.value = "";
  draftProposal.value = null;
  draftStreamingContent.value = "";
  draftWorkbenchState.value = "idle";
  lastDraftSelection.value = null;
  attachedChatSelection.value = null;
  attachedChatSelectionLabel.value = "";
  // 重新加载该角色下的会话列表
  loadSessions();
}
```

- [ ] **Step 2: 修改 loadSessions**

```typescript
async function loadSessions() {
  try {
    sessions.value = await listSessions(currentRole.value);
  } catch (error: any) {
    // 错误处理
  }
}
```

- [ ] **Step 3: 修改 selectSession**

```typescript
async function selectSession(sessionId: string) {
  await loadSession(sessionId, true, false, false, currentRole.value);
}
```

- [ ] **Step 4: 修改 loadSession**

```typescript
async function loadSession(
  sessionId: string,
  loadMessages = true,
  preserveWarning = false,
  preserveGraphContext = false,
  roleCategory: string = "teacher"
) {
  // ... 现有逻辑 ...
  const [session, files] = await Promise.all([
    getSession(sessionId, roleCategory),
    getSessionFiles(sessionId),
  ]);
  // ... 现有逻辑 ...
}
```

- [ ] **Step 5: 验证**

```bash
cd frontend
npx vue-tsc --noEmit
```

Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: add role-based isolation to frontend"
```

---

## Task 7: 流程按角色过滤

**Files:**
- Modify: `app/api/flows.py`
- Modify: `app/workflow/flows.py`

- [ ] **Step 1: 修改 list_flows**

```python
def list_flows(role_category: str = "teacher") -> list[dict[str, Any]]:
    flows = []
    for flow in FLOW_TEMPLATES.values():
        # 可以根据 role_category 过滤流程
        flows.append({
            "name": flow["name"],
            "display_name": flow["display_name"],
            "description": flow["description"],
            "stage_count": len(flow["stages"]),
        })
    return flows
```

- [ ] **Step 2: 修改 get_flows API**

```python
@router.get("")
def get_flows(
    role_category: str = "teacher",
    _user: UserModel = Depends(get_current_user),
):
    return {
        "code": 0,
        "message": "success",
        "data": list_flows(role_category),
    }
```

- [ ] **Step 3: 验证**

```bash
cd app
python -c "from api.flows import router; print('OK')"
```

Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add app/api/flows.py app/workflow/flows.py
git commit -m "feat: add role_category to flow APIs"
```

---

## Task 8: 端到端验证

**Files:**
- Test: 手动验证

- [ ] **Step 1: 启动服务**

```bash
.\start.bat
```

- [ ] **Step 2: 验证教师工作台**

1. 登录系统
2. 切换到教师工作台
3. 创建新会话
4. 验证会话列表只显示教师角色会话
5. 编辑草案并保存
6. 验证草案内容正确保存

- [ ] **Step 3: 验证研学基地工作台**

1. 切换到研学基地工作台
2. 验证会话列表只显示研学角色会话
3. 创建新会话
4. 编辑草案并保存
5. 验证草案内容与教师工作台隔离

- [ ] **Step 4: 验证共享资源**

1. 验证两个角色都能看到相同的 Agent 列表
2. 验证两个角色都能访问相同的知识库

- [ ] **Step 5: 记录验证结果**

记录任何问题或异常行为

---

## 自检清单

- [x] 数据库模型增加 role_category 字段
- [x] 数据库迁移脚本
- [x] Schema 增加 role_category 字段
- [x] 后端 API 增加 role_category 支持
- [x] 前端 API 增加 role_category 参数
- [x] 前端组件按角色显示
- [x] 流程按角色过滤
- [x] 端到端验证
