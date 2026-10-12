# 全量隔离架构设计：教师工作台 vs 研学基地工作台

## 目标

实现教师工作台和研学基地工作台的完全隔离，只有 Agent 和知识库共享。

## 架构原则

```
┌─────────────────────────────────────────────────────────────┐
│                      共享层                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Agents    │  │  Knowledge  │  │   Users     │        │
│  │  (共享)     │  │   (共享)    │  │  (共享)     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
┌───────▼───────┐                         ┌────────▼────────┐
│  教师工作台    │                         │ 研学基地工作台   │
│  role_category│                         │  role_category  │
│  = "teacher"  │                         │  = "study_travel"│
├───────────────┤                         ├─────────────────┤
│ 独立会话       │                         │ 独立会话         │
│ 独立流程       │                         │ 独立流程         │
│ 独立草案       │                         │ 独立草案         │
└───────────────┘                         └─────────────────┘
```

## 数据库变更

### SessionModel

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

### StageOutputModel

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

## API 变更

### 会话相关

- `POST /api/sessions` - 创建会话时增加 `role_category` 参数
- `GET /api/sessions` - 会话列表按 `role_category` 过滤
- `GET /api/sessions/{session_id}` - 获取会话时验证 `role_category`
- `PUT /api/sessions/{session_id}/stages/{stage_id}/draft` - 保存草案时增加 `role_category` 参数

### 流程相关

- `GET /api/flows` - 流程列表按 `role_category` 过滤

## 前端变更

### 角色切换

- 切换角色时，重新加载该角色下的会话列表
- 切换角色时，清空当前会话和草案状态

### API 调用

- 所有 API 调用增加 `role_category` 参数
- 从 `currentRole` 获取当前角色

## 数据库迁移

需要创建迁移脚本：
1. `sessions` 表增加 `role_category` 列
2. `stage_outputs` 表增加 `role_category` 列
3. 修改 `stage_outputs` 唯一约束

## 影响范围

### 后端文件

- `app/db/models.py` - 模型定义
- `app/api/sessions.py` - 会话 API
- `app/api/flows.py` - 流程 API
- `app/schemas.py` - 请求模型
- `app/workflow/flows.py` - 流程模板
- `app/services/` - 相关服务

### 前端文件

- `frontend/src/api.ts` - API 调用
- `frontend/src/App.vue` - 主应用
- `frontend/src/types.ts` - 类型定义
- `frontend/src/components/` - 相关组件

## 验证计划

1. 创建教师角色会话，验证只显示教师会话
2. 创建研学角色会话，验证只显示研学会话
3. 验证两个角色的草案内容完全隔离
4. 验证 Agent 和知识库共享
5. 验证流程按角色过滤
