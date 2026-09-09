import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const p = await PresentationFile.importPptx(await FileBlob.load("D:\\桌面\\BUPT\\2024-北邮人专属PPT模板\\2024文艺风绿色.pptx"));
console.log("presentation keys", Object.getOwnPropertyNames(Object.getPrototypeOf(p)));
console.log("slides keys", Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides)));
console.log("slides own", Object.keys(p.slides));
console.log("slides count?", p.slides.length, p.slides.count, p.slides.size);
const s = p.slides.getItem ? p.slides.getItem(0) : null;
console.log("slide keys", s && Object.getOwnPropertyNames(Object.getPrototypeOf(s)));
