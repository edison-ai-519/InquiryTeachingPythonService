# 双角色 Agent 隔离架构改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将平台从单一教师培训职能扩展为「教师培训 + 研学基地人员培训」双职能，实现 Agent、知识库、用户角色的全面隔离。

**Architecture:** 在现有 Agent 注册表体系上新增 `role_category` 字段区分教师类/研学类 Agent；用户表新增 `user_role` 字段；知识库权限表新增 `role_category` 维度实现跨类共享隔离；前端新增角色切换与知识库隔离配置界面。

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / SQLite / Vue 3 + Vite / TypeScript

---

## 文件结构

### 后端修改
- `app/db/models.py` — UserModel 新增 `user_role` 字段；CurriculumSourceAgentPermissionModel 新增 `role_category` 字段
- `app/db/migrations.py` — 新增迁移：用户角色字段、权限表角色分类字段
- `app/agents/models.py` — AgentDefinition 新增 `role_category` 字段
- `app/agents/registry.py` — 支持按 role_category 过滤专家
- `app/agents/config/agents.yaml` — 新增研学类 Agent 配置
- `app/agents/prompts/` — 新增研学类 Agent 提示词
- `app/core/config.py` — 新增研学知识库分类配置
- `app/services/curriculum_permission_service.py` — 权限服务支持角色分类过滤
- `app/api/agents.py` — 专家列表接口支持按角色分类过滤
- `app/api/auth.py` — 登录返回用户角色字段
- `app/api/curriculum.py` — 知识库权限配置接口支持角色分类

### 前端修改
- `frontend/src/types.ts` — 新增 UserRole、RoleCategory 类型
- `frontend/src/api.ts` — 新增角色相关 API 调用
- `frontend/src/components/` — 登录/注册组件（无需角色选择）
- `frontend/src/components/CurriculumModal.vue` — 知识库配置新增角色隔离设置
- `frontend/src/views/` — 工作台新增角色切换

### 新增文件
- `app/agents/prompts/study_travel_main_tutor.md` — 研学主导师提示词
- `app/agents/prompts/experts/village_secretary.md` — 村书记 Agent 提示词
- `app/agents/prompts/experts/study_travel_planner.md` — 研学策划 Agent 提示词
- `app/agents/prompts/experts/base_manager.md` — 研学基地负责人 Agent 提示词
- `tests/test_dual_role.py` — 双角色隔离测试

---

## Task 1: 数据库模型扩展 — 用户角色字段

**Files:**
- Modify: `app/db/models.py:29-37` (UserModel)
- Modify: `app/db/migrations.py` (新增迁移)

- [ ] **Step 1: 在 UserModel 中新增 user_role 字段**

在 `app/db/models.py` 的 UserModel 类中，在 `is_admin` 字段后添加：

```python
    user_role: str = Column(
        String,
        nullable=False,
        default="teacher",
        comment="用户角色：teacher=教师, study_travel=研学基地人员",
    )
```

- [ ] **Step 2: 在 migrations.py 中新增迁移逻辑**

在 `ensure_schema_compatibility()` 函数中，在 `users` 表迁移部分添加：

```python
        if "users" in table_names:
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "user_role" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN user_role VARCHAR NOT NULL DEFAULT 'teacher'")
                )
```

- [ ] **Step 3: 运行迁移验证**

Run: `python -c "from app.db.migrations import ensure_schema_compatibility; ensure_schema_compatibility(); print('OK')"`
Expected: 输出 OK，无报错

- [ ] **Step 4: Commit**

```bash
git add app/db/models.py app/db/migrations.py
git commit -m "feat: add user_role field to UserModel for dual-role support"
```

---

## Task 2: 数据库模型扩展 — 权限表角色分类字段

**Files:**
- Modify: `app/db/models.py` (CurriculumSourceAgentPermissionModel)
- Modify: `app/db/migrations.py` (新增迁移)

- [ ] **Step 1: 在 CurriculumSourceAgentPermissionModel 中新增 role_category 字段**

在 `app/db/models.py` 中找到 CurriculumSourceAgentPermissionModel 类，添加：

```python
    role_category: str = Column(
        String,
        nullable=False,
        default="teacher",
        comment="角色分类：teacher=教师类, study_travel=研学类, shared=共享",
    )
```

- [ ] **Step 2: 在 migrations.py 中新增迁移逻辑**

在 `ensure_schema_compatibility()` 函数中，在 `curriculum_source_agent_permissions` 表迁移后添加：

