# 双工作台草案切换设计方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现教师工作台与研学基地工作台的草案类型自动切换，角色决定草案模板。

**Architecture:** 用户通过顶部角色切换按钮选择工作台 → 每个工作台绑定独立主导师 Agent → 草案生成时根据当前工作台角色选择对应提示词模板 → 输出对应类型的草案。

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / SQLite / Vue 3 + Vite / TypeScript

---

## 核心设计

```
用户切换工作台
    ↓
教师工作台 → main_tutor → 教案草案（教学目标、课堂活动、学生探究）
研学基地工作台 → study_travel_main_tutor → 研学方案草案（接待流程、课程设计、场地安排）
```

**核心逻辑**：
- 用户通过顶部角色切换按钮选择工作台
- 每个工作台绑定独立的主导师 Agent
- 草案生成时自动根据当前工作台角色选择对应提示词模板
- 不需要额外的"草案类型"开关 — 角色已经决定了草案类型

**数据隔离**：
- 教师工作台：看到教师类专家 + 教师类知识库 + 教案草案
- 研学基地工作台：看到研学类专家 + 研学类知识库 + 研学方案草案

---

## 文件结构

### 后端修改
- `app/services/prompt_service.py` — 新增 `role_category` 参数，研学类使用独立提示词模板
- `app/services/draft_generate_service.py` — `stream_candidate` 传递 `role_category`
- `app/services/llm_service.py` — mock 数据按角色区分
- `app/api/chat.py` — 调用草案服务时传入当前用户角色

### 前端修改
- `frontend/src/components/AppHeader.vue` — 角色切换时传递 `role_category` 到草案生成
- `frontend/src/api.ts` — 草案生成请求携带 `role_category`

---

## Task 1: 提示词服务支持角色分类

**Files:**
- Modify: `app/services/prompt_service.py`

- [ ] **Step 1: 修改 `build_draft_generate_prompt` 支持 `role_category`**

```python
@staticmethod
def build_draft_generate_prompt(
    *,
    topic: str,
    flow_display_name: str,
    stage: dict,
    dialog_history: str,
    doc_input: str,
    current_draft: str = "",
    user_message: str = "",
    role_category: str = "teacher",
) -> str:
    if role_category == "study_travel":
        return f"""你是研学基地主导师 Agent，当前正在执行内部草案生成能力。请根据基地人员输入和阶段上下文，整理出一份可直接审阅的 Markdown 研学方案草案。

【课题】{topic}
【研学流程】{flow_display_name}
【当前阶段】{stage["name"]}
【阶段目标】{stage["direction"]}

【跨阶段对话历史】
{dialog_history or "暂无历史对话。"}

【阶段文档上下文】
{doc_input or "暂无阶段文档。"}

【当前已采纳草案】
{current_draft or "暂无草案。"}

【本轮基地人员输入】
{user_message or "请根据当前上下文生成研学方案草案。"}

【输出要求】
1. 只输出完整 Markdown 研学方案草案正文，不要输出解释、寒暄、前缀或代码块。
2. 草案结构：研学目标 → 基地接待流程 → 课程设计 → 场地安排 → 安全预案
3. 如果当前已采纳草案为空，就直接生成初稿；如果已有内容，可在其基础上吸收基地人员的新想法，但仍输出完整草案。
4. 结构清晰，适合在右侧直接编辑与审阅。
5. 不要输出任何草案标记块。
"""
    # 教师类模板（保持现有逻辑）
    return f"""你是主导师 Agent，当前正在执行内部草案生成能力。请根据教师输入和阶段上下文，整理出一份可直接审阅的 Markdown 草案。

【课题】{topic}
【教学流】{flow_display_name}
【当前阶段】{stage["name"]}
【阶段目标】{stage["direction"]}

【跨阶段对话历史】
{dialog_history or "暂无历史对话。"}

【阶段文档上下文】
{doc_input or "暂无阶段文档。"}

【当前已采纳草案】
{current_draft or "暂无草案。"}

【本轮教师输入】
{user_message or "请根据当前上下文生成草案。"}

【输出要求】
1. 只输出完整 Markdown 草案正文，不要输出解释、寒暄、前缀或代码块。
2. 如果当前已采纳草案为空，就直接生成初稿；如果已有内容，可在其基础上吸收教师的新想法，但仍输出完整草案。
3. 结构清晰，适合在右侧直接编辑与审阅。
4. 结果要适合直接进入差异审阅工作流。
5. 不要输出任何草案标记块。
"""
```

