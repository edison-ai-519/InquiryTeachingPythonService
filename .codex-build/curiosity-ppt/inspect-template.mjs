import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const templatePath = "D:\\桌面\\BUPT\\2024-北邮人专属PPT模板\\2024文艺风绿色.pptx";
const outDir = "D:\\javacode\\InquiryTeachingPythonService\\.codex-build\\curiosity-ppt";

await fs.mkdir(outDir, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(templatePath));
const snapshot = await presentation.inspect({
  kind: "deck,slide,textbox,shape,image,layout",
  include: "id,slide,name,title,textPreview,textChars,textLines,bbox,isPlaceholder",
  maxChars: 30000,
});
await fs.writeFile(path.join(outDir, "template-inspect.ndjson"), snapshot.ndjson, "utf8");

const montage = await presentation.export({ format: "png", montage: true, scale: 0.4 });
await fs.writeFile(path.join(outDir, "template-montage.png"), new Uint8Array(await montage.arrayBuffer()));

for (let i = 0; i < Math.min(12, presentation.slides.length); i += 1) {
  const slide = presentation.slides.getItem(i);
  const png = await slide.export({ format: "png", scale: 0.6 });
  await fs.writeFile(path.join(outDir, `template-slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
}

console.log(`slides=${presentation.slides.length}`);
