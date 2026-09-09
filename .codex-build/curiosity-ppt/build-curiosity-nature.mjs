import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "D:\\javacode\\InquiryTeachingPythonService";
const SKILL_DIR = "C:\\Users\\14011\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.905.11957\\skills\\presentations";
const RUNTIME_PYTHON = "C:\\Users\\14011\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";
const templatePath = "D:\\桌面\\BUPT\\2024-北邮人专属PPT模板\\2024文艺风绿色.pptx";
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
const buildDir = path.join(workspaceDir, ".codex-build", "curiosity-ppt");
const FINAL_PPTX = path.join(workspaceDir, "outputs", "好奇自然项目介绍-8页.pptx");

await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const presentation = await PresentationFile.importPptx(await FileBlob.load(templatePath));

while (presentation.slides.count > 8) {
  presentation.slides.remove(presentation.slides.getItem(8));
}

const set = (id, text) => {
  const shape = presentation.resolve(id);
  shape.text = text;
};

const note = (slideIndex, text) => {
  presentation.slides.getItem(slideIndex).speakerNotes.textFrame.setText(text);
};

// 1 封面
set("sh/jm1kbuds", "CURIOSITY NATURE");
set("sh/ul4vaxgb", "“好奇自然”项目");
set("sh/vmdcj2xw", "让大自然成为永不枯竭的课堂");
set("sh/4r6dg7et", "乡村儿童探究教育实践");
set("sh/5sfepcfe", "以自然为课堂，以好奇心为引擎，结合教师赋能与 AI 支持，帮助儿童把每一次“为什么”变成真实探索。");
set("sh/3qxwn2x8", "项目半年期策划方案");
set("sh/ozmd8r65", "BUPT");
set("sh/ipovexwn", "2026");
note(0, "内容来源：用户提供的项目整理文本。");

// 2 目录
set("sh/r65knqtk", "CONTENTS");
set("sh/x4r21kru", "目 录");
set("sh/u94fqp4n", "项目背景");
set("sh/p0vy54na", "为什么做“好奇自然”");
set("sh/69wbilcj", "项目理念");
set("sh/tw7ud0va", "建立怎样的教育");
set("sh/107uh0v6", "核心系统");
set("sh/gzydovul", "项目做什么、怎么运行");
set("sh/1wzix87i", "落地验证");
set("sh/et8zmto7", "半年计划与预期成果");
set("sh/r6x0rypg", "2026");
note(1, "内容来源：用户提供的项目整理文本。");

// 3 章节页
set("sh/d0jax03i", "01");
set("sh/3ah8rqlg", "项目背景");
set("sh/obq90bml", "WHY THIS PROJECT MATTERS");
set("sh/l4fi9cza", "孩子不缺好奇，缺少的是回应、方法和持续陪伴。");
note(2, "内容来源：用户提供的项目整理文本。");

// 4 背景
set("sh/rm1k7yt4", "WHY THIS PROJECT MATTERS");
set("sh/ql8jytsj", "为什么要做“好奇自然”");
set("sh/8v6983qh", "好奇缺少回应");
set("sh/9wfah8rm", "乡村儿童身边有田埂、星空、虫鸣和草木，很多问题却没有被及时接住。");
set("sh/a14ryt83", "场景缺少工具");
set("sh/b2ds7e9o", "教师和儿童服务站有真实场域，但缺少可操作的方法、资源与支持机制。");
set("sh/qpc3ylwr", "自然缺少读法");
set("sh/1wnmx0fe", "项目把自然观察转化为“惊奇、问题、探究、成长”的学习路径。");
set("sh/zul4vqx8", "项目切入点");
set("sh/etc32lw3", "用自然资源、儿童好奇和教师陪伴，构建可持续的探究教育实践。");
set("sh/18nu50nu", "2026");
note(3, "内容来源：用户提供的项目整理文本。");

// 5 理念
set("sh/z2tcnm5s", "EDUCATION MODEL");
set("sh/yhkbe1o7", "项目理念");
set("sh/65cnahc7", "大自然是永不枯竭的课堂\n学习从孩子真实的问题出发");
set("sh/2l4zip8j", "01.");
set("sh/povid4ra", "以自然为主场");
set("sh/onmhkzqp", "让学习发生在草木、虫鱼、星斗与四季变化之中。");
set("sh/l4bupwny", "02.");
set("sh/w32dkbuh", "以好奇为引擎");
set("sh/k7mxovud", "不是从知识点出发，而是从孩子的“为什么”出发。");
set("sh/ud0ne10b", "03.");
set("sh/5o7mhcju", "以教师为赋能者");
set("sh/vu5kbihc", "教师陪伴儿童观察、追问、实验，并连接外部资源。");
set("sh/zmlk3yhk", "《夏小正》 × 墨子四疑");
set("sh/kjelony9", "2026");
note(4, "内容来源：用户提供的项目整理文本。");