- [ ] **Step 2: 修改 `build_draft_agent_prompt` 支持 `role_category`**

```python
@staticmethod
def build_draft_agent_prompt(
    *,
    topic: str,
    flow_display_name: str,
    stage: dict,
    guide_output: str,
    dialog_history: str,
    doc_input: str,
    current_draft: str = "",
    user_message: str = "",
    role_category: str = "teacher",
) -> str:
    if role_category == "study_travel":
        return f"""你是研学基地主导师 Agent，当前正在执行内部草案撰写能力，把当前阶段的研学方案设计整理成可直接保存的 Markdown 草案。

【课题】{topic}
【研学流程】{flow_display_name}
【当前阶段】{stage["name"]}
【阶段目标】{stage["direction"]}

【流程引导回复】
【流程引导回复开始】
{guide_output or "暂无流程引导回复。"}
【流程引导回复结束】

【跨阶段对话历史】
{dialog_history or "暂无历史对话。"}

【阶段文档上下文】
{doc_input or "暂无阶段文档。"}

【右侧现有草案】
{current_draft or "暂无草案。"}

【本轮基地人员输入】
{user_message or "请根据当前上下文生成研学方案草案。"}

【输出要求】
1. 只输出 Markdown 草案正文，不要输出解释、寒暄、前缀或代码块。
2. 草案要和当前阶段目标、基地人员输入、流程引导回复一致，避免写成空泛模板。
3. 结构清晰，适合在右侧直接编辑。
4. 保持简洁但完整，优先使用标题、编号和要点列表。
5. 不要输出任何草案标记块。
"""
    # 教师类模板（保持现有逻辑）
    return f"""你是主导师 Agent，当前正在执行内部草案撰写能力，把当前阶段的教学设计整理成可直接保存的 Markdown 草案。

【课题】{topic}
【教学流】{flow_display_name}
【当前阶段】{stage["name"]}
【阶段目标】{stage["direction"]}

【流程引导回复】
【流程引导回复开始】
{guide_output or "暂无流程引导回复。"}
【流程引导回复结束】

【跨阶段对话历史】
{dialog_history or "暂无历史对话。"}

【阶段文档上下文】
{doc_input or "暂无阶段文档。"}

【右侧现有草案】
{current_draft or "暂无草案。"}

【本轮教师输入】
{user_message or "请根据当前上下文生成草案。"}

【输出要求】
1. 只输出 Markdown 草案正文，不要输出解释、寒暄、前缀或代码块。
2. 草案要和当前阶段目标、教师输入、流程引导回复一致，避免写成空泛模板。
3. 结构清晰，适合在右侧直接编辑。
4. 保持简洁但完整，优先使用标题、编号和要点列表。
5. 不要输出任何草案标记块。
"""
```

- [ ] **Step 3: 修改 `build_guide_agent_prompt` 支持 `role_category`**

```python
@staticmethod
def build_guide_agent_prompt(
    *,
    topic: str,
    flow_display_name: str,
    stage: dict,
    dialog_history: str,
    doc_input: str,
    current_draft: str = "",
    user_message: str = "",
    selection_text: str = "",
    role_category: str = "teacher",
) -> str:
    if role_category == "study_travel":
        main_prompt = load_agent_prompt(get_agent_registry().main_tutor(role_category="study_travel"))
        user_label = "基地人员"
        user_input_label = "本轮基地人员输入"
    else:
        main_prompt = load_agent_prompt(get_agent_registry().main_tutor())
        user_label = "教师"
        user_input_label = "本轮教师输入"
    
    return f"""{main_prompt}

【课题】{topic}
【教学流/研学流程】{flow_display_name}
【当前阶段】{stage["name"]}
【阶段目标】{stage["direction"]}

【跨阶段对话历史】
{dialog_history or "暂无历史对话。"}

【阶段文档上下文】
{doc_input or "暂无阶段文档。"}

【右侧现有草案】
{current_draft or "暂无草案。"}

【{user_label}当前选中的草案内容】
{PromptService._selection_block(selection_text)}

【{user_input_label}】
{user_message or "请结合当前阶段给出引导建议。"}

【工作方式】
1. 你是主导师 Agent，负责吸收当前阶段的完整能力要求并持续推进流程，但不要在普通引导回复中输出完整草案。
2. 采用 Human-in-the-loop 方式，不要一次性包办整份方案。
3. 如果本轮有选区，默认先围绕这段内容给出引导，指出它与当前阶段目标的关系、问题和下一步建议。
4. 语言要连贯、友好、具体，尽量把{user_label}的想法推进到下一步。
5. 不要输出草案标记块，不要输出 Markdown 草案正文。
"""
```

