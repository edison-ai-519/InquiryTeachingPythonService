"""只用演示数据驱动真实 Vue 界面；所有 API 请求在浏览器内拦截，不访问后端。"""
import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

import yaml
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("presentation_flows", ROOT / "app/workflow/flows.py")
flow_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow_module)
flows = []
for value in flow_module.FLOW_TEMPLATES.values():
    flow = deepcopy(value)
    flow["stage_count"] = len(flow["stages"])
    flows.append(flow)
agents = yaml.safe_load((ROOT / "app/agents/config/agents.yaml").read_text(encoding="utf-8"))["agents"]
experts = [{key: value[key] for key in ["id", "name", "role", "description", "capabilities"]} for value in agents if value["selectable"]]
flow = next(value for value in flows if value["name"] == "insect_hotel_project")
stage = flow["stages"][2]
now = "2026-09-08T10:00:00+08:00"
draft = """# 校园昆虫旅馆 · 结构设计（演示数据）

## 一、探究目标
比较材料与孔径，提出有依据的结构设计。
通过观察记录，为后续改进收集证据。

## 二、核心问题
不同孔径的竹节，会吸引怎样的本地昆虫？

## 三、分组设计
1. 选择干燥竹节、枯枝和落叶，记录材料来源。
2. 设计两组孔径不同的竹节模块。
3. 统一朝向与摆放高度，固定牢靠。
4. 保留遮雨、通风与温湿度传感器位置。

## 四、观察记录
记录日期、天气、昆虫活动和环境数据。

## 五、安全与生态边界
不捕捉、不惊扰、不人为强行引入昆虫。
工具操作由教师指导，定期检查结构稳定性。
"""
old = "记录日期、天气、昆虫活动和环境数据。"
new = "每周在固定时段记录日期、温湿度、孔径组别与入住痕迹；使用照片和观察表分别保留证据。"
candidate = draft.replace(old, new)
session = dict(id="demo-insect-hotel", title="校园昆虫旅馆（演示数据）", topic="校园昆虫旅馆（演示数据）", flow_name=flow["name"], flow_display_name=flow["display_name"], current_stage_index=2, status="active", draft_mode_enabled=True, updated_at=now, created_at=now, current_stage=stage)
session["outputs"] = [dict(stage_id=item["id"], stage_name=item["name"], order_index=i, draft_content=draft if i == 2 else "## 演示阶段记录\n已整理本阶段的探究问题与观察任务。", final_content="## 演示阶段定稿\n已整理本阶段的探究问题与观察任务。" if i < 2 else "", confirmed=i < 2) for i, item in enumerate(flow["stages"]) if i <= 2]
sessions = [{key: value for key, value in session.items() if key not in ["outputs", "current_stage"]}]
messages = [
    dict(id="demo-message-1", stage_id=stage["id"], role="assistant", content="我们进入**旅馆结构设计**。先比较材料、孔径与遮挡方案，再把设计想法变成可观察、可检验的问题。", agent_name="主导师 Agent", agent_role="探究教学主导师"),
    dict(id="demo-message-2", stage_id=stage["id"], role="user", content="学生想用竹节和枯枝搭建昆虫旅馆，怎样让不同小组的设计具有可比性？"),
    dict(id="demo-message-3", stage_id=stage["id"], role="assistant", content="建议每轮只比较一个主要变量，例如**竹节孔径**。\n\n- 统一材料来源、朝向与摆放高度。\n- 记录自然入住痕迹，不人为引入昆虫。\n- 将观察记录与温湿度数据对应。\n\n这样能够帮助学生用证据解释设计取舍。", agent_id="insect_agent", agent_name="昆虫 Agent", agent_role="昆虫观察专家", message_type="expert_advice"),
    dict(id="demo-message-4", stage_id=stage["id"], role="assistant", content="教学方案已整理在右侧。选中需要细化的记录要求，可继续提出修改；在“预览与审阅”中逐条接受或拒绝建议。\n\n*本会话内容为演示数据。*", agent_name="主导师 Agent", agent_role="探究教学主导师"),
]
files = [dict(id="demo-file-1", name="校园观察记录（演示资料）.md", extension=".md", mime_type="text/markdown", size_bytes=880, extracted_chars=310, status="ready", error_message="", created_at=now)]
proposal = dict(id="demo-proposal-1", session_id=session["id"], stage_id=stage["id"], base_content=draft, candidate_content=candidate, segments=[dict(id="demo-hunk-1", kind="replace", base_start=draft.index(old), base_end=draft.index(old)+len(old), candidate_start=candidate.index(new), candidate_end=candidate.index(new)+len(new), base_text=old, candidate_text=new, status="pending")], status="pending", proposal_kind="edit", target_mode="selection", target_summary="细化观察记录中的频率、字段与证据保存方式（演示修改）。", target_range=dict(start_offset=draft.index(old), end_offset=draft.index(old)+len(old)), highlight_segment_ids=["demo-hunk-1"], created_at=now, updated_at=now)
curriculum_files = [dict(source="校园生态观察任务（演示资料）.md", extension=".md", chunk_count=3, vector_chunk_count=3, vector_status="ready", embedding_model="演示索引", last_error="", updated_at=now, allowed_expert_ids=["insect_agent", "nature_agent"]), dict(source="科学探究记录要点（演示资料）.md", extension=".md", chunk_count=3, vector_chunk_count=3, vector_status="ready", embedding_model="演示索引", last_error="", updated_at=now, allowed_expert_ids=["mathematics_teacher_agent", "physics_teacher_agent"])]
vector_status = dict(enabled=True, required=False, available=True, dependency_ready=True, model="演示索引", model_dir="", device="cpu", vector_dir="", collection="demo", vector_count=6, database_chunk_count=6, source_count=2, rebuild_required=False, error="", candidate_k=12, top_k=3, vector_weight=0.6, bm25_weight=0.4)
retrievals = [dict(id="demo-retrieval", session_id=session["id"], stage_id=stage["id"], query="昆虫旅馆：如何组织非侵扰观察与证据记录（演示查询）", mode="local_hybrid", expert_id="insect_agent", allowed_sources=[curriculum_files[0]["source"]], hit_sources=[curriculum_files[0]["source"]], vector_error="", created_at=now, records=[dict(chunk_id=1, chunk_ids=[1], source=curriculum_files[0]["source"], source_index=1, content="演示片段：以固定时间、固定位置进行非侵扰式观察，分别保存照片、活动痕迹和环境记录。以下分值为界面演示数据。", score=0.82, bm25_score=0.74, vector_score=0.87, fusion_score=0.82, retrieval_mode="local_hybrid")])]
state = {"admin": False, "auth": True}
requests = []
errors = []

