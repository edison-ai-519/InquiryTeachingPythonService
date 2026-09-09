import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const {
  WORKSPACE_DIR,
  RUNTIME_NODE_MODULES,
  SKILL_DIR,
  RUNTIME_PYTHON,
} = process.env;

if (!WORKSPACE_DIR || !RUNTIME_NODE_MODULES || !SKILL_DIR || !RUNTIME_PYTHON) {
  throw new Error("WORKSPACE_DIR, RUNTIME_NODE_MODULES, SKILL_DIR and RUNTIME_PYTHON are required");
}

const artifactToolPath = path.join(RUNTIME_NODE_MODULES, "@oai", "artifact-tool", "dist", "artifact_tool.mjs");
const { Presentation, PresentationFile } = await import(pathToFileURL(artifactToolPath).href);
const utilsPath = path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs");
const { finalizePresentation } = await import(pathToFileURL(utilsPath).href);

const W = 1280;
const H = 720;
const expectedSlideSizeEmu = "12192000,6858000";
const outDir = path.join(WORKSPACE_DIR, "outputs");
const buildDir = path.join(WORKSPACE_DIR, ".codex_artifacts", "build_ai_inquiry_ppt");
await fs.mkdir(outDir, { recursive: true });
await fs.mkdir(buildDir, { recursive: true });

const colors = {
  ink: "#11374A",
  deep: "#075B61",
  teal: "#0DB8B1",
  mint: "#BFF4DF",
  blue: "#287DB5",
  line: "#A9EADF",
  pale: "#EFFFF9",
  soft: "#F7FEFC",
  gray: "#526A76",
  faint: "#DDF7EF",
  white: "#FFFFFF",
};

const font = "Microsoft YaHei";
const refImages = [
  "C:\\Users\\14011\\AppData\\Local\\Temp\\codex-clipboard-c8f09716-3ed2-4fd0-a684-56e33aa53fe2.png",
  "C:\\Users\\14011\\AppData\\Local\\Temp\\codex-clipboard-dee10173-0a11-42b8-b12f-da823af834fe.png",
  "C:\\Users\\14011\\AppData\\Local\\Temp\\codex-clipboard-a5c14601-d25d-4099-84bd-aa0224d1bf67.png",
  "C:\\Users\\14011\\AppData\\Local\\Temp\\codex-clipboard-2a691e71-fb09-4f13-93ba-01ee8afdbc84.png",
  "C:\\Users\\14011\\AppData\\Local\\Temp\\codex-clipboard-07eb9d0a-edaa-4557-96bf-b4b7a3e3132e.png",
];
const imageBytes = await Promise.all(refImages.map((file) => fs.readFile(file)));

function addText(slide, text, pos, style = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: pos,
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  box.text = text;
  box.text.style = {
    typeface: font,
    fontSize: style.fontSize ?? 22,
    bold: style.bold ?? false,
    color: style.color ?? colors.ink,
    alignment: style.alignment ?? "left",
    autoFit: "shrinkText",
  };
  return box;
}

function addTitle(slide, title, subtitle = "", section = "") {
  addText(slide, section || "AI FOR INQUIRY TEACHING", { left: 70, top: 36, width: 520, height: 26 }, {
    fontSize: 13,
    bold: true,
    color: colors.teal,
  });
  slide.shapes.add({
    geometry: "line",
    position: { left: 70, top: 72, width: 250, height: 0 },
    fill: "none",
    line: { style: "solid", fill: colors.line, width: 2 },
  });
  addText(slide, title, { left: 70, top: 92, width: 740, height: 70 }, {
    fontSize: 42,
    bold: true,
    color: colors.deep,
  });
  if (subtitle) {
    addText(slide, subtitle, { left: 72, top: 162, width: 720, height: 40 }, {
      fontSize: 19,
      color: colors.gray,
    });
  }
}

