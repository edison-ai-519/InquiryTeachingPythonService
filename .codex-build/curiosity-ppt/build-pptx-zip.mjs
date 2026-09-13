import fs from "node:fs/promises";
import path from "node:path";
import JSZip from "jszip";

const templatePath = "D:\\桌面\\BUPT\\2024-北邮人专属PPT模板\\2024文艺风绿色.pptx";
const outPath = "D:\\javacode\\InquiryTeachingPythonService\\outputs\\好奇自然项目介绍-8页.pptx";

const escapeXml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;");

const replaceTexts = (xml, replacements) => {
  let index = 0;
  return xml.replace(/<p:sp\b[\s\S]*?<\/p:sp>/g, (shapeXml) => {
    if (!shapeXml.includes("<a:t>") || index >= replacements.length) return shapeXml;
    const text = replacements[index++];
    let replaced = false;
    return shapeXml.replace(/<a:t>([\s\S]*?)<\/a:t>/g, () => {
      if (replaced) return "<a:t></a:t>";
      replaced = true;
      return `<a:t>${escapeXml(text)}</a:t>`;
    });
  }).replace(/<a:t>([\s\S]*?)<\/a:t>/g, (match) => {
    if (index >= replacements.length) return match;
    const text = replacements[index++];
    return `<a:t>${escapeXml(text)}</a:t>`;
  });
};

const slideTexts = {
  1: [
    "CURIOSITY NATURE",
    "“好奇自然”项目",
    "让大自然成为永不枯竭的课堂",
    "乡村儿童探究教育实践",
    "以自然为课堂，以好奇心为引擎，结合教师赋能与 AI 支持，把每一次“为什么”变成真实探索。",
    "项目半年期策划方案",
    "BUPT",
    "2026",
  ],
  2: [
    "CONTENTS",
    "项目背景",
    "为什么做“好奇自然”",
    "01",
    "项目理念",
    "建立怎样的教育",
    "02",
    "核心系统",
    "项目做什么、怎么运行",
    "03",
    "落地验证",
    "半年计划与预期成果",
    "04",
    "2026",
    "目 录",
  ],
  3: [
    "01",
    "项目背景",
    "WHY THIS PROJECT MATTERS",
    "孩子不缺好奇，缺少的是回应、方法和持续陪伴。",
  ],
  4: [
    "WHY THIS PROJECT MATTERS",
    "项目背景",
    "好奇回应",
    "问题需要回应。",
    "场景缺少工具",
    "有场域\n缺方法支持",
    "自然读法",
    "把观察转化为探究路径。",
    "项目切入点",
    "自然、好奇和陪伴共同支撑持续探究。",
    "2026",
    "BUPT",
  ],
  5: [
    "EDUCATION MODEL",
    "项目理念",
    "01.",
    "以自然为主场",
    "让学习发生在草木、虫鱼、星斗和四季变化之中。",
    "大自然是永不枯竭的课堂\n学习从孩子真实的问题出发",
    "03.",
    "以教师为赋能者",
    "教师陪伴儿童观察、追问、实验，连接外部资源。",
    "《夏小正》 × 墨子四疑",
    "02.",
    "以好奇为引擎",
    "从孩子的“为什么”出发，而不是从知识点出发。",
    "2026",
    "BUPT",
  ],
  6: [
    "THREE CORE SYSTEMS",
    "项目不是单独做一门课程，而是建设三套彼此配合的系统。",
    "从一次好奇，形成可积累、可展示、可复制的教育生态。",
    "自然探索系统",
    "1120 条观察知识库\n100 个实验主题",
    "好奇心博物馆",
    "沉淀问题、猜想\n回应和反思",
    "教师赋能系统",
    "9 课培训与 AI 支持\n形成教师梯队",
    "三大核心系统",
    "2026",
    "BUPT",
  ],
  7: [
    "GROWTH MECHANISM",
    "好奇心生长机制",
    "儿童经历看见、发问、猜想、观察、发现、分享，并在分享后生成新的问题。",
    "孩子自治",
    "从参与者成长为“小墙主”，把发现讲给同伴。",
    "教师引导",
    "把零散问题变成可验证的探究任务。",
    "外部支持",
    "AI 推荐观察方向与实验路径。",
    "教学与心理支持帮助教师回应现场问题。",
    "2026",
    "BUPT",
  ],
  8: [
    "IMPLEMENTATION",
    "半年实施与预期成果",
    "01",
    "实施路径",
    "6 个试点同步推进，培训 100 名教师，筛选 30 名骨干和 10 名种子教师。",
    "02",
    "成果沉淀",
    "沉淀探究模式、教师课程、AI 原型、儿童案例和评估工具。",
    "6个月验证",
    "准备、启动、实践、深化、进阶、评估，形成可复制的项目模式包。",
    "项目\n成果",
    "2026",
    "BUPT",
  ],
};

await fs.mkdir(path.dirname(outPath), { recursive: true });
const zip = await JSZip.loadAsync(await fs.readFile(templatePath));

for (const [number, texts] of Object.entries(slideTexts)) {
  const file = zip.file(`ppt/slides/slide${number}.xml`);
  const xml = await file.async("string");
  zip.file(`ppt/slides/slide${number}.xml`, replaceTexts(xml, texts));
}

let presentationXml = await zip.file("ppt/presentation.xml").async("string");
const sldIds = [...presentationXml.matchAll(/<p:sldId[^>]*r:id="([^"]+)"[^>]*\/>/g)];
const keepRids = new Set(sldIds.slice(0, 8).map((m) => m[1]));
presentationXml = presentationXml.replace(/<p:sldId[^>]*r:id="([^"]+)"[^>]*\/>/g, (match, rid) => (
  keepRids.has(rid) ? match : ""
));
zip.file("ppt/presentation.xml", presentationXml);

let relsXml = await zip.file("ppt/_rels/presentation.xml.rels").async("string");
relsXml = relsXml.replace(/<Relationship[^>]*Id="([^"]+)"[^>]*Type="[^"]+\/slide"[^>]*\/>/g, (match, rid) => (
  keepRids.has(rid) ? match : ""
));
zip.file("ppt/_rels/presentation.xml.rels", relsXml);

for (let i = 9; i <= 14; i += 1) {
  zip.remove(`ppt/slides/slide${i}.xml`);
  zip.remove(`ppt/slides/_rels/slide${i}.xml.rels`);
}

const buffer = await zip.generateAsync({
  type: "nodebuffer",
  compression: "DEFLATE",
  compressionOptions: { level: 6 },
});
await fs.writeFile(outPath, buffer);
console.log(outPath);
