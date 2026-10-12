from app.workflow.flows import get_flow


class MarkdownExportService:
    @staticmethod
    def compile_lesson_plan(
        topic: str, flow_name: str, outputs: list, role_category: str = "teacher"
    ) -> str:
        flow = get_flow(flow_name)
        output_map = {item.stage_id: item for item in outputs}
        is_study_travel = role_category == "study_travel"
        document_title = "研学方案" if is_study_travel else "探究式教学设计"
        document_type = "研学实践活动" if is_study_travel else "探究式科学课"
        role_name = "研学主导师" if is_study_travel else "主导师 Agent"

        lines = [
            f"# {document_title}：{topic}",
            "",
            f"> 流程：{flow['display_name']}。本文档由 AI {'研学' if is_study_travel else '教学'}指导服务协同生成。",
            "",
            "## 一、项目基本信息",
            "",
            f"- {'项目名称' if is_study_travel else '课题名称'}：{topic}",
            f"- 活动类型：{document_type}",
            f"- {'实施周期：按基地接待与行程安排确定' if is_study_travel else '建议课时：1-2 课时，可按课堂长度裁剪'}",
            "",
            "## 二、阶段化活动设计",
            "",
        ]

        for stage in flow["stages"]:
            output = output_map.get(stage["id"])
            content = ""
            if output:
                content = output.final_content or output.draft_content or ""
            lines.extend(
                [
                    f"### {stage['name']}",
                    "",
                    f"**导师角色**：{role_name}",
                    "",
                    f"**阶段目标**：{stage['direction']}",
                    "",
                    content or "_本阶段暂未生成草案。_",
                    "",
                    "**活动评价建议**：关注参与者是否能提出证据、说明推理过程，并根据同伴反馈修正想法。",
                    "",
                ]
            )

        lines.extend(
            [
                "## 三、整体评价量规",
                "",
                "| 维度 | 观察要点 | 评价方式 |",
                "| --- | --- | --- |",
                "| 问题意识 | 能否从现象中提出可探究问题 | 提问卡、课堂追问 |",
                "| 证据意识 | 能否记录、比较、解释实验数据 | 实验记录单、小组汇报 |",
                "| 合作表达 | 能否倾听同伴并清晰表达观点 | 小组互评、展示评价 |",
                "| 迁移应用 | 能否把规律迁移到新情境 | 延伸任务、作品展示 |",
                "",
            ]
        )
        return "\n".join(lines)