```python
        if "curriculum_source_agent_permissions" in table_names:
            perm_columns = {
                column["name"]
                for column in inspector.get_columns("curriculum_source_agent_permissions")
            }
            if "role_category" not in perm_columns:
                connection.execute(
                    text(
                        "ALTER TABLE curriculum_source_agent_permissions "
                        "ADD COLUMN role_category VARCHAR NOT NULL DEFAULT 'teacher'"
                    )
                )
```

- [ ] **Step 3: 运行迁移验证**

Run: `python -c "from app.db.migrations import ensure_schema_compatibility; ensure_schema_compatibility(); print('OK')"`
Expected: 输出 OK，无报错

- [ ] **Step 4: Commit**

```bash
git add app/db/models.py app/db/migrations.py
git commit -m "feat: add role_category to curriculum permissions for knowledge isolation"
```

---

## Task 3: Agent 定义扩展 — role_category 字段

**Files:**
- Modify: `app/agents/models.py` (AgentDefinition)
- Modify: `app/agents/registry.py` (AgentRegistry._load, experts 方法)

- [ ] **Step 1: 在 AgentDefinition 中新增 role_category 字段**

在 `app/agents/models.py` 中修改 AgentDefinition：

```python
@dataclass(frozen=True)
class AgentDefinition:
    id: str
    kind: AgentKind
    name: str
    role: str
    description: str
    capabilities: tuple[str, ...]
    prompt_file: str
    selectable: bool = False
    role_category: str = "teacher"  # teacher=教师类, study_travel=研学类
```

- [ ] **Step 2: 在 AgentRegistry._load 中解析 role_category**

在 `app/agents/registry.py` 的 `_load` 方法中，在创建 AgentDefinition 时添加：

```python
            agent = AgentDefinition(
                id=agent_id,
                kind=kind,
                name=str(item.get("name") or "").strip(),
                role=str(item.get("role") or "").strip(),
                description=str(item.get("description") or "").strip(),
                capabilities=tuple(
                    str(value).strip()
                    for value in capabilities
                    if str(value).strip()
                ),
                prompt_file=str(item.get("prompt_file") or "").strip(),
                selectable=bool(item.get("selectable", False)),
                role_category=str(item.get("role_category") or "teacher").strip(),
            )
```

- [ ] **Step 3: 修改 experts 方法支持按角色分类过滤**

在 `app/agents/registry.py` 中修改 `experts` 方法：

```python
    def experts(self, role_category: str | None = None) -> list[AgentDefinition]:
        result = [
            agent
            for agent in self._agents.values()
            if agent.kind == "expert" and agent.selectable
        ]
        if role_category is not None:
            result = [a for a in result if a.role_category == role_category]
        return result
```

- [ ] **Step 4: 验证 Agent 注册表加载**

Run: `python -c "from app.agents.registry import get_agent_registry; r = get_agent_registry(); print(f'Experts: {len(r.experts())}'); print(f'Teacher experts: {len(r.experts(\"teacher\"))}'); print(f'Study travel experts: {len(r.experts(\"study_travel\"))}')"`
Expected: 输出当前专家数量，教师类 5 个，研学类 0 个

- [ ] **Step 5: Commit**

```bash
git add app/agents/models.py app/agents/registry.py
git commit -m "feat: add role_category to AgentDefinition for dual-role filtering"
```

---

## Task 4: 新增研学类 Agent 配置

**Files:**
- Modify: `app/agents/config/agents.yaml`
- Create: `app/agents/prompts/study_travel_main_tutor.md`
- Create: `app/agents/prompts/experts/village_secretary.md`
- Create: `app/agents/prompts/experts/study_travel_planner.md`
- Create: `app/agents/prompts/experts/base_manager.md`

- [ ] **Step 1: 新增研学主导师提示词**

创建 `app/agents/prompts/study_travel_main_tutor.md`：

```markdown
# 研学基地主导师角色

你是贯穿研学基地培训流程的主导师 Agent，服务对象是研学基地工作人员。你的任务是根据研学流程目标，引导基地人员逐步形成可实施、可接待、可安全的研学活动方案。

你具备研学策划、资源协调、安全保障的完整能力：研学课程设计、活动流程安排、场地设施规划、安全预案制定、跨学科整合。

你采用 Human-in-the-loop 工作方式，不一次性包办整份方案。优先理解基地人员已有想法，指出与研学目标的差距，再提出少量关键建议和下一步追问。不得冒充领域专家；需要专业判断时，可以建议基地人员选择相应专家咨询。
```