function addFooter(slide, page) {
  slide.shapes.add({
    geometry: "line",
    position: { left: 72, top: 666, width: 360, height: 0 },
    fill: "none",
    line: { style: "solid", fill: colors.line, width: 1.2 },
  });
  addText(slide, "InquiryTeachingPythonService 项目汇报", { left: 460, top: 650, width: 360, height: 28 }, {
    fontSize: 13,
    color: "#6F8792",
    alignment: "center",
  });
  addText(slide, String(page).padStart(2, "0"), { left: 1138, top: 638, width: 70, height: 36 }, {
    fontSize: 21,
    bold: true,
    color: colors.teal,
    alignment: "right",
  });
}

function addBackground(slide, { withArc = true, imageIndex = null } = {}) {
  slide.background.fill = colors.soft;
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: W, height: 30 },
    fill: "#D7FAEF",
    line: { fill: "none", width: 0 },
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 690, width: W, height: 30 },
    fill: "#F0FFFA",
    line: { fill: "none", width: 0 },
  });
  if (withArc) {
    slide.shapes.add({
      geometry: "ellipse",
      position: { left: 0, top: 90, width: 180, height: 180 },
      fill: "#DDF7EF/70",
      line: { fill: "none", width: 0 },
    });
    slide.shapes.add({
      geometry: "ellipse",
      position: { left: 1010, top: 24, width: 210, height: 210 },
      fill: "#DFF8FF/45",
      line: { fill: "none", width: 0 },
    });
  }
  if (imageIndex !== null) {
    slide.images.add({
      blob: imageBytes[imageIndex],
      contentType: "image/png",
      alt: "用户提供的自然风教育科技参考图",
      fit: "cover",
      position: { left: 842, top: 78, width: 360, height: 202 },
      geometry: "roundRect",
      borderRadius: "rounded-xl",
    });
  }
}

function addCard(slide, pos, title, body, number = "", accent = colors.teal) {
  const shape = slide.shapes.add({
    geometry: "roundRect",
    position: pos,
    fill: colors.white,
    line: { style: "solid", fill: "#D1F2EA", width: 1.2 },
    borderRadius: 18,
    shadow: "shadow-sm",
  });
  if (number) {
    addText(slide, number, { left: pos.left + pos.width - 66, top: pos.top + 16, width: 44, height: 28 }, {
      fontSize: 22,
      bold: true,
      color: "#7DDCCC",
      alignment: "right",
    });
  }
  slide.shapes.add({
    geometry: "roundRect",
    position: { left: pos.left + 22, top: pos.top + 24, width: 8, height: 48 },
    fill: accent,
    line: { fill: "none", width: 0 },
    borderRadius: 6,
  });
  addText(slide, title, { left: pos.left + 44, top: pos.top + 22, width: pos.width - 96, height: 46 }, {
    fontSize: 23,
    bold: true,
    color: colors.deep,
  });
  const bodyOffset = pos.height < 112 ? 58 : 82;
  const bodyHeight = Math.max(1, pos.height - bodyOffset - 14);
  addText(slide, body, { left: pos.left + 44, top: pos.top + bodyOffset, width: pos.width - 70, height: bodyHeight }, {
    fontSize: pos.height < 112 ? 14 : 17,
    color: colors.gray,
  });
  return shape;
}

function addTag(slide, text, left, top, width = 150) {
  const pill = slide.shapes.add({
    geometry: "roundRect",
    position: { left, top, width, height: 34 },
    fill: "#E6FBF4",
    line: { style: "solid", fill: "#BEEFE3", width: 1 },
    borderRadius: 17,
  });
  pill.text = text;
  pill.text.style = {
    typeface: font,
    fontSize: 14,
    bold: true,
    color: colors.deep,
    alignment: "center",
    autoFit: "shrinkText",
  };
  return pill;
}

function addBulletList(slide, items, left, top, width, lineHeight = 38, fontSize = 19) {
  items.forEach((item, index) => {
    const y = top + index * lineHeight;
    slide.shapes.add({
      geometry: "ellipse",
      position: { left, top: y + 9, width: 10, height: 10 },
      fill: colors.teal,
      line: { fill: "none", width: 0 },
    });
    addText(slide, item, { left: left + 22, top: y, width, height: lineHeight }, {
      fontSize,
      color: colors.ink,
    });
  });
}

function note(slide, text) {
  slide.speakerNotes.textFrame.setText(text);
}

