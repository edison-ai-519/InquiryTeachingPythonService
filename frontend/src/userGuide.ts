import type { UserRole } from "./types";

export type GuideStep = { title: string; description: string };
export type RoleGuide = { title: string; intro: string; steps: GuideStep[]; example: string };

export const commonGuideSteps: GuideStep[] = [
  { title: "开始一个课题或任务", description: "教师和家长点击左侧“新建草案”或从“任务大厅”领取任务；研学基地人员在“项目协同”中创建场景并发布任务。" },
  { title: "告诉主导师你的情况", description: "在中间对话区说明目标、背景、参与对象和已有条件。主导师负责阶段引导；领域专家只回答当前这一轮问题。" },
  { title: "查看建议并整理方案", description: "在右侧编辑内容。页面会标明“未保存”“保存中”或“已保存”；需要检查排版或 AI 修订时再打开“预览与审阅”。" },
  { title: "确认阶段并完成方案", description: "当前阶段内容会在定稿推进时一并提交。最后一阶段完成后，可导出方案；研学任务会按任务流程提交报告。" },
];

export const commonHelpItems: GuideStep[] = [
  { title: "主导师与领域专家", description: "主导师负责阶段引导和流程推进。选择领域专家后，他会针对本轮问题提供建议；需要继续推进整体流程时切回主导师。" },
  { title: "上传参考资料", description: "点击输入框旁的回形针上传 PDF、DOCX、TXT 或 MD。每个文件不超过 20 MB，每个会话最多 10 个文件，正文合计最多 50,000 字符；扫描版 PDF 暂不支持 OCR。" },
  { title: "让 AI 修订草案", description: "草案模式用于生成初稿或修订内容。修订已有草案时，先选中右侧要修改的段落；发送按钮会说明还缺少什么条件。" },
  { title: "确认保存状态", description: "编辑后看到“未保存”表示修改仍在本地；“保存中”表示正在提交；“已保存”表示服务器已确认。保存失败时，内容仍留在编辑区，可以点击“重试保存”。" },
  { title: "推进阶段、回滚和导出", description: "定稿推进会提交当前阶段内容并进入下一阶段。回滚会撤回最近一轮或退回上一阶段；完成流程后可导出方案。" },
  { title: "生成或任务失败时", description: "生成失败时，输入内容仍可重新发送；阶段推进失败时，当前内容会保留并可重试。上传失败可查看文件提示并检查格式和大小。" },
];

export const userGuideByRole: Record<UserRole, RoleGuide> = {
  teacher: {
    title: "教师工作台",
    intro: "围绕教学课题逐阶段设计探究式教案。主导师负责推进流程，领域专家可为当前问题提供补充建议。",
    steps: [
      { title: "创建教学课题", description: "点击“新建草案”，输入课题名称并选择适用流程。" },
      { title: "描述教学情境", description: "告诉主导师学生年级、学习目标、课时和已有资源，逐阶段完善教学方案。" },
      { title: "按需咨询领域专家", description: "在顶部“本轮咨询”选择专家并发送具体问题。专家建议针对本轮咨询；流程推进仍由主导师负责。" },
      { title: "整理并导出教案", description: "在右侧编辑、保存和审阅阶段内容，逐步定稿，最后导出完整教案。" },
    ],
    example: "三年级学生要学习光的传播，计划用一课时探究。教室有手电筒、镜子和白纸，请先帮我设计能引出学生问题的导入活动。",
  },
  parent: {
    title: "家长工作台",
    intro: "从孩子感兴趣的现象出发，结合年龄、家庭空间和可用材料设计安全、适龄的亲子探究活动。",
    steps: [
      { title: "创建家庭探究活动", description: "点击“新建草案”并填写探究主题。孩子年龄/年级、活动时长、家庭空间、材料和成人陪伴情况均可选填。" },
      { title: "描述观察与兴趣", description: "告诉主导师孩子看到了什么、提出了什么问题，以及家庭可用的时间和材料。" },
      { title: "一起观察和尝试", description: "按当前阶段的引导开展活动，优先用开放式问题鼓励孩子描述和猜想；结合孩子年龄检查安全安排。" },
      { title: "完善家庭活动方案", description: "在右侧直接修改活动内容，保存、预览并逐阶段定稿，完成后导出家庭探究活动方案。" },
    ],
    example: "孩子八岁，在阳台看到雨后叶片上的小水珠。我们有放大镜，可以陪伴半小时，请帮我用开放式问题引导观察，不要先告诉孩子原因。",
  },
  study_travel: {
    title: "研学基地工作台",
    intro: "基地管理者通过项目协同设置场景、发布任务并整理各类工作台提交的报告。教师和家长在各自工作台的任务大厅领取任务。",
    steps: [
      { title: "创建研学项目", description: "打开顶部“项目协同”，创建项目并补充地点、场景说明、物料和附件。" },
      { title: "制定并发布任务", description: "选择教师或家长工作台，填写任务目标和对应流程，再发布给任务执行人员。" },
      { title: "查看任务进度", description: "在项目任务列表中查看领取与提交情况；执行人员完成流程后会自动提交报告。" },
      { title: "整理项目成果", description: "查看各任务报告，在“基地人工汇总”中整理项目成果并保存。" },
    ],
    example: "为“古道自然观察”创建项目，补充地点和物料，再给教师工作台发布半天观察设计任务。",
  },
};

export const roleGuideTabs: { role: UserRole; label: string }[] = [
  { role: "teacher", label: "教师" },
  { role: "parent", label: "家长" },
  { role: "study_travel", label: "研学基地" },
];