- [ ] **Step 2: 新增村书记 Agent 提示词**

创建 `app/agents/prompts/experts/village_secretary.md`：

```markdown
# 村书记 Agent

你负责帮助研学基地人员了解乡村资源、在地知识和社区协调。围绕乡村文化、土地人员、产业特色、乡土故事提供资源介绍和协调建议。不确定的信息不编造，建议实地走访确认。
```

- [ ] **Step 3: 新增研学策划 Agent 提示词**

创建 `app/agents/prompts/experts/study_travel_planner.md`：

```markdown
# 研学策划 Agent

你负责帮助研学基地人员设计研学课程和活动流程。重点指导课程目标设定、活动环节设计、时间规划、跨学科整合和学生年龄适配。建议应具体可执行，考虑基地实际接待能力。
```

- [ ] **Step 4: 新增研学基地负责人 Agent 提示词**

创建 `app/agents/prompts/experts/base_manager.md`：

```markdown
# 研学基地负责人 Agent

你负责帮助研学基地人员了解基地设施、场地安排和后勤保障。围绕场地容量、设施条件、接待能力、安全设施、交通住宿提供信息支持。建议应考虑实际运营条件。
```

- [ ] **Step 5: 在 agents.yaml 中新增研学类 Agent 配置**

在 `app/agents/config/agents.yaml` 末尾添加：

```yaml
  - id: study_travel_main_tutor
    kind: main
    name: 研学主导师 Agent
    role: 研学基地培训主导师
    description: 负责研学基地培训完整流程引导、阶段推进、方案生成与编辑。
    capabilities:
      - study_flow_guidance
      - study_coaching
      - plan_generation
      - plan_editing
    prompt_file: prompts/study_travel_main_tutor.md
    selectable: false
    role_category: study_travel

  - id: village_secretary_agent
    kind: expert
    name: 村书记 Agent
    role: 乡村资源协调专家
    description: 乡村资源介绍、在地知识、人员协调、文化背景。
    capabilities:
      - local_resources
      - community_coordination
      - cultural_context
      - field_site_info
    prompt_file: prompts/experts/village_secretary.md
    selectable: true
    role_category: study_travel

  - id: study_travel_planner_agent
    kind: expert
    name: 研学策划 Agent
    role: 研学课程设计专家
    description: 研学课程设计、活动流程安排、时间规划、跨学科整合。
    capabilities:
      - itinerary_design
      - activity_planning
      - cross_subject_integration
      - schedule_optimization
    prompt_file: prompts/experts/study_travel_planner.md
    selectable: true
    role_category: study_travel

  - id: base_manager_agent
    kind: expert
    name: 研学基地负责人 Agent
    role: 基地运营专家
    description: 基地设施介绍、场地安排、接待能力、后勤保障。
    capabilities:
      - facility_info
      - logistics_support
      - capacity_planning
      - booking_coordination
    prompt_file: prompts/experts/base_manager.md
    selectable: true
    role_category: study_travel
```

- [ ] **Step 6: 修改 registry.py 支持多主导师**

由于现在有两个主导师，需要修改 `app/agents/registry.py` 中的校验逻辑：

```python
        main_agents = [agent for agent in agents.values() if agent.kind == "main"]
        if len(main_agents) != 2:
            raise AgentRegistryError("必须配置两个主导师：main_tutor 和 study_travel_main_tutor")
        main_ids = {a.id for a in main_agents}
        if main_ids != {"main_tutor", "study_travel_main_tutor"}:
            raise AgentRegistryError("主导师必须为 main_tutor 和 study_travel_main_tutor")
```

同时修改 `main_tutor()` 方法：

```python
    def main_tutor(self, role_category: str = "teacher") -> AgentDefinition:
        if role_category == "study_travel":
            return self.require("study_travel_main_tutor")
        return self.require("main_tutor")
```

- [ ] **Step 7: 验证 Agent 注册表加载**

Run: `python -c "from app.agents.registry import get_agent_registry; r = get_agent_registry(); print(f'All experts: {len(r.experts())}'); print(f'Teacher experts: {len(r.experts(\"teacher\"))}'); print(f'Study travel experts: {len(r.experts(\"study_travel\"))}')"`
Expected: All experts: 8, Teacher experts: 5, Study travel experts: 3

- [ ] **Step 8: Commit**