// 6 三大系统
set("sh/87ipkzal", "THREE CORE SYSTEMS");
set("sh/7m98ru9g", "三大核心系统");
set("sh/ml07i9sv", "项目不是单独做一门课程，而是建设三套彼此配合的系统。");
set("sh/zi98nu94", "从孩子的一次好奇，逐步形成可积累、可展示、可复制的教育生态。");
set("sh/svmt4v6t", "自然探索系统");
set("sh/cbe5g3ih", "1120 条自然观察知识库，100 个循疑实验主题，支持季节化探索。");
set("sh/zep4byhs", "好奇心博物馆");
set("sh/gju58ji9", "用好奇之墙沉淀问题、猜想、回应和反思，让发现持续生长。");
set("sh/u907axkf", "教师赋能系统");
set("sh/hcrqlcj6", "9 课培训、线上社群和 AI 辅助，形成 100、30、10 教师梯队。");
set("sh/7698f214", "2026");
note(5, "内容来源：用户提供的项目整理文本。");

// 7 运行机制与 AI
set("sh/ydkbm5sv", "GROWTH MECHANISM");
set("sh/zedcfa9g", "好奇心生长机制");
set("sh/wneps3ap", "项目让儿童经历“看见、发问、猜想、观察、发现、分享”的完整探究路径，并在分享后生成新的问题。");
set("sh/eh4jil4r", "孩子自治");
set("sh/jedkn654", "从参与者成长为“小墙主”，再把发现讲给同伴和社区。");
set("sh/e98nm9gr", "教师引导");
set("sh/fahofehc", "教师组织真实观察，帮助儿童把零散问题变成可验证的探究任务。");
set("sh/ra9k7ap8", "外部支持");
set("sh/jmtgjqto", "AI 按季节、场景和儿童问题推荐观察方向与实验路径。");
set("sh/uxkz61s7", "心理与教学支持帮助教师回应情绪、建设好奇之墙并处理现场问题。");
set("sh/ulc7qdsj", "2026");
note(6, "内容来源：用户提供的项目整理文本。");

// 8 落地与成果
set("sh/ri9g7uhw", "IMPLEMENTATION AND OUTCOMES");
set("sh/6h0fypgb", "半年实施与预期成果");
set("sh/pwjqho7u", "6个月\n验证");
set("sh/3u18fepo", "准备、启动、实践、深化、进阶、评估");
set("sh/2ts769o3", "完成一轮从试点建设到模式沉淀的验证，形成可复制的项目模式包。");
set("sh/na1sb2lg", "01");
set("sh/8bat47ml", "实施路径");
set("sh/9w3uds36", "6 个试点同步推进，先培训 100 名教师，再筛选 30 名骨干教师和 10 名种子教师。");
set("sh/07atgnmp", "02");
set("sh/l8ja9s3a", "成果沉淀");
set("sh/q18bad4n", "形成自然观察与实验探究模式、教师九课体系、AI 原型、儿童案例和评估工具。");
set("sh/budwj61c", "2026");
note(7, "内容来源：用户提供的项目整理文本。");

const candidatePath = path.join(stagingDir, "好奇自然项目介绍-8页.candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const { finalizePresentation } = await import(pathToFileURL(
  path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs"),
).href);

const result = await finalizePresentation({
  explicitTotalSlideCount: 8,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-heading-fit",
  ],
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  fontPolicy: {
    basis: "reference",
    families: presentation.fontFamilies,
    referencePath: templatePath,
  },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "好奇自然项目介绍-8页.validation.json"),
});

const finalDeck = await PresentationFile.importPptx(await FileBlob.load(FINAL_PPTX));
const montage = await finalDeck.export({ format: "png", montage: true, scale: 0.45 });
await fs.writeFile(path.join(buildDir, "final-montage.png"), new Uint8Array(await montage.arrayBuffer()));
for (let i = 0; i < finalDeck.slides.count; i += 1) {
  const png = await finalDeck.slides.getItem(i).export({ format: "png", scale: 0.75 });
  await fs.writeFile(path.join(buildDir, `final-slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({ finalPath: FINAL_PPTX, validation: result.status ?? "ok" }, null, 2));
