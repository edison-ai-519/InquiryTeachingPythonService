import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const pptx = "D:\\javacode\\InquiryTeachingPythonService\\outputs\\好奇自然项目介绍-8页.pptx";
const outDir = "D:\\javacode\\InquiryTeachingPythonService\\.codex-build\\curiosity-ppt";
const presentation = await PresentationFile.importPptx(await FileBlob.load(pptx));
const snapshot = await presentation.inspect({
  kind: "slide,textbox",
  include: "slide,title,textPreview,bbox",
  maxChars: 50000,
});
await fs.writeFile(path.join(outDir, "final-inspect.ndjson"), snapshot.ndjson, "utf8");
const montage = await presentation.export({ format: "png", montage: true, scale: 0.45 });
await fs.writeFile(path.join(outDir, "final-montage.png"), new Uint8Array(await montage.arrayBuffer()));
for (let i = 0; i < presentation.slides.count; i += 1) {
  const png = await presentation.slides.getItem(i).export({ format: "png", scale: 0.8 });
  await fs.writeFile(path.join(outDir, `final-slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
}
console.log(`slides=${presentation.slides.count}`);