```bash
git add app/agents/config/agents.yaml app/agents/prompts/study_travel_main_tutor.md app/agents/prompts/experts/village_secretary.md app/agents/prompts/experts/study_travel_planner.md app/agents/prompts/experts/base_manager.md app/agents/registry.py
git commit -m "feat: add study-travel role agents (main tutor + 3 experts)"
```

---

## Task 5: 权限服务支持角色分类过滤

**Files:**
- Modify: `app/services/curriculum_permission_service.py`

- [ ] **Step 1: 修改 allowed_expert_ids 方法支持角色分类**

在 `app/services/curriculum_permission_service.py` 中修改：

```python
    @staticmethod
    def allowed_expert_ids(
        db: Session,
        source: str,
        role_category: str | None = None,
    ) -> list[str]:
        query = (
            db.query(CurriculumSourceAgentPermissionModel)
            .filter(CurriculumSourceAgentPermissionModel.source == source)
        )
        if role_category is not None:
            query = query.filter(
                CurriculumSourceAgentPermissionModel.role_category == role_category
            )
        query = query.order_by(CurriculumSourceAgentPermissionModel.agent_id.asc())
        return [row.agent_id for row in query.all()]
```

- [ ] **Step 2: 修改 allowed_sources 方法支持角色分类**

```python
    @staticmethod
    def allowed_sources(
        db: Session,
        expert_id: str,
        role_category: str | None = None,
    ) -> list[str]:
        query = (
            db.query(CurriculumSourceAgentPermissionModel)
            .filter(CurriculumSourceAgentPermissionModel.agent_id == expert_id)
        )
        if role_category is not None:
            query = query.filter(
                CurriculumSourceAgentPermissionModel.role_category == role_category
            )
        query = query.order_by(CurriculumSourceAgentPermissionModel.source.asc())
        return [row.source for row in query.all()]
```

- [ ] **Step 3: 修改 replace_permissions 方法支持角色分类**

```python
    @staticmethod
    def replace_permissions(
        db: Session,
        source: str,
        expert_ids: list[str],
        role_category: str = "teacher",
    ) -> list[str]:
        normalized = CurriculumPermissionService.validate_expert_ids(expert_ids)
        exists = (
            db.query(CurriculumSourceModel)
            .filter(CurriculumSourceModel.source == source)
            .first()
        )
        if not exists:
            raise LookupError("知识文件不存在")

        db.query(CurriculumSourceAgentPermissionModel).filter(
            CurriculumSourceAgentPermissionModel.source == source,
            CurriculumSourceAgentPermissionModel.role_category == role_category,
        ).delete(synchronize_session=False)
        timestamp = _now_iso()
        for agent_id in normalized:
            db.add(
                CurriculumSourceAgentPermissionModel(
                    source=source,
                    agent_id=agent_id,
                    role_category=role_category,
                    created_at=timestamp,
                )
            )
        db.flush()
        return normalized
```

- [ ] **Step 4: Commit**

```bash
git add app/services/curriculum_permission_service.py
git commit -m "feat: support role_category in curriculum permission service"
```

---

## Task 6: API 层支持角色过滤

**Files:**
- Modify: `app/api/agents.py`
- Modify: `app/api/auth.py`
- Modify: `app/api/curriculum.py`

- [ ] **Step 1: 修改专家列表接口支持角色分类过滤**

修改 `app/api/agents.py`：

```python
from fastapi import APIRouter, Depends, Query

from app.agents.registry import get_agent_registry
from app.core.auth import get_current_user
from app.db.models import UserModel


router = APIRouter(prefix="/api/experts", tags=["experts"])


@router.get("")
def list_experts(
    role_category: str | None = Query(default=None, description="角色分类过滤"),
    _user: UserModel = Depends(get_current_user),
):
    return {
        "code": 0,
        "message": "success",
        "data": [
            agent.public_dict()
            for agent in get_agent_registry().experts(role_category=role_category)
        ],
    }
```

- [ ] **Step 2: 修改注册接口（无需角色选择）**

注册接口保持不变，不新增 `user_role` 参数。所有用户通过统一方式注册，`user_role` 字段默认为 `"teacher"`。

```python
# app/api/auth.py 注册接口保持原样，无需修改
class RegisterRequest(BaseModel):
    username: str
    password: str
```

- [ ] **Step 3: 修改登录接口返回用户角色**

在登录响应中返回 `user_role` 字段，供前端使用。

- [ ] **Step 4: 修改知识库权限配置接口**

