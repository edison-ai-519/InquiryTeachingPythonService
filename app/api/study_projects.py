import asyncio
import datetime as dt
import json
import mimetypes
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import (
    SessionModel,
    StudyProjectFileModel,
    StudyProjectModel,
    StudyTaskModel,
    StudyTaskSubmissionModel,
    UserModel,
)
from app.schemas import (
    StudyProjectCreateRequest,
    StudyProjectUpdateRequest,
    StudyTaskClaimRequest,
    StudyTaskCreateRequest,
    StudyTaskUpdateRequest,
)
from app.services.session_access_service import resolve_workspace_role
from app.services.session_file_service import FileExtractionError, SessionFileService
from app.workflow.flows import get_flow, list_flows


router = APIRouter(tags=["study-projects"])
project_router = APIRouter(prefix="/api/study-projects")
task_router = APIRouter(prefix="/api/study-tasks")
ROLE_LABELS = {"teacher": "教师", "parent": "家长", "study_travel": "研学基地"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def require_study_role(db: Session, user: UserModel) -> None:
    resolve_workspace_role(db, user, "study_travel")


def get_project(db: Session, project_id: str) -> StudyProjectModel:
    project = db.query(StudyProjectModel).filter(StudyProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="研学项目不存在")
    return project


def project_files(db: Session, project_id: str) -> list[StudyProjectFileModel]:
    return (
        db.query(StudyProjectFileModel)
        .filter(StudyProjectFileModel.project_id == project_id)
        .order_by(StudyProjectFileModel.created_at.asc())
        .all()
    )


def serialize_file(item: StudyProjectFileModel) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "extension": item.extension,
        "mime_type": item.mime_type,
        "size_bytes": item.size_bytes,
        "status": item.status,
        "error_message": item.error_message,
        "created_at": item.created_at,
    }


def serialize_project(project: StudyProjectModel, db: Session, *, detailed: bool = False) -> dict:
    tasks = (
        db.query(StudyTaskModel)
        .filter(StudyTaskModel.project_id == project.id)
        .order_by(StudyTaskModel.created_at.asc())
        .all()
    )
    result = {
        "id": project.id,
        "name": project.name,
        "location": project.location,
        "scene_description": project.scene_description,
        "materials": json.loads(project.materials_json or "[]"),
        "status": project.status,
        "summary_markdown": project.summary_markdown,
        "files": [serialize_file(item) for item in project_files(db, project.id)],
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "tasks": [],
    }
    for task in tasks:
        submissions = (
            db.query(StudyTaskSubmissionModel)
            .filter(StudyTaskSubmissionModel.task_id == task.id)
            .order_by(StudyTaskSubmissionModel.claimed_at.asc())
            .all()
        )
        task_data = serialize_task(task, db)
        task_data.update({
            "submission_count": len(submissions),
            "submitted_count": sum(row.status == "submitted" for row in submissions),
        })
        if detailed:
            task_data["submissions"] = [
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "username": db.query(UserModel.username).filter(UserModel.id == row.user_id).scalar() or "未知用户",
                    "session_id": row.session_id,
                    "status": row.status,
                    "report_markdown": row.report_markdown,
                    "claimed_at": row.claimed_at,
                    "submitted_at": row.submitted_at,
                }
                for row in submissions
            ]
        result["tasks"].append(task_data)
    return result


def serialize_task(task: StudyTaskModel, db: Session) -> dict:
    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "target_role": task.target_role,
        "target_role_label": ROLE_LABELS[task.target_role],
        "flow_name": task.flow_name,
        "flow_display_name": get_flow(task.flow_name)["display_name"],
        "status": task.status,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def validate_flow(target_role: str, flow_name: str) -> dict:
    try:
        flow = get_flow(flow_name)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="所选工作流不存在") from exc
    if flow.get("role_category", "teacher") != target_role:
        raise HTTPException(status_code=400, detail="工作流不属于所选目标工作台")
    if flow_name not in {item["name"] for item in list_flows(target_role)}:
        raise HTTPException(status_code=400, detail="所选工作流当前不可用")
    return flow


def accessible_task_context(db: Session, project_id: str, role: str, user_id: str) -> bool:
    published_task = db.query(StudyTaskModel.id).join(
        StudyProjectModel, StudyProjectModel.id == StudyTaskModel.project_id
    ).filter(
        StudyTaskModel.project_id == project_id,
        StudyTaskModel.target_role == role,
        StudyTaskModel.status == "open",
        StudyProjectModel.status == "active",
    ).first()
    if published_task:
        return True
    return bool(
        db.query(StudyTaskSubmissionModel.id)
        .join(StudyTaskModel, StudyTaskModel.id == StudyTaskSubmissionModel.task_id)
        .filter(
            StudyTaskModel.project_id == project_id,
            StudyTaskModel.target_role == role,
            StudyTaskSubmissionModel.user_id == user_id,
        )
        .first()
    )