- [ ] **Step 4: Commit**

```bash
git add app/services/prompt_service.py
git commit -m "feat: support role_category in draft prompt templates"
```

---

## Task 2: 草案生成服务传递角色分类

**Files:**
- Modify: `app/services/draft_generate_service.py`

- [ ] **Step 1: 修改 `stream_candidate` 方法**

```python
class DraftGenerateService:
    @staticmethod
    async def stream_candidate(
        *,
        topic: str,
        flow_display_name: str,
        stage: dict,
        dialog_history: str,
        doc_input: str,
        current_draft: str,
        user_message: str,
        llm_history: list[dict],
        role_category: str = "teacher",
    ) -> AsyncIterator[tuple[str, str]]:
        prompt = PromptService.build_draft_generate_prompt(
            topic=topic,
            flow_display_name=flow_display_name,
            stage=stage,
            dialog_history=dialog_history,
            doc_input=doc_input,
            current_draft=current_draft,
            user_message=user_message,
            role_category=role_category,
        )
        candidate = ""
        async for chunk in LLMService.chat_stream(
            prompt,
            llm_history,
            user_message,
            response_kind="draft_generate",
        ):
            if not chunk:
                continue
            candidate += chunk
            yield candidate, chunk
```

- [ ] **Step 2: Commit**

```bash
git add app/services/draft_generate_service.py
git commit -m "feat: pass role_category to draft generate service"
```

---

## Task 3: Mock 数据按角色区分

**Files:**
- Modify: `app/services/llm_service.py`

- [ ] **Step 1: 修改 `_mock_draft_generate_stream` 支持角色**

```python
@staticmethod
async def _mock_draft_generate_stream(system_prompt: str, new_message: str):
    stage_name = LLMService._between(system_prompt, "【当前阶段】", "\n") or "当前阶段"
    stage_goal = LLMService._between(system_prompt, "【阶段目标】", "\n\n") or "阶段目标"
    
    # 检测是否为研学类
    is_study_travel = "研学" in system_prompt or "基地" in system_prompt
    
    if is_study_travel:
        draft = (
            f"### {stage_name}研学方案草案\n\n"
            f"**阶段目标**：{stage_goal}\n\n"
            f"**流程引导承接**：基于基地人员输入"{new_message}"继续推进研学方案设计。\n\n"
            "1. **研学目标**：围绕基地特色资源，设计一个学生能够直接观察、体验并形成认知的研学活动。\n"
            "2. **基地接待流程**：明确接待时间、人数、分组方式、讲解路线和互动环节。\n"
            "3. **课程设计**：结合基地资源设计跨学科课程，突出体验性和探究性。\n"
            "4. **场地安排**：明确活动场地、设施使用、安全通道和应急集合点。\n"
            "5. **安全预案**：识别潜在风险，制定预防措施和应急处置流程。"
        )
    else:
        draft = (
            f"### {stage_name}设计草案\n\n"
            f"**阶段目标**：{stage_goal}\n\n"
            f"**流程引导承接**：基于教师输入"{new_message}"继续推进课堂设计。\n\n"
            "1. **核心活动**：围绕教师提出的课堂设想，设计一个学生能够直接观察、讨论并形成证据的探究活动。\n"
            "2. **教学意图与探究价值**：让学生从现象进入问题，再通过证据形成解释，避免直接接受结论。\n"
            "3. **学生探究任务**：学生以小组为单位记录现象、提出猜想、整理证据，并用简短语言表达推理过程。\n"
            "4. **草案优化提示**：如果课堂材料或学生基础发生变化，可以进一步细化变量、步骤和记录方式。"
        )

    for index in range(0, len(draft), 12):
        await asyncio.sleep(0.01)
        yield draft[index : index + 12]
```