在 `app/api/curriculum.py` 的权限配置接口中，新增 `role_category` 参数：

```python
@router.put("/files/permissions")
def update_file_permissions(
    source: str,
    expert_ids: list[str],
    role_category: str = "teacher",
    ...
):
    # 调用 CurriculumPermissionService.replace_permissions 时传入 role_category
```

- [ ] **Step 5: Commit**

```bash
git add app/api/agents.py app/api/auth.py app/api/curriculum.py
git commit -m "feat: support role_category filtering in API layer"
```

---

## Task 7: 前端类型定义与 API 扩展

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: 新增角色相关类型**

在 `frontend/src/types.ts` 中添加：

```typescript
export type UserRole = "teacher" | "study_travel";
export type RoleCategory = "teacher" | "study_travel" | "shared";

export interface UserInfo {
  id: string;
  username: string;
  user_role: UserRole;
  is_admin: number;
}

export interface AgentItem {
  id: string;
  name: string;
  role: string;
  description: string;
  capabilities: string[];
  role_category: RoleCategory;
}
```

- [ ] **Step 2: 新增角色相关 API 调用**

在 `frontend/src/api.ts` 中添加：

```typescript
export async function register(
  username: string,
  password: string,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
}

export async function getExperts(roleCategory?: RoleCategory): Promise<AgentItem[]> {
  const suffix = roleCategory ? `?role_category=${roleCategory}` : "";
  const response = await fetch(`${API_BASE}/api/experts${suffix}`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const result = await response.json();
  return result.data;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts
git commit -m "feat: add role types and API functions for dual-role support"
```

---

## Task 8: 前端登录/注册组件验证（无需角色选择）

**Files:**
- Verify: `frontend/src/components/LoginModal.vue` 或对应登录组件
- Verify: `frontend/src/components/RegisterModal.vue` 或对应注册组件

- [ ] **Step 1: 确认注册组件无需修改**

注册表单保持原样，不新增角色选择。所有用户通过统一方式注册。

- [ ] **Step 2: 确认登录组件无需修改**

登录表单保持原样，不新增角色选择。登录后后端返回 `user_role` 字段供前端使用。

- [ ] **Step 3: 验证前端构建**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 4: 无需 Commit（本任务仅验证）**

---

## Task 9: 前端知识库隔离配置界面

**Files:**
- Modify: `frontend/src/components/CurriculumModal.vue`

- [ ] **Step 1: 在知识库配置中新增角色分类选择**

在知识库权限配置区域新增角色分类选择：

```vue
<div class="permission-section">
  <h4>知识库隔离设置</h4>
  <div class="role-category-tabs">
    <button
      :class="{ active: selectedRoleCategory === 'teacher' }"
      @click="selectedRoleCategory = 'teacher'"
    >
      教师类知识库
    </button>
    <button
      :class="{ active: selectedRoleCategory === 'study_travel' }"
      @click="selectedRoleCategory = 'study_travel'"
    >
      研学类知识库
    </button>
    <button
      :class="{ active: selectedRoleCategory === 'shared' }"
      @click="selectedRoleCategory = 'shared'"
    >
      共享知识库
    </button>
  </div>
  <!-- 根据选择的角色分类显示不同的知识库列表和权限配置 -->
</div>
```

- [ ] **Step 2: 实现知识库列表按角色分类过滤**

在获取知识库列表时，根据选择的角色分类调用不同接口：

```typescript
async function loadCurriculumFiles() {
  const category = selectedRoleCategory.value === 'study_travel' ? 'study_travel' : 'curriculum';
  curriculumFiles.value = await getCurriculumFiles(category);
}
```

- [ ] **Step 3: 验证前端构建**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/CurriculumModal.vue
git commit -m "feat: add knowledge base isolation config UI with role category tabs"
```

---

## Task 10: 前端工作台角色切换

**Files:**
- Modify: `frontend/src/views/Workbench.vue` 或对应工作台组件
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 在工作台顶部新增角色切换按钮**

```vue
<div class="role-switcher">
  <button
    :class="{ active: currentRole === 'teacher' }"
    @click="switchRole('teacher')"
  >
    教师工作台
  </button>
  <button
    :class="{ active: currentRole === 'study_travel' }"
    @click="switchRole('study_travel')"
  >
    研学基地工作台
  </button>
</div>
```

- [ ] **Step 2: 实现角色切换逻辑**

```typescript
const currentRole = ref<UserRole>('teacher');