@project_router.post("")
def create_project(
    payload: StudyProjectCreateRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    timestamp = now_iso()
    project = StudyProjectModel(
        id=new_id("project"),
        name=payload.name.strip(),
        location=payload.location.strip(),
        scene_description=payload.scene_description.strip(),
        materials_json=json.dumps([item.strip() for item in payload.materials if item.strip()], ensure_ascii=False),
        status="draft",
        summary_markdown="",
        created_by_user_id=user.id,
        created_at=timestamp,
        updated_at=timestamp,
    )
    if not project.name:
        raise HTTPException(status_code=422, detail="项目名称不能为空")
    db.add(project)
    db.commit()
    return {"code": 0, "message": "success", "data": serialize_project(project, db)}


@project_router.get("")
def list_projects(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    projects = db.query(StudyProjectModel).order_by(StudyProjectModel.updated_at.desc()).all()
    return {"code": 0, "message": "success", "data": [serialize_project(item, db) for item in projects]}


@project_router.get("/{project_id}")
def read_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    return {"code": 0, "message": "success", "data": serialize_project(get_project(db, project_id), db, detailed=True)}


@project_router.patch("/{project_id}")
def update_project(
    project_id: str,
    payload: StudyProjectUpdateRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    project = get_project(db, project_id)
    values = payload.model_dump(exclude_unset=True, exclude_none=True)
    summary_only = set(values).issubset({"summary_markdown"})
    if project.status == "closed" and not summary_only:
        raise HTTPException(status_code=409, detail="项目已结束，只能编辑项目汇总")
    for field, value in values.items():
        if field == "materials":
            value = json.dumps([item.strip() for item in value if item.strip()], ensure_ascii=False)
            field = "materials_json"
        elif isinstance(value, str) and field != "summary_markdown":
            value = value.strip()
        setattr(project, field, value)
    if not project.name.strip():
        raise HTTPException(status_code=422, detail="项目名称不能为空")
    project.updated_at = now_iso()
    db.commit()
    return {"code": 0, "message": "success", "data": serialize_project(project, db, detailed=True)}


@project_router.post("/{project_id}/publish")
def publish_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    project = get_project(db, project_id)
    if project.status == "closed":
        raise HTTPException(status_code=409, detail="已结束的项目不能重新发布")
    project.status = "active"
    project.updated_at = now_iso()
    db.query(StudyTaskModel).filter(
        StudyTaskModel.project_id == project.id,
        StudyTaskModel.status == "draft",
    ).update({"status": "open", "updated_at": project.updated_at})
    db.commit()
    return {"code": 0, "message": "success", "data": serialize_project(project, db)}


@project_router.post("/{project_id}/close")
def close_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    project = get_project(db, project_id)
    project.status = "closed"
    project.updated_at = now_iso()
    db.query(StudyTaskModel).filter(
        StudyTaskModel.project_id == project.id,
        StudyTaskModel.status.in_(["draft", "open"]),
    ).update({"status": "closed", "updated_at": project.updated_at})
    db.commit()
    return {"code": 0, "message": "success", "data": serialize_project(project, db, detailed=True)}


@project_router.post("/{project_id}/files")
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    project = get_project(db, project_id)
    if project.status == "closed":
        raise HTTPException(status_code=409, detail="项目已结束，不能上传附件")
    settings = get_settings()
    if len(project_files(db, project_id)) >= settings.upload_max_files_per_session:
        raise HTTPException(status_code=409, detail="项目附件数量已达上限")
    try:
        name = SessionFileService.safe_display_name(file.filename or "")
        extension = SessionFileService.extension_for(name)
    except FileExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    data = await file.read(settings.upload_max_file_bytes + 1)
    await file.close()
    if not data:
        raise HTTPException(status_code=400, detail="不能上传空文件")
    if len(data) > settings.upload_max_file_bytes:
        raise HTTPException(status_code=413, detail="附件超过单文件大小上限")
    file_id = new_id("pfile")
    relative_path = SessionFileService.relative_storage_path(project_id, file_id, extension)
    record = StudyProjectFileModel(
        id=file_id,
        project_id=project_id,
        name=name,
        extension=extension,
        mime_type=file.content_type or mimetypes.guess_type(name)[0] or "",
        size_bytes=len(data),
        extracted_text="",
        status="processing",
        error_message="",
        stored_path=relative_path.as_posix(),
        uploaded_by_user_id=user.id,
        created_at=now_iso(),
    )
    db.add(record)
    db.commit()
    try:
        await asyncio.to_thread(SessionFileService.write_file, relative_path, data)
        extracted_text = await asyncio.to_thread(SessionFileService.extract_text, relative_path, extension)
        record.extracted_text = extracted_text[: settings.upload_max_total_chars]
        record.status = "ready"
    except Exception as exc:
        record.status = "failed"
        record.error_message = str(exc)[:1000] if isinstance(exc, FileExtractionError) else "附件处理失败"
    project.updated_at = now_iso()
    db.commit()
    db.refresh(record)
    return {"code": 0, "message": "success", "data": serialize_file(record)}


@project_router.delete("/{project_id}/files/{file_id}")
def delete_project_file(
    project_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    project = get_project(db, project_id)
    if project.status == "closed":
        raise HTTPException(status_code=409, detail="项目已结束，不能删除附件")
    row = db.query(StudyProjectFileModel).filter(
        StudyProjectFileModel.id == file_id,
        StudyProjectFileModel.project_id == project_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="附件不存在")
    SessionFileService.delete_stored_file(row.stored_path)
    db.delete(row)
    project.updated_at = now_iso()
    db.commit()
    return {"code": 0, "message": "success", "data": None}


@project_router.get("/{project_id}/files/{file_id}/download")
def download_project_file(
    project_id: str,
    file_id: str,
    role_category: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    role = resolve_workspace_role(db, user, role_category)
    project = get_project(db, project_id)
    if role != "study_travel" and not accessible_task_context(db, project_id, role, user.id):
        raise HTTPException(status_code=403, detail="无权查看该项目资料")
    row = db.query(StudyProjectFileModel).filter(
        StudyProjectFileModel.id == file_id,
        StudyProjectFileModel.project_id == project_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="附件不存在")
    path = SessionFileService.absolute_storage_path(row.stored_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="附件文件不存在")
    return FileResponse(path, filename=row.name, media_type=row.mime_type or "application/octet-stream")


@project_router.post("/{project_id}/tasks")
def create_task(
    project_id: str,
    payload: StudyTaskCreateRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    project = get_project(db, project_id)
    if project.status == "closed":
        raise HTTPException(status_code=409, detail="项目已结束，不能新增任务")
    validate_flow(payload.target_role, payload.flow_name)
    timestamp = now_iso()
    task = StudyTaskModel(
        id=new_id("task"),
        project_id=project_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        target_role=payload.target_role,
        flow_name=payload.flow_name,
        status="open" if project.status == "active" else "draft",
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(task)
    project.updated_at = timestamp
    db.commit()
    return {"code": 0, "message": "success", "data": serialize_task(task, db)}


def get_task(db: Session, task_id: str) -> StudyTaskModel:
    task = db.query(StudyTaskModel).filter(StudyTaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@project_router.patch("/{project_id}/tasks/{task_id}")
def update_task(
    project_id: str,
    task_id: str,
    payload: StudyTaskUpdateRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    project = get_project(db, project_id)
    task = get_task(db, task_id)
    if task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if project.status == "closed" or task.status == "closed":
        raise HTTPException(status_code=409, detail="已关闭项目或任务不能编辑")
    values = payload.model_dump(exclude_unset=True, exclude_none=True)
    has_submissions = db.query(StudyTaskSubmissionModel.id).filter(
        StudyTaskSubmissionModel.task_id == task.id
    ).first() is not None
    target_role = values.get("target_role", task.target_role)
    flow_name = values.get("flow_name", task.flow_name)
    if has_submissions and (
        target_role != task.target_role or flow_name != task.flow_name
    ):
        raise HTTPException(status_code=409, detail="任务已有人领取，不能修改目标工作台或工作流")
    validate_flow(target_role, flow_name)
    for field, value in values.items():
        setattr(task, field, value.strip() if isinstance(value, str) else value)
    task.updated_at = now_iso()
    db.commit()
    return {"code": 0, "message": "success", "data": serialize_task(task, db)}


@project_router.post("/{project_id}/tasks/{task_id}/close")
def close_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    require_study_role(db, user)
    task = get_task(db, task_id)
    if task.project_id != project_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "closed"
    task.updated_at = now_iso()
    db.commit()
    project = get_project(db, project_id)
    return {"code": 0, "message": "success", "data": serialize_project(project, db, detailed=True)}


@task_router.get("/available")
def available_tasks(
    role_category: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    role = resolve_workspace_role(db, user, role_category)
    tasks = (
        db.query(StudyTaskModel)
        .join(StudyProjectModel, StudyProjectModel.id == StudyTaskModel.project_id)
        .filter(
            StudyTaskModel.target_role == role,
            StudyTaskModel.status == "open",
            StudyProjectModel.status == "active",
        )
        .order_by(StudyTaskModel.created_at.desc())
        .all()
    )
    data = []
    for task in tasks:
        project = get_project(db, task.project_id)
        submission = db.query(StudyTaskSubmissionModel).filter(
            StudyTaskSubmissionModel.task_id == task.id,
            StudyTaskSubmissionModel.user_id == user.id,
        ).first()
        data.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "target_role": task.target_role,
            "flow_name": task.flow_name,
            "flow_display_name": get_flow(task.flow_name)["display_name"],
            "status": task.status,
            "my_submission": serialize_submission(submission) if submission else None,
            "project": {
                "id": project.id,
                "name": project.name,
                "location": project.location,
                "scene_description": project.scene_description,
                "materials": json.loads(project.materials_json or "[]"),
                "files": [serialize_file(item) for item in project_files(db, project.id)],
            },
        })
    return {"code": 0, "message": "success", "data": data}


def serialize_submission(row: StudyTaskSubmissionModel) -> dict:
    return {
        "id": row.id,
        "task_id": row.task_id,
        "session_id": row.session_id,
        "status": row.status,
        "report_markdown": row.report_markdown,
        "claimed_at": row.claimed_at,
        "submitted_at": row.submitted_at,
    }


@task_router.post("/{task_id}/claim")
def claim_task(
    task_id: str,
    payload: StudyTaskClaimRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    role = resolve_workspace_role(db, user, payload.role_category)
    task = get_task(db, task_id)
    if task.target_role != role:
        raise HTTPException(status_code=403, detail="该任务不属于当前工作台")
    project = get_project(db, task.project_id)
    existing = db.query(StudyTaskSubmissionModel).filter(
        StudyTaskSubmissionModel.task_id == task_id,
        StudyTaskSubmissionModel.user_id == user.id,
    ).first()
    if existing:
        session = db.query(SessionModel).filter(SessionModel.id == existing.session_id).first()
        return {"code": 0, "message": "success", "data": {"submission": serialize_submission(existing), "session": {"id": session.id, "status": session.status}}}
    if project.status != "active" or task.status != "open":
        raise HTTPException(status_code=409, detail="任务当前不可领取")

    timestamp = now_iso()
    session_id = new_id("sess")
    flow = get_flow(task.flow_name)
    session = SessionModel(
        id=session_id,
        owner_user_id=user.id,
        title=f"{task.title}-{ROLE_LABELS[role]}报告",
        topic=task.title,
        flow_name=task.flow_name,
        current_stage_index=0,
        status="active",
        draft_mode_enabled=0,
        role_category=role,
        home_context_json="{}",
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(session)
    from app.api.sessions import create_stage_outputs
    create_stage_outputs(db, session_id, task.flow_name, role)
    submission = StudyTaskSubmissionModel(
        id=new_id("submission"),
        task_id=task.id,
        user_id=user.id,
        session_id=session_id,
        status="claimed",
        report_markdown="",
        claimed_at=timestamp,
        submitted_at="",
    )
    db.add(submission)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(StudyTaskSubmissionModel).filter(
            StudyTaskSubmissionModel.task_id == task_id,
            StudyTaskSubmissionModel.user_id == user.id,
        ).first()
        if not existing:
            raise
        session = db.query(SessionModel).filter(SessionModel.id == existing.session_id).first()
        return {"code": 0, "message": "success", "data": {"submission": serialize_submission(existing), "session": {"id": session.id, "status": session.status}}}
    return {
        "code": 0,
        "message": "success",
        "data": {
            "submission": serialize_submission(submission),
            "session": {"id": session.id, "status": session.status, "topic": session.topic, "flow_name": flow["name"], "role_category": role},
        },
    }


@task_router.get("/mine")
def my_submissions(
    role_category: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    role = resolve_workspace_role(db, user, role_category)
    rows = (
        db.query(StudyTaskSubmissionModel, StudyTaskModel, StudyProjectModel)
        .join(StudyTaskModel, StudyTaskModel.id == StudyTaskSubmissionModel.task_id)
        .join(StudyProjectModel, StudyProjectModel.id == StudyTaskModel.project_id)
        .filter(StudyTaskSubmissionModel.user_id == user.id)
        .filter(StudyTaskModel.target_role == role)
        .order_by(StudyTaskSubmissionModel.claimed_at.desc())
        .all()
    )
    return {"code": 0, "message": "success", "data": [
        {
            **serialize_submission(submission),
            "task_title": task.title,
            "project_id": project.id,
            "project_name": project.name,
            "target_role": task.target_role,
        }
        for submission, task, project in rows
    ]}


router.include_router(project_router)
router.include_router(task_router)