def handle_route(route):
    url = urlparse(route.request.url)
    path = url.path
    if url.port == 5179 and not path.startswith("/api/"):
        return route.continue_()
    if "/api/" not in path:
        return route.abort()
    requests.append({"method": route.request.method, "path": path})
    headers = {"access-control-allow-origin": "http://127.0.0.1:5179", "access-control-allow-credentials": "true", "access-control-allow-methods": "GET,POST,PUT,DELETE,OPTIONS", "access-control-allow-headers": "content-type"}
    if route.request.method == "OPTIONS":
        return route.fulfill(status=204, headers=headers)
    if path == "/api/auth/me" and not state["auth"]:
        return route.fulfill(status=401, headers=headers, json={"detail": "演示未登录状态"})
    data = None
    if path == "/api/auth/me": data = dict(id="demo-user", username="演示管理员" if state["admin"] else "演示教师", is_admin=state["admin"])
    elif path == "/api/flows": data = flows
    elif path == "/api/experts": data = experts
    elif path == "/api/sessions": data = sessions
    elif path == f"/api/sessions/{session['id']}": data = session
    elif path.endswith("/messages"): data = messages
    elif path.endswith("/draft-proposal"): data = proposal
    elif path == "/api/curriculum/files": data = curriculum_files
    elif path == "/api/curriculum/status": data = vector_status
    elif path == "/api/curriculum/retrievals": data = retrievals
    elif path.endswith("/files"): data = files
    elif path.endswith("/export"):
        return route.fulfill(status=200, headers=headers, content_type="text/markdown; charset=utf-8", body=draft)
    else:
        errors.append("未预期API请求：" + route.request.method + " " + path)
        return route.fulfill(status=400, headers=headers, json={"detail": "演示截图不执行此操作"})
    return route.fulfill(status=200, headers=headers, json={"data": data})

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.5, locale="zh-CN", timezone_id="Asia/Shanghai", accept_downloads=True)
    context.route("**/*", handle_route)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:5179", wait_until="networkidle")
    page.get_by_text("演示教师", exact=True).wait_for()
    page.screenshot(path=str(OUT / "01-workspace-overview.png"), full_page=True)
    page.set_viewport_size({"width": 1600, "height": 800})
    page.screenshot(path=str(OUT / "workbench.png"), full_page=True)
    print("已生成主图 workbench.png（2400×1200）", flush=True)
    page.set_viewport_size({"width": 1600, "height": 1000})
    page.locator(".expert-selector-trigger").click()
    page.locator(".expert-selector-popover").wait_for()
    page.screenshot(path=str(OUT / "02-expert-selector.png"), full_page=True)
    page.locator(".expert-option").filter(has_text="昆虫 Agent").click()
    page.locator(".composer-chip.expert").click()
    editor = page.locator(".draft-editor-textarea")
    editor.evaluate("(el, text) => { const start = el.value.indexOf(text); el.focus(); el.setSelectionRange(start, start + text.length); el.dispatchEvent(new Event('select', {bubbles:true})); }", old)
    page.get_by_role("button", name="添加到对话", exact=True).click()
    page.locator(".composer-chip").filter(has_text="@17行-17行").wait_for()
    page.locator(".chat-composer textarea").fill("请把这段观察记录要求改得更具体。（演示输入）")
    page.screenshot(path=str(OUT / "03-selection-to-chat.png"), full_page=True)
    page.get_by_role("button", name="预览与审阅", exact=True).click()
    page.locator(".draft-review-overlay:not(.legacy-hidden)").wait_for()
    page.screenshot(path=str(OUT / "04-draft-review.png"), full_page=True)
    page.locator(".draft-review-overlay:not(.legacy-hidden)").get_by_role("button", name="关闭", exact=True).click()
    with page.expect_download() as download_info:
        page.get_by_role("button", name="导出", exact=True).click()
    download = download_info.value
    download.save_as(str(OUT / "demo-export.md"))
    assert (OUT / "demo-export.md").read_text(encoding="utf-8") == draft
    page.get_by_title("课标知识库", exact=True).click()
    readonly_modal = page.locator(".modal-overlay:not(.legacy-hidden) .curriculum-modal")
    readonly_modal.get_by_text("校园生态观察任务（演示资料）.md", exact=True).wait_for()
    page.screenshot(path=str(OUT / "09-curriculum-readonly.png"), full_page=True)
    readonly_modal.screenshot(path=str(OUT / "09b-curriculum-readonly-panel.png"))
    readonly_modal.get_by_role("button", name="关闭", exact=True).click()
    state["admin"] = True
    page.reload(wait_until="networkidle")
    page.get_by_text("演示管理员", exact=True).wait_for()
    page.get_by_title("课标知识库", exact=True).click()
    modal = page.locator(".modal-overlay:not(.legacy-hidden) .curriculum-modal")
    modal.get_by_text("混合检索可用", exact=True).wait_for()
    modal.locator(".curriculum-retrieval-row summary").click()
    page.screenshot(path=str(OUT / "05-curriculum-rag-admin.png"), full_page=True)
    modal.screenshot(path=str(OUT / "05b-curriculum-panel.png"))
    modal.get_by_role("button", name="配置权限", exact=True).first.click()
    page.screenshot(path=str(OUT / "06-expert-source-permissions.png"), full_page=True)
    modal.get_by_role("button", name="关闭", exact=True).click()
    page.get_by_title("新建会话", exact=True).click()
    page.get_by_role("heading", name="新建探究会话", exact=True).wait_for()
    page.screenshot(path=str(OUT / "07-new-session.png"), full_page=True)
    state["auth"] = False
    page.reload(wait_until="networkidle")
    page.get_by_role("heading", name="登录工作台", exact=True).wait_for()
    page.screenshot(path=str(OUT / "08-auth-panel.png"), full_page=True)
    browser.close()

report = {"source": "原始frontend Vue组件，由5179端口的独立Vite服务加载；未修改应用代码、样式或DOM。", "data_boundary": "账号、会话、消息、草稿、修改建议、文件清单、召回记录、索引状态及分值均为浏览器内的演示数据；流程定义与专家配置直接读取项目源码。所有API请求均由Playwright在浏览器内拦截；未访问真实后端、数据库或模型。", "required_caption": "真实界面 · 演示数据", "viewport": [1600, 1000], "scale": 1.5, "checks": ["真实Vue工作台加载", "专家选择弹层与选择交互", "草稿选区添加到对话", "候选差异审阅展示", "导出按钮完成演示Markdown下载", "管理员课标及召回展开", "专家资料授权编辑界面", "新建会话弹窗", "未登录界面"], "errors": errors, "requests": requests, "artifacts": sorted(path.name for path in OUT.glob("*.png"))}
(OUT / "capture-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
if errors:
    raise SystemExit(1)