function createTemplateDeck() {
  const p = Presentation.create({ slideSize: { width: W, height: H } });
  const slides = [];

  let s = p.slides.add();
  slides.push(s);
  addBackground(s);
  s.images.add({ blob: imageBytes[0], contentType: "image/png", alt: "自然风教育科技封面参考", fit: "cover", position: { left: 710, top: 70, width: 500, height: 430 }, geometry: "roundRect", borderRadius: 22 });
  addText(s, "自然探究教育汇报模板", { left: 72, top: 172, width: 610, height: 68 }, { fontSize: 46, bold: true, color: colors.deep });
  addText(s, "适用于自然教育、探究式教学、AI 助教与课程项目汇报", { left: 76, top: 258, width: 590, height: 74 }, { fontSize: 22, color: colors.gray });
  addTag(s, "清爽专业", 78, 382);
  addTag(s, "自然风", 250, 382);
  addTag(s, "教育科技", 390, 382);
  addFooter(s, 1);
  note(s, "模板参考页。视觉来源为用户提供的自然风教育科技图片，用于以后自然教育和探究式教学汇报复用。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "章节页版式", "大号页码、浅色留白、青绿色强调线", "CHAPTER");
  addText(s, "01", { left: 88, top: 220, width: 300, height: 180 }, { fontSize: 150, bold: true, color: "#BDF1E0" });
  addText(s, "项目背景与目标", { left: 430, top: 292, width: 520, height: 58 }, { fontSize: 42, bold: true, color: colors.ink });
  addText(s, "用于每个大章节开场，保持画面轻盈，突出主题", { left: 434, top: 366, width: 540, height: 38 }, { fontSize: 20, color: colors.gray });
  addFooter(s, 2);
  note(s, "模板参考页。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "内容页版式", "左侧观点，右侧四个证据块");
  addCard(s, { left: 70, top: 240, width: 360, height: 300 }, "页面主论点", "用较短文字说明本页要表达的核心判断，适合项目概述、问题背景和价值说明。", "", colors.teal);
  addCard(s, { left: 490, top: 220, width: 300, height: 140 }, "证据一", "一到两句话说明具体能力。", "01", colors.teal);
  addCard(s, { left: 820, top: 220, width: 300, height: 140 }, "证据二", "一到两句话说明具体能力。", "02", colors.blue);
  addCard(s, { left: 490, top: 390, width: 300, height: 140 }, "证据三", "一到两句话说明具体能力。", "03", colors.blue);
  addCard(s, { left: 820, top: 390, width: 300, height: 140 }, "证据四", "一到两句话说明具体能力。", "04", colors.teal);
  addFooter(s, 3);
  note(s, "模板参考页。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "图解页版式", "适合系统架构、流程图和路线图");
  const nodes = [
    ["输入", 110, 290],
    ["编排", 360, 290],
    ["生成", 610, 290],
    ["审阅", 860, 290],
  ];
  nodes.forEach(([label, x, y], index) => {
    addCard(s, { left: x, top: y, width: 170, height: 100 }, label, index === 0 ? "资料与问题" : index === 1 ? "流程与专家" : index === 2 ? "草案与资源" : "教师确认", String(index + 1).padStart(2, "0"), index % 2 ? colors.blue : colors.teal);
    if (index < nodes.length - 1) {
      s.shapes.add({ geometry: "line", position: { left: x + 178, top: y + 50, width: 70, height: 0 }, fill: "none", line: { style: "solid", fill: colors.teal, width: 2 } });
    }
  });
  addFooter(s, 4);
  note(s, "模板参考页。");

  return { presentation: p, slides };
}

function createFinalDeck() {
  const p = Presentation.create({ slideSize: { width: W, height: H } });
  const slides = [];

  let s = p.slides.add();
  slides.push(s);
  addBackground(s);
  s.images.add({ blob: imageBytes[0], contentType: "image/png", alt: "AI 探究式教学助手视觉参考", fit: "cover", position: { left: 720, top: 64, width: 500, height: 450 }, geometry: "roundRect", borderRadius: 24 });
  addText(s, "AI 探究式教学助手", { left: 74, top: 156, width: 620, height: 72 }, { fontSize: 50, bold: true, color: colors.deep });
  addText(s, "InquiryTeachingPythonService 成果展示", { left: 78, top: 244, width: 610, height: 44 }, { fontSize: 26, bold: true, color: colors.ink });
  addText(s, "当前成果 · 项目特点 · 技术架构 · 未来方向", { left: 80, top: 330, width: 640, height: 34 }, { fontSize: 21, color: colors.gray });
  addTag(s, "教师在环", 82, 438, 136);
  addTag(s, "阶段化流程", 242, 438, 150);
  addTag(s, "智能协同", 416, 438, 136);
  addFooter(s, 1);
  note(s, "内容依据当前仓库 README、PROJECT_STRUCTURE、前后端代码和已生成的发展规划文档整理。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s, { imageIndex: 1 });
  addTitle(s, "项目背景与目标", "从教师备课痛点出发，构建可持续打磨的探究式教学助手", "CHAPTER");
  addCard(s, { left: 74, top: 242, width: 340, height: 280 }, "项目定位", "面向中小学教师，围绕真实课堂探究活动，辅助完成教学设计、课堂实施与迭代优化。", "", colors.teal);
  addCard(s, { left: 462, top: 252, width: 310, height: 120 }, "服务对象", "一线教师与课堂探究活动", "01", colors.teal);
  addCard(s, { left: 812, top: 252, width: 310, height: 120 }, "主要目标", "辅助完成教学设计与迭代", "02", colors.blue);
  addCard(s, { left: 462, top: 402, width: 310, height: 120 }, "输出形式", "对话、草稿、导出资源", "03", colors.blue);
  addCard(s, { left: 812, top: 402, width: 310, height: 120 }, "项目价值", "提升设计效率与探究质量", "04", colors.teal);
  addFooter(s, 2);
  note(s, "参考 README 中项目定位、主导师与领域专家、会话参考资料等说明。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "七阶段探究式教学流", "以阶段推进保证教学方案逐步成形");
  const stages = ["导入情境", "提出问题", "猜想假设", "设计方案", "观察实验", "表达交流", "总结评价"];
  stages.forEach((stage, i) => {
    const x = 82 + i * 162;
    const y = 318;
    const node = s.shapes.add({ geometry: "ellipse", position: { left: x, top: y, width: 92, height: 92 }, fill: i % 2 === 0 ? "#D8FAEF" : "#E1F6FF", line: { style: "solid", fill: colors.line, width: 1.4 } });
    node.text = String(i + 1).padStart(2, "0");
    node.text.style = { typeface: font, fontSize: 24, bold: true, color: colors.deep, alignment: "center" };
    addText(s, stage, { left: x - 26, top: y + 106, width: 146, height: 32 }, { fontSize: 18, bold: true, color: colors.ink, alignment: "center" });
    if (i < stages.length - 1) {
      s.shapes.add({ geometry: "line", position: { left: x + 100, top: y + 46, width: 62, height: 0 }, fill: "none", line: { style: "solid", fill: colors.teal, width: 2 } });
    }
  });
  addText(s, "流程价值", { left: 86, top: 528, width: 120, height: 34 }, { fontSize: 22, bold: true, color: colors.deep });
  addBulletList(s, ["把一次开放对话转化为可推进的教学过程", "每个阶段保留草案，教师可以确认、回退和继续打磨", "适合科学探究、自然观察和跨学科项目学习"], 210, 526, 820, 34, 18);
  addFooter(s, 3);
  note(s, "七阶段流程来自项目工作流设计。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "教师在环机制", "教师掌握关键判断，AI 负责整理、建议和生成");
  const hitl = [
    ["设定目标", "主题、年级、场地、课时"],
    ["选择专家", "按问题选择合适顾问"],
    ["审阅草案", "接受、拒绝或继续追问"],
    ["确认成果", "导出并用于真实课堂"],
  ];
  hitl.forEach(([t, b], i) => {
    addCard(s, { left: 90 + i * 285, top: 250, width: 240, height: 178 }, t, b, String(i + 1).padStart(2, "0"), i % 2 ? colors.blue : colors.teal);
  });
  addText(s, "这套机制让教师专业判断保留在流程中心。AI 不直接替教师拍板，而是把资料、建议和草案整理到更容易判断的位置。", { left: 140, top: 500, width: 1000, height: 70 }, { fontSize: 22, color: colors.ink, alignment: "center" });
  addFooter(s, 4);
  note(s, "教师在环基于当前交互流程：阶段推进、专家选择、草案审阅和导出。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "主导师与专家 Agent 协同", "主导师推进全局，领域专家处理本轮专业问题");
  const main = addCard(s, { left: 486, top: 250, width: 310, height: 156 }, "主导师 Agent", "流程推进、上下文维护、草案生成、专家建议整合", "M", colors.teal);
  const expertLabels = [
    ["昆虫", 116, 178],
    ["自然生态", 290, 178],
    ["数学数据", 884, 178],
    ["安全伦理", 1058, 178],
    ["物理探究", 290, 470],
    ["课程知识", 884, 470],
  ];
  expertLabels.forEach(([label, x, y], i) => {
    addCard(s, { left: x, top: y, width: 150, height: 94 }, label, i === 5 ? "RAG 支撑" : "本轮建议", "", i % 2 ? colors.blue : colors.teal);
    if (x < 500) {
      s.shapes.add({ geometry: "line", position: { left: x + 150, top: y + 47, width: 486 - x - 150, height: 0 }, fill: "none", line: { style: "solid", fill: "#8ADFD5", width: 1.5 } });
    } else {
      s.shapes.add({ geometry: "line", position: { left: 796, top: y + 47, width: x - 796, height: 0 }, fill: "none", line: { style: "solid", fill: "#8ADFD5", width: 1.5 } });
    }
  });
  addText(s, "专家回答后自动回到主导师，避免多角色同时改写最终教案。", { left: 260, top: 602, width: 760, height: 32 }, { fontSize: 18, color: colors.gray, alignment: "center" });
  addFooter(s, 5);
  note(s, "当前仓库配置包含 main_tutor 与昆虫、自然生态、数学、安全、物理等专家 Agent。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "系统架构与核心能力", "FastAPI、Vue3、SQLite 与 SSE 支撑实时教学工作台");
  const layers = [
    ["前端工作台", "Vue3 / 聊天 / 草稿 / 导出", ["对话交互", "内容草稿", "一键导出"]],
    ["服务编排层", "FastAPI / SSE / 流程管理", ["API 服务", "SSE 流式", "流程推进"]],
    ["Agent 能力层", "主导师 / 专家 / RAG", ["主导师", "阶段专家", "知识增强"]],
    ["数据与存储层", "SQLite / 会话 / 草稿 / 知识库", ["会话数据", "草稿数据", "知识片段"]],
  ];
  layers.forEach(([name, desc, chips], i) => {
    const y = 166 + i * 104;
    addCard(s, { left: 76, top: y, width: 780, height: 82 }, name, desc, String(i + 1).padStart(2, "0"), i % 2 ? colors.blue : colors.teal);
    chips.forEach((chip, j) => addTag(s, chip, 486 + j * 122, y + 25, 104));
  });
  s.images.add({ blob: imageBytes[3], contentType: "image/png", alt: "系统架构参考视觉", fit: "cover", position: { left: 900, top: 178, width: 258, height: 258 }, geometry: "ellipse" });
  addText(s, "技术目标：让教师在一个工作台里完成咨询、生成、审阅和沉淀。", { left: 874, top: 482, width: 320, height: 78 }, { fontSize: 18, color: colors.ink, alignment: "center" });
  addFooter(s, 6);
  note(s, "架构依据 README 与 PROJECT_STRUCTURE：FastAPI 后端、Vue3 前端、SQLite 数据库、SSE 流式响应。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "会话、草稿、回滚与导出", "当前成果已经覆盖教师从讨论到成稿的主要动作");
  const cycle = [
    ["创建会话", "围绕主题形成项目空间", 162, 252],
    ["上传资料", "补充校本材料与参考文本", 430, 252],
    ["生成草稿", "主导师输出阶段化内容", 698, 252],
    ["审阅修改", "教师确认后继续推进", 430, 438],
    ["回滚导出", "保留可控迭代和成果沉淀", 698, 438],
  ];
  cycle.forEach(([t, b, x, y], i) => {
    addCard(s, { left: x, top: y, width: 214, height: 118 }, t, b, String(i + 1).padStart(2, "0"), i % 2 ? colors.blue : colors.teal);
  });
  s.shapes.add({ geometry: "line", position: { left: 376, top: 310, width: 48, height: 0 }, fill: "none", line: { style: "solid", fill: colors.teal, width: 2 } });
  s.shapes.add({ geometry: "line", position: { left: 644, top: 310, width: 48, height: 0 }, fill: "none", line: { style: "solid", fill: colors.teal, width: 2 } });
  s.shapes.add({ geometry: "line", position: { left: 805, top: 374, width: 0, height: 58 }, fill: "none", line: { style: "solid", fill: colors.teal, width: 2 } });
  s.shapes.add({ geometry: "line", position: { left: 644, top: 496, width: 48, height: 0 }, fill: "none", line: { style: "solid", fill: colors.teal, width: 2 } });
  addText(s, "这些能力让平台从聊天工具变成可持续打磨的教学创作环境。", { left: 164, top: 584, width: 820, height: 32 }, { fontSize: 20, color: colors.gray, alignment: "center" });
  addFooter(s, 7);
  note(s, "依据当前 App.vue、session_files、sessions、export 等模块能力整理。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "课程知识库与 RAG", "课标文件可上传、授权、检索和审计");
  addCard(s, { left: 86, top: 226, width: 300, height: 260 }, "资料入口", "管理员上传 PDF、DOCX、TXT、MD。系统提取正文、切分片段，并写入课程知识库。", "01", colors.teal);
  addCard(s, { left: 438, top: 226, width: 300, height: 260 }, "权限控制", "新文件默认未授权。管理员按专家配置可查询来源，下一轮咨询立即生效。", "02", colors.blue);
  addCard(s, { left: 790, top: 226, width: 300, height: 260 }, "混合检索", "BM25 与本地向量检索结合。向量不可用时可退回 BM25，保证基础可用。", "03", colors.teal);
  addText(s, "检索记录会保存专家 ID、授权来源、命中片段和评分，便于教学内容追踪。", { left: 140, top: 540, width: 930, height: 34 }, { fontSize: 20, color: colors.ink, alignment: "center" });
  addFooter(s, 8);
  note(s, "依据 README 中本地课标混合 RAG 与 curriculum_knowledge_service、rag_service、curriculum_permission_service。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s, { imageIndex: 2 });
  addTitle(s, "当前完成情况", "核心闭环已经形成，下一步重点转向试点化和后台化");
  const doneItems = [
    ["已完成", "登录与会话隔离", "教师可独立创建和管理会话"],
    ["已完成", "主导师与专家", "支持显式选择专家进行本轮咨询"],
    ["已完成", "课标 RAG", "支持文件上传、权限、检索和审计"],
    ["已完成", "草案工作台", "支持编辑、审阅、保存和导出"],
    ["待增强", "后台管理", "需要组织、项目、数据和日志管理"],
    ["待增强", "课堂数据", "需要学生观察记录和长期项目档案"],
  ];
  doneItems.forEach(([state, name, desc], i) => {
    const x = i % 2 === 0 ? 86 : 634;
    const y = 204 + Math.floor(i / 2) * 116;
    addCard(s, { left: x, top: y, width: 476, height: 88 }, name, desc, state === "已完成" ? "✓" : "…", state === "已完成" ? colors.teal : colors.blue);
  });
  addFooter(s, 9);
  note(s, "完成情况依据当前仓库模块与已完成文档汇总。");

  s = p.slides.add();
  slides.push(s);
  addBackground(s);
  addTitle(s, "未来路线图", "从备课助手走向自然探究项目平台");
  const roadmap = [
    ["近期", "打磨标杆场景", "昆虫生命周期观察、课程包样例、关键接口并发测试"],
    ["中期", "后台数据管理", "用户、学校、班级、项目、知识库、日志和权限管理"],
    ["长期", "课堂数据闭环", "学生记录、图片、传感器、成长档案和区域项目管理"],
  ];
  roadmap.forEach(([phase, title, body], i) => {
    const x = 108 + i * 370;
    const top = 238;
    const phaseNode = s.shapes.add({ geometry: "ellipse", position: { left: x + 100, top: 150, width: 86, height: 86 }, fill: i === 0 ? "#D8FAEF" : i === 1 ? "#E0F6FF" : "#E9FFF4", line: { style: "solid", fill: colors.line, width: 1.4 } });
    phaseNode.text = phase;
    phaseNode.text.style = { typeface: font, fontSize: 18, bold: true, color: colors.deep, alignment: "center", autoFit: "shrinkText" };
    addCard(s, { left: x, top, width: 292, height: 230 }, title, body, String(i + 1).padStart(2, "0"), i === 1 ? colors.blue : colors.teal);
    if (i < roadmap.length - 1) {
      s.shapes.add({ geometry: "line", position: { left: x + 300, top: top + 116, width: 62, height: 0 }, fill: "none", line: { style: "solid", fill: colors.teal, width: 2 } });
    }
  });
  addText(s, "并发测试重点：多人登录、SSE 流式响应、文件上传、RAG 权限、索引重建和数据库锁冲突。", { left: 150, top: 546, width: 980, height: 44 }, { fontSize: 19, color: colors.ink, alignment: "center" });
  addFooter(s, 10);
  note(s, "未来方向依据平台未来发展方向与测试规划文档整理，重点包括后台系统、长期观察昆虫生命周期和并发测试。");

  return { presentation: p, slides };
}

async function exportDeck(presentation, finalPath, requirements) {
  const candidatePath = path.join(buildDir, `${path.basename(finalPath, ".pptx")}.candidate.pptx`);
  await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
  const result = await finalizePresentation({
    ...requirements,
    workspaceDir: WORKSPACE_DIR,
    candidatePath,
    finalPath,
    pythonExecutable: RUNTIME_PYTHON,
    integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
    layoutArgs: [
      "--expected-slide-size-emu", expectedSlideSizeEmu,
      "--validate-heading-fit",
    ],
    requiredNativeTableOwnerSlides: [],
    fontPolicy: {
      basis: "design",
      families: [font],
      scriptFonts: { ea: font },
    },
    verifyArtifactToolImport: true,
    receiptPath: path.join(buildDir, `${path.basename(finalPath)}.validation.json`),
  });
  return result;
}

async function renderSlides(presentation, slides, prefix) {
  const files = [];
  for (let i = 0; i < slides.length; i += 1) {
    const slide = slides[i];
    const blob = await presentation.export({ slide, format: "png", scale: 1 });
    const file = path.join(buildDir, `${prefix}-${String(i + 1).padStart(2, "0")}.png`);
    await fs.writeFile(file, new Uint8Array(await blob.arrayBuffer()));
    files.push(file);
  }
  const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
  const montagePath = path.join(buildDir, `${prefix}-montage.webp`);
  await fs.writeFile(montagePath, new Uint8Array(await montage.arrayBuffer()));
  return { files, montagePath };
}

const templateDeck = createTemplateDeck();
const templateReferencePath = path.join(buildDir, "natural-inquiry-template-reference.pptx");
await (await PresentationFile.exportPptx(templateDeck.presentation)).save(templateReferencePath);
const templatePreview = await templateDeck.presentation.export({ slide: templateDeck.slides[0], format: "png", scale: 1 });
const templatePreviewPath = path.join(buildDir, "natural-inquiry-template-preview.png");
await fs.writeFile(templatePreviewPath, new Uint8Array(await templatePreview.arrayBuffer()));

const finalDeck = createFinalDeck();
const finalPath = path.join(outDir, "AI探究式教学助手成果展示_v1.pptx");
await exportDeck(finalDeck.presentation, finalPath, {
  explicitTotalSlideCount: 10,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
});
const previews = await renderSlides(finalDeck.presentation, finalDeck.slides, "ai-inquiry-final");

console.log(JSON.stringify({
  templateReferencePath,
  templatePreviewPath,
  finalPath,
  previewMontage: previews.montagePath,
  previewFiles: previews.files,
}, null, 2));