- [ ] **Step 2: 修改 `_mock_guide_stream` 支持角色**

```python
@staticmethod
async def _mock_guide_stream(system_prompt: str, new_message: str):
    stage_name = LLMService._between(system_prompt, "【当前阶段】", "\n") or "当前阶段"
    stage_goal = LLMService._between(system_prompt, "【阶段目标】", "\n\n") or "阶段目标"
    selection_text = LLMService._between(system_prompt, "【教师当前选中的草案内容】", "【本轮教师输入】")
    
    # 检测是否为研学类
    is_study_travel = "研学" in system_prompt or "基地" in system_prompt
    user_label = "基地老师" if is_study_travel else "老师"
    selection_label = "【基地人员当前选中的草案内容】" if is_study_travel else "【教师当前选中的草案内容】"
    input_label = "【本轮基地人员输入】" if is_study_travel else "【本轮教师输入】"]
    
    selection_text = LLMService._between(system_prompt, selection_label, input_label)
    
    if selection_text and selection_text != "本轮无选区。":
        guide_hint = "我会先围绕你选中的这段内容来推进，重点看它和当前阶段目标是否对齐、还缺少哪些证据或追问。"
        full_reply = (
            f"【主导师 Agent】：{user_label}，我收到你的想法："{new_message}"。\n\n"
            f"你刚刚选中的这段内容很关键。站在"{stage_name}"这一阶段，我们要先把它和{stage_goal}更紧地扣在一起。\n\n"
            f"{guide_hint}\n\n"
            "你可以继续补充这段想解决的问题、学生反应或你最担心的地方，我会继续围绕这段帮你收紧。"
        )
    else:
        guide_hint = "你可以先补充一个更具体的课堂情境，或者说明希望学生优先观察什么现象。"
        full_reply = (
            f"【主导师 Agent】：{user_label}，我收到你的想法："{new_message}"。\n\n"
            f"站在"{stage_name}"这一阶段，我们要先把{stage_goal}落到可观察、可追问、可推进的课堂动作上。\n\n"
            f"{guide_hint}\n\n"
            "你可以继续补充课堂材料、学生已有基础或预期现象，我会继续帮你把方向收紧。"
        )

    for index in range(0, len(full_reply), 12):
        await asyncio.sleep(0.01)
        yield full_reply[index : index + 12]
```

- [ ] **Step 3: Commit**

```bash
git add app/services/llm_service.py
git commit -m "feat: differentiate mock data by role_category"
```

---

## Task 4: Chat API 传递用户角色

**Files:**
- Modify: `app/api/chat.py`

- [ ] **Step 1: 修改草案生成调用传递 `role_category`**

在 `app/api/chat.py` 中，找到 `DraftGenerateService.stream_candidate` 调用处，添加 `role_category` 参数：

```python
# 获取当前用户角色
user_role = "study_travel" if current_user and current_user.user_role == "study_travel" else "teacher"

# 在调用 stream_candidate 时传递
async for candidate_content, chunk in DraftGenerateService.stream_candidate(
    topic=session_snapshot["topic"],
    flow_display_name=session_snapshot["flow_display_name"],
    stage=current_stage,
    dialog_history=session_snapshot["dialog_history"],
    doc_input=session_snapshot["doc_input"],
    current_draft=session_snapshot["current_draft"],
    user_message=user_message,
    llm_history=llm_history,
    role_category=user_role,
):
    # ... 现有逻辑
```

- [ ] **Step 2: 修改状态文本按角色切换称呼**

```python
# 根据用户角色选择称呼
user_label = "老师" if user_role == "teacher" else "基地老师"

# 替换硬编码的"老师可以直接审阅"
draft_status_text = f"右侧草案已经整理好了，{user_label}可以直接审阅或继续修改。"
```

