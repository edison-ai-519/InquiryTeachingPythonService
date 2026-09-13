import path from 'node:path';
import { pathToFileURL } from 'node:url';

const runtime = 'C:/Users/14011/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const { FileBlob, PresentationFile } = await import(
  pathToFileURL(path.join(runtime, 'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href,
);
const input = 'D:/javacode/InquiryTeachingPythonService/outputs/AI探究式教学助手成果展示_v2.pptx';
const deck = await PresentationFile.importPptx(await FileBlob.load(input));
if (deck.slides.items.length !== 13) throw new Error(`期望13页，实际${deck.slides.items.length}页`);
const snapshot = await deck.inspect({ kind: 'slide,textbox,shape,image,notes', maxChars: 200000 });
const rows = snapshot.ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
const notes = rows.filter((row) => row.kind === 'notes');
const images = rows.filter((row) => row.kind === 'image');
const textRows = rows.filter((row) => row.kind === 'textbox' || (row.kind === 'shape' && row.text));
const allText = rows.filter((row) => row.kind !== 'notes').map((row) => row.text ?? '').join('\n');
const required = [
  'AI 探究式教学助手',
  '探究教学，需要持续做判断',
  '一个观察，沿七个阶段长成教学方案',
  '主导师管流程，专家回答本轮专业问题',
  '课程知识先授权，再进入专业建议',
  '基础闭环已具备，平台化与规模验证仍待推进',
  '让每一个好问题',
];
for (const phrase of required) if (!allText.includes(phrase)) throw new Error(`缺少关键文案：${phrase}`);
for (const phrase of ['AI FOR INQUIRY TEACHING', '技术赋能教育', '自动调度五位专家']) {
  if (allText.includes(phrase)) throw new Error(`存在禁用/不准确文案：${phrase}`);
}
if (notes.length !== 13) throw new Error(`演讲备注期望13条，实际${notes.length}条`);
if (images.length !== 1) throw new Error(`期望仅真实界面截图1张，实际${images.length}张`);
if (textRows.length < 100) throw new Error(`可编辑文本对象数量异常：${textRows.length}`);
console.log(JSON.stringify({
  file: input,
  slideCount: deck.slides.items.length,
  speakerNotes: notes.length,
  imageCount: images.length,
  editableTextObjects: textRows.length,
  requiredCopyChecks: required.length,
  forbiddenCopyChecks: 3,
}, null, 2));
process.exit(0);
