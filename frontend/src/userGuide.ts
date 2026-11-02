import type { UserRole } from "./types";

export type GuideStep = { title: string; description: string };
export type RoleGuide = { title: string; intro: string; steps: GuideStep[]; example: string };

export const commonGuideSteps: GuideStep[] = [
  { title: "选择工作台并新建草案", description: "在顶部切换到适合自己的工作台，点击左侧“新建草案”，填写主题或课题名称，并选择一个流程。" },
  { title: "按阶段与主导师协作", description: "查看左侧当前阶段，在中间对话区说明目标、背景、已有条件和希望得到的帮助，然后点击“发送”。" },
  { title: "编辑并保存方案", description: "在右侧编辑方案内容，点击“保存”保留当前阶段草稿；需要检查排版时点击“预览与审阅”。" },
  { title: "定稿并导出", description: "确认当前阶段后点击“定稿并进入下一阶段”。完成流程后，点击“导出”下载方案。" },
];

export const commonHelpItems: GuideStep[] = [
  { title: "主导师与领域专家", description: "主导师负责阶段引导和流程推进。选择领域专家后，他会针对本轮问题提供建议；需要继续推进整体流程时切回主导师。" },
  { title: "上传参考资料", description: "点击输入框旁的回形针上传 PDF、DOCX、TXT 或 MD。每个文件不超过 20 MB，每个会话最多 10 个文件，正文合计最多 50,000 字符；扫描版 PDF 暂不支持 OCR。" },
  { title: "让 AI 修订草案", description: "点击“草案”开启草案模式。修订已有内容时，先在右侧选中要修改的段落，再发送修改要求；可以先预览与审阅候选内容。" },
  { title: "保存、回滚和导出", description: "“保存”保留当前阶段草稿；“回滚”回到上一阶段；“定稿并进入下一阶段”会推进流程；“导出”下载方案文件。" },
  { title: "生成中断或遇到问题", description: "停止生成时本轮内容不会保存。若页面未连接、上传失败或任务列表为空，先检查网络、当前工作台和文件限制，再重试或联系管理员。" },
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
    intro: "基地管理者通过项目协同设置场景并发布任务；任务执行人员在任务大厅领取任务，完成后提交报告。",
    steps: [
      { title: "找到可领取任务", description: "点击顶部“项目协同”，查看面向当前工作台发布的任务、地点和任务要求。" },
      { title: "查看场景资料", description: "展开“查看场景与物料”，了解活动背景、物料清单和基地提供的附件。" },
      { title: "领取并完成任务", description: "点击“领取并开始”进入对应流程，按阶段与主导师协作；需要继续时可从“我的任务”重新打开。" },
      { title: "完成后提交报告", description: "完成工作流最后阶段后，系统会自动形成相应报告并提交给基地。" },
    ],
    example: "领取“校园昆虫观察”任务后，先查看观察区域和物料说明，再按流程完成观察设计；完成最后阶段后，报告会自动提交。",
  },
};

export const roleGuideTabs: { role: UserRole; label: string }[] = [
  { role: "teacher", label: "教师" },
  { role: "parent", label: "家长" },
  { role: "study_travel", label: "研学基地" },
];