- [ ] **Step 3: Commit**

```bash
git add app/api/chat.py
git commit -m "feat: pass user_role to draft generation in chat API"
```

---

## Task 5: 前端角色切换同步到草案生成

**Files:**
- Modify: `frontend/src/components/AppHeader.vue`
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: AppHeader 角色切换时存储到 localStorage**

```typescript
function switchRole(role: UserRole) {
  currentRole.value = role;
  localStorage.setItem('user_role', role);
  emit('switch-role', role);
}
```

- [ ] **Step 2: 草案生成请求携带 `role_category`**

在 `frontend/src/api.ts` 中，修改 `streamChat` 函数，在 `draft_request_kind` 存在时添加 `role_category`：

```typescript
export type StreamChatPayload = {
  type: "chat" | "sys_action";
  request_id?: string;
  message?: string;
  action?: "next_stage" | "prev_stage" | "intro" | "confirm_stage";
  final_content?: string;
  expert_id?: string;
  draft_request_kind?: "generate" | "edit";
  role_category?: "teacher" | "study_travel";
  selection?: DraftSelection | null;
  graph_selection?: GraphSelectionPayload | null;
};
```

- [ ] **Step 3: 验证前端构建**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AppHeader.vue frontend/src/api.ts
git commit -m "feat: sync role switch to draft generation"
```

---

## Task 6: 集成测试

**Files:**
- Create: `tests/test_dual_role_draft.py`

- [ ] **Step 1: 编写测试**

```python
import pytest
from app.services.prompt_service import PromptService


def test_draft_prompt_teacher():
    """测试教师类草案提示词"""
    prompt = PromptService.build_draft_generate_prompt(
        topic="光的反射",
        flow_display_name="七阶段科学探究流",
        stage={"name": "观察起点", "direction": "从真实现象切入"},
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="我想从镜子反光开始",
        role_category="teacher",
    )
    assert "教师输入" in prompt
    assert "教学流" in prompt
    assert "研学" not in prompt


def test_draft_prompt_study_travel():
    """测试研学类草案提示词"""
    prompt = PromptService.build_draft_generate_prompt(
        topic="昆虫旅馆",
        flow_display_name="研学探究流",
        stage={"name": "行前准备", "direction": "明确研学目标"},
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="想让学生观察昆虫栖息",
        role_category="study_travel",
    )
    assert "基地人员输入" in prompt
    assert "研学流程" in prompt
    assert "研学目标" in prompt
    assert "安全预案" in prompt


def test_draft_agent_prompt_teacher():
    """测试教师类草案 Agent 提示词"""
    prompt = PromptService.build_draft_agent_prompt(
        topic="光的反射",
        flow_display_name="七阶段科学探究流",
        stage={"name": "观察起点", "direction": "从真实现象切入"},
        guide_output="引导回复",
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="我想从镜子反光开始",
        role_category="teacher",
    )
    assert "教师输入" in prompt
    assert "教学设计" in prompt


def test_draft_agent_prompt_study_travel():
    """测试研学类草案 Agent 提示词"""
    prompt = PromptService.build_draft_agent_prompt(
        topic="昆虫旅馆",
        flow_display_name="研学探究流",
        stage={"name": "行前准备", "direction": "明确研学目标"},
        guide_output="引导回复",
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="想让学生观察昆虫栖息",
        role_category="study_travel",
    )
    assert "基地人员输入" in prompt
    assert "研学方案设计" in prompt
```

- [ ] **Step 2: 运行测试**

Run: `pytest tests/test_dual_role_draft.py -v`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add tests/test_dual_role_draft.py
git commit -m "test: add dual-role draft prompt tests"
```

---

## 自检清单

- [x] 所有任务都有明确的代码示例
- [x] 提示词模板区分教师/研学两类
- [x] Mock 数据按角色区分
- [x] 前端角色切换同步到草案生成
- [x] 测试覆盖核心功能
- [x] 无 TBD/TODO 占位符
- [x] 文件路径准确
- [x] 命令可直接执行
