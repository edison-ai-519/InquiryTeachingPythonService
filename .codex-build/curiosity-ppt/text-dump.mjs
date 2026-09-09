import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const p = await PresentationFile.importPptx(await FileBlob.load("D:\\桌面\\BUPT\\2024-北邮人专属PPT模板\\2024文艺风绿色.pptx"));
const snapshot = await p.inspect({ kind: "slide,textbox", include: "id,slide,text,textPreview,bbox", maxChars: 60000 });
await fs.writeFile("D:\\javacode\\InquiryTeachingPythonService\\.codex-build\\curiosity-ppt\\texts.ndjson", snapshot.ndjson, "utf8");
