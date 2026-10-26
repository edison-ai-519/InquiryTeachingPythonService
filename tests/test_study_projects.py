import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path


TEST_DIR = Path(tempfile.mkdtemp(prefix="study-projects-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_DIR / 'study.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(TEST_DIR / "uploads")
os.environ["KNOWLEDGE_SOURCE_DIR"] = str(TEST_DIR / "knowledge_sources")
os.environ["LLM_API_KEY"] = ""
os.environ["AGENT_CONFIG_PATH"] = "app/agents/config/agents.yaml"
os.environ["CURRICULUM_VECTOR_ENABLED"] = "false"
os.environ["ECOLOGY_GRAPH_AUTO_SYNC_ENABLED"] = "false"
os.environ["GLOBI_IMPORT_WORKER_ENABLED"] = "false"

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.models import UserModel, UserWorkspaceRoleModel
from app.main import app
from app.services.context_service import ContextService


class StudyProjectApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study = TestClient(app)
        cls.teacher = TestClient(app)
        cls.parent = TestClient(app)
        cls.other = TestClient(app)
        cls._register(cls.study, "study_travel")
        cls._register(cls.teacher, "teacher")
        cls._register(cls.parent, "parent")
        cls._register(cls.other, "teacher")

    @classmethod
    def tearDownClass(cls):
        for client in (cls.study, cls.teacher, cls.parent, cls.other):
            client.close()
        shutil.rmtree(TEST_DIR, ignore_errors=True)

    @classmethod
    def _register(cls, client, role):
        username = f"project_{role}_{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/auth/register",
            json={"username": username, "password": "project-test-password"},
        )
        if response.status_code != 200:
            raise AssertionError(response.text)
        user_id = response.json()["data"]["id"]
        with SessionLocal() as db:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            user.user_role = role
            db.query(UserWorkspaceRoleModel).filter(
                UserWorkspaceRoleModel.user_id == user_id
            ).delete()
            db.add(UserWorkspaceRoleModel(
                user_id=user_id,
                role_category=role,
                created_at=user.created_at,
            ))
            db.commit()

    def test_study_workspace_can_create_a_project(self):
        response = self.study.post(
            "/api/study-projects",
            json={
                "name": "古道自然观察项目",
                "location": "石佛岭古道",
                "scene_description": "观察古道边坡与植物生境",
                "materials": ["放大镜", "记录板"],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        project = response.json()["data"]
        self.assertEqual(project["status"], "draft")
        self.assertEqual(project["materials"], ["放大镜", "记录板"])

    def test_non_study_workspace_cannot_create_a_project(self):
        response = self.teacher.post(
            "/api/study-projects",
            json={"name": "不应创建", "materials": []},
        )
        self.assertEqual(response.status_code, 403)

    def test_project_task_is_routed_only_to_its_target_workspace(self):
        project = self.study.post(
            "/api/study-projects",
            json={"name": "任务路由项目", "materials": ["记录板"]},
        )
        self.assertEqual(project.status_code, 200, project.text)
        project_id = project.json()["data"]["id"]
        task = self.study.post(
            f"/api/study-projects/{project_id}/tasks",
            json={
                "title": "设计课堂观察活动",
                "description": "形成可执行的课堂方案",
                "target_role": "teacher",
                "flow_name": "inquiry_7_stage",
            },
        )
        self.assertEqual(task.status_code, 200, task.text)
        published = self.study.post(f"/api/study-projects/{project_id}/publish")
        self.assertEqual(published.status_code, 200, published.text)
        teacher_tasks = self.teacher.get(
            "/api/study-tasks/available", params={"role_category": "teacher"}
        )
        parent_tasks = self.parent.get(
            "/api/study-tasks/available", params={"role_category": "parent"}
        )
        self.assertEqual(teacher_tasks.status_code, 200, teacher_tasks.text)
        self.assertIn(task.json()["data"]["id"], [row["id"] for row in teacher_tasks.json()["data"]])
        self.assertNotIn(task.json()["data"]["id"], [row["id"] for row in parent_tasks.json()["data"]])

    def test_multiple_users_can_claim_the_same_task_independently(self):
        project = self.study.post(
            "/api/study-projects",
            json={"name": "多人执行项目", "materials": []},
        ).json()["data"]
        task = self.study.post(
            f"/api/study-projects/{project['id']}/tasks",
            json={
                "title": "设计课堂活动",
                "description": "独立完成",
                "target_role": "teacher",
                "flow_name": "inquiry_7_stage",
            },
        ).json()["data"]
        self.study.post(f"/api/study-projects/{project['id']}/publish")
        first = self.teacher.post(
            f"/api/study-tasks/{task['id']}/claim",
            json={"role_category": "teacher"},
        )
        second = self.other.post(
            f"/api/study-tasks/{task['id']}/claim",
            json={"role_category": "teacher"},
        )
        again = self.teacher.post(
            f"/api/study-tasks/{task['id']}/claim",
            json={"role_category": "teacher"},
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertNotEqual(first.json()["data"]["session"]["id"], second.json()["data"]["session"]["id"])
        self.assertEqual(first.json()["data"]["submission"]["id"], again.json()["data"]["submission"]["id"])

    def test_claimed_task_can_edit_copy_but_cannot_change_its_workflow(self):
        project = self.study.post(
            "/api/study-projects",
            json={"name": "领取后编辑校验", "materials": []},
        ).json()["data"]
        task = self.study.post(
            f"/api/study-projects/{project['id']}/tasks",
            json={
                "title": "原标题",
                "description": "旧要求",
                "target_role": "teacher",
                "flow_name": "inquiry_7_stage",
            },
        ).json()["data"]
        self.study.post(f"/api/study-projects/{project['id']}/publish")
        self.teacher.post(
            f"/api/study-tasks/{task['id']}/claim",
            json={"role_category": "teacher"},
        )
        updated = self.study.patch(
            f"/api/study-projects/{project['id']}/tasks/{task['id']}",
            json={
                "title": "新标题",
                "description": "新要求",
                "target_role": "teacher",
                "flow_name": "inquiry_7_stage",
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["data"]["title"], "新标题")
        changed_flow = self.study.patch(
            f"/api/study-projects/{project['id']}/tasks/{task['id']}",
            json={"target_role": "parent", "flow_name": "stone_buddha_ancient_road_home_inquiry"},
        )
        self.assertEqual(changed_flow.status_code, 409)

    def test_completed_workflow_produces_a_role_report_for_the_project(self):
        project = self.study.post(
            "/api/study-projects",
            json={"name": "报告回收项目", "materials": []},
        ).json()["data"]
        task = self.study.post(
            f"/api/study-projects/{project['id']}/tasks",
            json={
                "title": "教师观察任务",
                "description": "生成报告",
                "target_role": "teacher",
                "flow_name": "three_step_inquiry",
            },
        ).json()["data"]
        self.study.post(f"/api/study-projects/{project['id']}/publish")
        claimed = self.teacher.post(
            f"/api/study-tasks/{task['id']}/claim",
            json={"role_category": "teacher"},
        ).json()["data"]
        session_id = claimed["session"]["id"]
        for stage_number in range(3):
            response = self.teacher.post(
                f"/api/sessions/{session_id}/confirm-stage?role_category=teacher",
                json={"final_content": f"第{stage_number + 1}阶段报告内容"},
            )
            self.assertEqual(response.status_code, 200, response.text)
        project_detail = self.study.get(f"/api/study-projects/{project['id']}")
        self.assertEqual(project_detail.status_code, 200, project_detail.text)
        submission = project_detail.json()["data"]["tasks"][0]["submissions"][0]
        self.assertEqual(submission["status"], "submitted")
        self.assertIn("教师报告", submission["report_markdown"])
        self.assertIn("第3阶段报告内容", submission["report_markdown"])

    def test_rolling_back_a_submitted_task_withdraws_its_old_report(self):
        project = self.study.post(
            "/api/study-projects",
            json={"name": "提交后回退项目", "materials": []},
        ).json()["data"]
        task = self.study.post(
            f"/api/study-projects/{project['id']}/tasks",
            json={
                "title": "可回退报告任务",
                "description": "",
                "target_role": "teacher",
                "flow_name": "three_step_inquiry",
            },
        ).json()["data"]
        self.study.post(f"/api/study-projects/{project['id']}/publish")
        claimed = self.teacher.post(
            f"/api/study-tasks/{task['id']}/claim",
            json={"role_category": "teacher"},
        ).json()["data"]
        session_id = claimed["session"]["id"]
        for stage_number in range(3):
            response = self.teacher.post(
                f"/api/sessions/{session_id}/confirm-stage?role_category=teacher",
                json={"final_content": f"旧报告阶段{stage_number + 1}"},
            )
            self.assertEqual(response.status_code, 200, response.text)
        rolled_back = self.teacher.post(
            f"/api/sessions/{session_id}/rollback?role_category=teacher",
            json={"steps": 1, "stage_back": True},
        )
        self.assertEqual(rolled_back.status_code, 200, rolled_back.text)
        project_detail = self.study.get(f"/api/study-projects/{project['id']}")
        submission = project_detail.json()["data"]["tasks"][0]["submissions"][0]
        self.assertEqual(submission["status"], "claimed")
        self.assertEqual(submission["report_markdown"], "")
        recommitted = self.teacher.post(
            f"/api/sessions/{session_id}/confirm-stage?role_category=teacher",
            json={"final_content": "回退后重新整理的报告"},
        )
        self.assertEqual(recommitted.status_code, 200, recommitted.text)
        project_detail = self.study.get(f"/api/study-projects/{project['id']}")
        refreshed_submission = project_detail.json()["data"]["tasks"][0]["submissions"][0]
        self.assertEqual(refreshed_submission["status"], "submitted")
        self.assertIn("回退后重新整理的报告", refreshed_submission["report_markdown"])

    def test_project_close_stops_new_claims_but_allows_manual_summary(self):
        project = self.study.post(
            "/api/study-projects",
            json={"name": "项目关闭测试", "materials": []},
        ).json()["data"]
        task = self.study.post(
            f"/api/study-projects/{project['id']}/tasks",
            json={
                "title": "领取关闭测试",
                "description": "",
                "target_role": "teacher",
                "flow_name": "inquiry_7_stage",
            },
        ).json()["data"]
        self.study.post(f"/api/study-projects/{project['id']}/publish")
        self.study.post(f"/api/study-projects/{project['id']}/close")
        claim = self.teacher.post(
            f"/api/study-tasks/{task['id']}/claim",
            json={"role_category": "teacher"},
        )
        self.assertEqual(claim.status_code, 409)
        summary = self.study.patch(
            f"/api/study-projects/{project['id']}",
            json={"summary_markdown": "基地人工整理结果"},
        )
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(summary.json()["data"]["summary_markdown"], "基地人工整理结果")

    def test_task_rejects_a_flow_from_another_workspace(self):
        project = self.study.post(
            "/api/study-projects",
            json={"name": "流程校验项目", "materials": []},
        ).json()["data"]
        response = self.study.post(
            f"/api/study-projects/{project['id']}/tasks",
            json={
                "title": "不匹配的工作流",
                "description": "",
                "target_role": "parent",
                "flow_name": "inquiry_7_stage",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_project_attachments_are_available_to_assigned_workspaces(self):
        project = self.study.post(
            "/api/study-projects",
            json={
                "name": "附件共享项目",
                "scene_description": "观察古道边坡的植物生境",
                "materials": ["放大镜"],
            },
        ).json()["data"]
        upload = self.study.post(
            f"/api/study-projects/{project['id']}/files",
            files={"file": ("场景说明.txt", "古道边坡观察".encode("utf-8"), "text/plain")},
        )
        self.assertEqual(upload.status_code, 200, upload.text)
        task = self.study.post(
            f"/api/study-projects/{project['id']}/tasks",
            json={
                "title": "教师任务",
                "description": "结合项目场景和附件设计观察活动",
                "target_role": "teacher",
                "flow_name": "inquiry_7_stage",
            },
        ).json()["data"]
        self.study.post(f"/api/study-projects/{project['id']}/publish")
        available = self.teacher.get(
            "/api/study-tasks/available", params={"role_category": "teacher"}
        )
        matching = next(item for item in available.json()["data"] if item["id"] == task["id"])
        file_info = matching["project"]["files"][0]
        download = self.teacher.get(
            f"/api/study-projects/{project['id']}/files/{file_info['id']}/download",
            params={"role_category": "teacher"},
        )
        self.assertEqual(download.status_code, 200, download.text)
        self.assertEqual(download.content, "古道边坡观察".encode("utf-8"))
        claimed = self.teacher.post(
            f"/api/study-tasks/{task['id']}/claim",
            json={"role_category": "teacher"},
        ).json()["data"]
        with SessionLocal() as db:
            context = ContextService.build_study_task_context(db, claimed["session"]["id"])
        self.assertIn("观察古道边坡的植物生境", context)
        self.assertIn("放大镜", context)
        self.assertIn("结合项目场景和附件设计观察活动", context)
        self.assertIn("古道边坡观察", context)

    def test_unpublished_project_attachments_are_not_visible_to_target_workspaces(self):
        project = self.study.post(
            "/api/study-projects",
            json={"name": "未发布附件隔离", "materials": []},
        ).json()["data"]
        upload = self.study.post(
            f"/api/study-projects/{project['id']}/files",
            files={"file": ("private.txt", b"draft only", "text/plain")},
        )
        self.assertEqual(upload.status_code, 200, upload.text)
        self.study.post(
            f"/api/study-projects/{project['id']}/tasks",
            json={
                "title": "尚未发布的教师任务",
                "description": "",
                "target_role": "teacher",
                "flow_name": "inquiry_7_stage",
            },
        )
        response = self.teacher.get(
            f"/api/study-projects/{project['id']}/files/{upload.json()['data']['id']}/download",
            params={"role_category": "teacher"},
        )
        self.assertEqual(response.status_code, 403)

    def test_other_worker_cannot_read_a_submitters_personal_execution(self):
        self.assertNotEqual(
            self.teacher.get("/api/auth/me").json()["data"]["id"],
            self.other.get("/api/auth/me").json()["data"]["id"],
        )
        project = self.study.post(
            "/api/study-projects",
            json={"name": "个人提交隔离", "materials": []},
        ).json()["data"]
        task = self.study.post(
            f"/api/study-projects/{project['id']}/tasks",
            json={
                "title": "私人执行会话",
                "description": "",
                "target_role": "teacher",
                "flow_name": "inquiry_7_stage",
            },
        ).json()["data"]
        self.study.post(f"/api/study-projects/{project['id']}/publish")
        claimed = self.teacher.post(
            f"/api/study-tasks/{task['id']}/claim",
            json={"role_category": "teacher"},
        ).json()["data"]
        denied = self.other.get(
            f"/api/sessions/{claimed['session']['id']}?role_category=teacher"
        )
        self.assertEqual(denied.status_code, 404)
        other_submissions = self.other.get(
            "/api/study-tasks/mine", params={"role_category": "teacher"}
        ).json()["data"]
        self.assertNotIn(
            claimed["session"]["id"],
            [item["session_id"] for item in other_submissions],
        )


if __name__ == "__main__":
    unittest.main()