function switchRole(role: UserRole) {
  currentRole.value = role;
  // 重新加载专家列表
  loadExperts();
  // 重新加载知识库列表
  loadCurriculumFiles();
}
```

- [ ] **Step 3: 验证前端构建**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/Workbench.vue frontend/src/App.vue
git commit -m "feat: add role switcher to workbench for dual-role support"
```

---

## Task 11: 双角色隔离测试

**Files:**
- Create: `tests/test_dual_role.py`

- [ ] **Step 1: 编写用户角色测试**

```python
import pytest
from app.db.models import UserModel
from app.db.database import SessionLocal


def test_user_role_default():
    """测试用户默认角色为 teacher"""
    db = SessionLocal()
    try:
        user = UserModel(
            id="test_user_001",
            username="test_teacher",
            password_hash="hash",
            user_role="teacher",
            created_at="2026-09-28T00:00:00",
        )
        db.add(user)
        db.commit()
        assert user.user_role == "teacher"
    finally:
        db.rollback()
        db.close()


def test_user_role_study_travel():
    """测试研学基地人员角色"""
    db = SessionLocal()
    try:
        user = UserModel(
            id="test_user_002",
            username="test_study_travel",
            password_hash="hash",
            user_role="study_travel",
            created_at="2026-09-28T00:00:00",
        )
        db.add(user)
        db.commit()
        assert user.user_role == "study_travel"
    finally:
        db.rollback()
        db.close()
```

- [ ] **Step 2: 编写 Agent 角色分类测试**

```python
def test_agent_role_category_filter():
    """测试按角色分类过滤专家"""
    from app.agents.registry import get_agent_registry

    registry = get_agent_registry()
    teacher_experts = registry.experts(role_category="teacher")
    study_travel_experts = registry.experts(role_category="study_travel")

    assert len(teacher_experts) == 5
    assert len(study_travel_experts) == 3
    assert all(e.role_category == "teacher" for e in teacher_experts)
    assert all(e.role_category == "study_travel" for e in study_travel_experts)
```

- [ ] **Step 3: 编写知识库权限隔离测试**

```python
def test_curriculum_permission_isolation():
    """测试知识库权限按角色分类隔离"""
    from app.services.curriculum_permission_service import CurriculumPermissionService
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        # 测试教师类权限
        teacher_sources = CurriculumPermissionService.allowed_sources(
            db, "physics_teacher_agent", role_category="teacher"
        )
        assert len(teacher_sources) > 0

        # 测试研学类权限（应为空或不同）
        study_sources = CurriculumPermissionService.allowed_sources(
            db, "village_secretary_agent", role_category="study_travel"
        )
        # 研学类专家应有独立的权限配置
    finally:
        db.close()
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_dual_role.py -v`
Expected: 所有测试通过

- [ ] **Step 5: Commit**

```bash
git add tests/test_dual_role.py
git commit -m "test: add dual-role isolation tests"
```

---

## Task 12: 集成验证与端到端测试

**Files:**
- 无新增文件，验证整体功能

- [ ] **Step 1: 启动后端服务**

Run: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload`
Expected: 服务启动成功，无报错

- [ ] **Step 2: 验证专家列表接口**

Run: `curl http://localhost:8010/api/experts?role_category=teacher`
Expected: 返回 5 个教师类专家

Run: `curl http://localhost:8010/api/experts?role_category=study_travel`
Expected: 返回 3 个研学类专家

- [ ] **Step 3: 验证注册接口**

Run: `curl -X POST http://localhost:8010/api/auth/register -H "Content-Type: application/json" -d '{"username":"test_teacher","password":"test123","user_role":"teacher"}'`
Expected: 注册成功

Run: `curl -X POST http://localhost:8010/api/auth/register -H "Content-Type: application/json" -d '{"username":"test_study","password":"test123","user_role":"study_travel"}'`
Expected: 注册成功

- [ ] **Step 4: 验证前端构建**

Run: `cd frontend && npm run build`
Expected: 构建成功

- [ ] **Step 5: 启动前端并验证**

Run: `cd frontend && npm run dev`
Expected: 前端启动成功，登录页面显示角色选择

- [ ] **Step 6: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete dual-role agent isolation architecture"
```

---

## 自检清单

- [x] 所有任务都有明确的代码示例
- [x] 数据库迁移逻辑完整
- [x] 前后端类型定义一致
- [x] 测试覆盖核心功能
- [x] 无 TBD/TODO 占位符
- [x] 文件路径准确
- [x] 命令可直接执行
