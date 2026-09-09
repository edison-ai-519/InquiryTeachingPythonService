import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

// 只生成成果文稿；不读写应用运行数据。
const root = 'D:/javacode/InquiryTeachingPythonService';
const build = path.join(root, '.codex_artifacts/build_ai_inquiry_ppt_v2');
const runtime = 'C:/Users/14011/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const skill = 'C:/Users/14011/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
process.env.RUNTIME_NODE_MODULES = path.join(runtime, 'node/node_modules');
const { Presentation, PresentationFile, FileBlob } = await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const { finalizePresentation } = await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const C = { paper:'#FAFCF9', white:'#FFFFFF', ink:'#183B3C', teal:'#187D70', mint:'#DFF1E7', pale:'#F0F7F2', cyan:'#E4F2F4', blue:'#367B98', gray:'#5C706E', line:'#C6D9D0', amber:'#967239', sand:'#F4EDDC' };
const FONT = 'Microsoft YaHei';
const p = Presentation.create({slideSize:{width:1280,height:720}});
const manifests = [];
let serial = 0;
function shape(s,g,x,y,w,h,fill='none',stroke='none',sw=0,name='') {
  return s.shapes.add({geometry:g,name:name||`shape-${++serial}`,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:sw,style:'solid'}});
}
function text(s,t,x,y,w,h,size=24,bold=false,color=C.ink,align='left') {
  const a=shape(s,'textbox',x,y,w,h);
  a.text=t;
  a.text.style={typeface:FONT,fontSize:size,bold,color,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};
  return a;
}
function rect(s,x,y,w,h,fill=C.mint,stroke='none',sw=0){return shape(s,'rect',x,y,w,h,fill,stroke,sw);}
function circle(s,x,y,d,fill=C.mint,stroke='none',sw=0){return shape(s,'ellipse',x,y,d,d,fill,stroke,sw);}
function line(s,x1,y1,x2,y2,color=C.line,width=2){
  // 路线由原生自由曲线构成，保持可编辑，并避免负尺寸线框。
  return poly(s,[[x1,y1],[x2,y2]],color,width);
}
function poly(s,pts,color=C.teal,width=3,fill='none',close=false){
  const minx=Math.min(...pts.map(q=>q[0])),miny=Math.min(...pts.map(q=>q[1]));
  const w=Math.max(1,Math.max(...pts.map(q=>q[0]))-minx),h=Math.max(1,Math.max(...pts.map(q=>q[1]))-miny);
  const cmd=pts.map((q,i)=>({[i?'lineTo':'moveTo']:{x:q[0]-minx,y:q[1]-miny}}));
  if(close)cmd.push({close:{}});
  return s.shapes.add({geometry:'custom',name:`path-${++serial}`,position:{left:minx,top:miny,width:w,height:h},fill,line:{fill:color,width,style:'solid'},customPaths:[{width:w,height:h,commands:cmd}]});
}
function arrow(s,x1,y1,x2,y2,color=C.teal,width=2.5){
  line(s,x1,y1,x2,y2,color,width);
  const a=Math.atan2(y2-y1,x2-x1),d=9;
  poly(s,[[x2-d*Math.cos(a-.55),y2-d*Math.sin(a-.55)],[x2,y2],[x2-d*Math.cos(a+.55),y2-d*Math.sin(a+.55)]],color,width);
}
function arc(s,cx,cy,rx,ry,a1,a2,color=C.line,width=3){
  const pts=Array.from({length:65},(_,i)=>{const a=(a1+(a2-a1)*i/64)*Math.PI/180;return[cx+rx*Math.cos(a),cy+ry*Math.sin(a)]});
  poly(s,pts,color,width);return pts;
}
function node(s,t,x,y,w=200,h=66,fill=C.mint,color=C.ink){const a=rect(s,x,y,w,h,fill);text(s,t,x+12,y+8,w-24,h-16,24,true,color,'center');return a;}
function label(s,t,x,y,w=220,color=C.gray){text(s,t,x,y,w,38,24,false,color);}
function base(title,subtitle='',bg=C.paper){
  const s=p.slides.add();s.background.fill=bg;
  const n=p.slides.items.length;
  text(s,title,64,50,1136,66,44,true);
  if(subtitle)text(s,subtitle,66,127,1128,46,24,false,C.gray);
  text(s,String(n).padStart(2,'0'),1160,648,56,35,24,false,C.gray,'right');
  return s;
}
function note(s,seconds,body,sources){
  const n=p.slides.items.length;
  const sourceLines=sources.map(x=>`- ${x}`).join('\n');
  const full=`建议讲述 ${seconds} 秒\n\n${body}\n\n依据\n${sourceLines}`;
  s.speakerNotes.textFrame.setText(full);
  manifests.push({slide:n,seconds,body,sources});
}

// 01：克制的品牌封面，以可编辑路线表达教师、AI与探究的关系。
{
const s=p.slides.add();s.background.fill=C.paper;
rect(s,64,76,52,7,C.teal);
text(s,'AI 探究式\n教学助手',64,174,660,160,60,true);
text(s,'InquiryTeachingPythonService\n项目成果展示',67,369,630,76,24,false,C.gray);
text(s,'让 AI 从“生成教案”走向\n“陪教师完成探究设计”',65,498,695,94,32,true,C.teal);
circle(s,808,167,360,C.pale);
const route=[[770,523],[824,505],[875,461],[883,400],[920,350],[995,329],[1062,276],[1091,206]];
poly(s,route,C.line,22);poly(s,route,C.teal,3);
route.slice(1,-1).forEach((q,i)=>circle(s,q[0]-9,q[1]-9,18,i%2?C.white:C.mint,C.teal,2));
circle(s,807,441,94,C.white,C.teal,2);circle(s,840,459,27,C.teal);shape(s,'roundRect',828,491,52,27,C.teal);
text(s,'教师',800,554,115,40,24,true,C.teal,'center');
rect(s,1030,440,121,82,C.cyan);text(s,'AI',1030,456,121,48,32,true,C.blue,'center');
arrow(s,1027,455,958,423,C.blue,2);
circle(s,1065,180,54,C.mint,C.teal,2);
text(s,'探究',1040,119,106,43,24,true,C.teal,'center');
note(s,25,'这个项目关注教师如何持续完成探究设计。AI参与问题梳理、阶段讨论、专业咨询和草案整理，教师保留教学判断。接下来用产品流程、实现关系和未来路线来说明当前成果。',['用户提供的新版PPT设计要求','README.md','平台未来发展方向与测试规划.md §2—3']);
}

// 02：左右对比，不把概念对比包装成竞品实验。
{
const s=base('探究教学，需要持续做判断','从“一次拿到文本”到“逐步形成教学方案”');
rect(s,64,208,360,347,'#EFF2EF');
text(s,'一次生成式交互',91,225,308,45,32,true,C.gray);
['输入主题','生成完整教案','教师事后调整'].forEach((v,i)=>{text(s,v,105,298+i*83,280,38,24,false,C.gray,'center');if(i<2)arrow(s,245,341+i*83,245,369+i*83,C.gray,2);});
text(s,'探究设计中的连续决策',493,225,700,45,32,true,C.teal);
const xs=[505,665,825,985], ys=[325,458];
['问题','猜想','方案','实验','观察','讨论','迭代'].forEach((v,i)=>{const idx=i<4?i:6-i;const x=xs[idx],y=i<4?ys[0]:ys[1];circle(s,x,y,76,C.mint);text(s,v,x,y+17,76,40,24,true,C.teal,'center');});
arrow(s,588,363,653,363);arrow(s,748,363,813,363);arrow(s,908,363,973,363);
poly(s,[[1082,363],[1125,363],[1125,496],[913,496]],C.teal,2.5);arrow(s,928,496,913,496);
arrow(s,812,496,748,496);arrow(s,652,496,589,496);
text(s,'探究式教学不是一次内容生成，而是一段持续决策过程',68,593,1117,64,32,true);
note(s,40,'这里的左侧是一种概念化的一次生成交互，并非对所有竞品的事实判断。真实教学设计中，教师会不断决定问题是否值得研究、方案是否可行、证据是否支持结论。本项目把这些持续决策放进工作流程。右侧是探究活动的一般动作示意，不等同于代码阶段名称。',['用户提供的核心叙事与第2页要求','平台未来发展方向与测试规划.md §3.1—3.3']);
}

// 03：主线、支撑与反馈各归其位。
{
const s=base('让教学设计在同一个工作台持续推进','教师在环 · 阶段化推进 · 专业能力协同');
const a=node(s,'教师提出需求',65,239,235,84,C.white),b=node(s,'主导师\n阶段化讨论',368,239,241,84,C.mint),c=node(s,'阶段草案',678,239,224,84,C.white),d=node(s,'教师审阅',971,239,242,84,C.cyan);
arrow(s,307,281,357,281);arrow(s,617,281,667,281);arrow(s,910,281,960,281);
line(s,1092,335,1092,429,C.teal,2.5);arrow(s,1092,427,1092,476);
node(s,'导出教学方案',971,478,242,77,C.mint);
poly(s,[[1030,345],[1030,385],[488,385],[488,335]],C.teal,2.5);arrow(s,488,357,488,335);
rect(s,653,364,274,42,C.paper);text(s,'追问、修改、继续推进',644,365,310,39,24,false,C.teal,'center');
rect(s,65,452,836,127,C.pale);
text(s,'为当前任务提供支撑',88,463,430,38,24,true,C.teal);
text(s,'会话资料     专家咨询     获授权课程知识',89,518,785,41,24,false);
arrow(s,488,448,488,403,C.line,2);
text(s,'专家回答进入共享对话历史，供后续主导师继续讨论与整理',67,607,1125,39,24,false,C.gray);
note(s,45,'主导师维持阶段化教学主流程，教师通过讨论完善想法，并在开启草案模式后按需生成或修订草案。会话资料会进入各类教学上下文；课程知识则仅由本轮显式选择且获授权的专家检索。专家回答进入共享历史，后续主导师可以利用这段上下文继续讨论；系统不会在专家回答后自动追加一段主导师总结。教师可修改与保存，并在需要时导出 Markdown 教案。',['app/api/chat.py:373','app/api/chat.py:487','app/services/prompt_service.py','app/api/sessions.py:311','app/services/export_service.py','PROJECT_STRUCTURE.md']);
}

// 04：七阶段路径按实际工作流名称呈现。
{
const s=base('一个观察，沿七个阶段长成教学方案','七阶段探究流 · 每段都有目标，推进与回退由教师触发');
const pts=[];for(let i=0;i<=100;i++){const x=112+1050*i/100;const y=374-104*Math.sin(2*Math.PI*i/100);pts.push([x,y]);}
poly(s,pts,C.mint,25);poly(s,pts,C.teal,3);
const names=['观察起点','循疑问题','可能的猜想','实验设计','实验中的\n新问题','可能的结论','延伸与\n新问题'];
const descriptions=['从现象出发','聚焦可探究问题','说出预测与理由','形成验证方案','追踪证据与变化','用证据表达解释','评价并提出新问题'];
for(let i=0;i<7;i++){const x=112+1050*i/6,y=374-104*Math.sin(2*Math.PI*i/6);circle(s,x-23,y-23,46,C.white,C.teal,2.5);text(s,String(i+1),x-22,y-21,44,41,24,true,C.teal,'center');const top=i<4?y-128:y+45;text(s,names[i],x-92,top,184,73,24,true,C.ink,'center');if(i===0||i===3||i===6){text(s,descriptions[i],x-108,i<4?y+49:y-99,216,42,24,false,C.gray,'center');}}
rect(s,65,586,1148,53,C.pale);text(s,'阶段目标  →  对话与追问  →  按需生成草案  →  确认推进 / 回退修改',84,592,1110,41,24,false,C.teal,'center');
note(s,60,'七个名称直接来自 inquiry_7_stage 配置：观察起点、循疑问题、可能的猜想、实验设计、实验中的新问题、可能的结论、延伸与新问题。可以用昆虫观察作为讲述示例：先观察变化，再提出问题和预测，设计记录方法，处理新发现，形成有证据的解释。平台当前服务于教师设计这些活动，并不意味着学生记录平台已建成。每段有目标，但并非自动产出草案：教师需要开启草案模式后主动生成。下一步与回退是用户触发的工作流操作，不是学习质量自动判定。',['app/workflow/flows.py:132','app/api/sessions.py:268','app/api/sessions.py:386','app/api/chat.py:487','frontend/src/App.vue']);
}

// 05：教师作为环的中心，用动作而非功能清单叙述。
{
const s=base('关键教学判断，始终留在教师手中','AI 负责整理、建议与生成，教师决定内容是否适用');
const cx=451,cy=397;arc(s,cx,cy,216,172,0,359,C.line,3);
circle(s,cx-92,cy-92,184,C.mint);text(s,'教师',cx-78,cy-49,156,52,44,true,C.teal,'center');text(s,'最终判断',cx-77,cy+9,154,42,24,false,C.teal,'center');
const items=[['设定目标',451,221],['AI 建议',648,313],['生成草案',647,479],['审阅修改',451,572],['确认推进',250,479],['继续追问',250,313]];
items.forEach(([t,x,y],i)=>{rect(s,x-80,y-28,160,56,i%2?C.white:C.pale);text(s,t,x-80,y-23,160,46,24,true,i%2?C.gray:C.teal,'center');});
arrow(s,520,231,552,245);arrow(s,665,377,665,411);arrow(s,557,554,524,568);arrow(s,381,568,348,554);arrow(s,238,411,238,377);arrow(s,347,245,381,231);
line(s,789,238,789,585,C.line,2);
text(s,'三处明确的控制点',846,240,341,47,32,true);
text(s,'选择本轮专家\n\n接受或拒绝草案修改\n\n推进阶段或回退重做',846,315,349,214,24,false,C.ink);
note(s,50,'教师在环是具体交互机制。教师选择是否咨询专家；已有草案的选区编辑会生成待审提案，教师可以接受或拒绝；教师主动推进阶段，也可以撤销最近聊天轮次或返回上一阶段。轮次撤销恢复相关草案并删除关联消息与检索记录；返回上阶段则撤销该阶段确认、清空定稿，保留草案与对话，两者不是完整历史版本恢复。首次草案生成可直接写入，并非所有生成都必须经过独立审批。教师仍可手工编辑并保存。这里的环表示教学设计决策，并不等于课堂实施数据已经自动闭环。',['frontend/src/App.vue','app/api/chat.py:539','app/api/sessions.py:386','app/services/draft_proposal_service.py:159','app/services/draft_edit_service.py']);
}

// 06：中心辐射图；专家选择与课程知识连接准确区分。
{
const s=base('主导师管流程，专家回答本轮专业问题','教师按需选择一位专家；下一轮未再次选择时回到主导师');
const cx=647,cy=391;
const spokes=[[425,252],[858,252],[932,425],[780,565],[493,565]];
spokes.forEach(([x,y])=>line(s,cx,cy,x,y,C.line,2.5));
circle(s,cx-104,cy-91,198,C.mint,C.teal,2);text(s,'Main Tutor',cx-95,cy-44,188,43,32,true,C.teal,'center');text(s,'维护主流程与上下文',cx-105,cy+12,211,52,24,false,C.teal,'center');
const items=[['昆虫专家',425,252],['自然生态专家',858,252],['物理探究专家',932,425],['安全伦理专家',780,565],['数学数据专家',493,565]];
items.forEach(([t,x,y])=>{rect(s,x-106,y-29,212,58,C.white,C.line,1.5);text(s,t,x-99,y-23,198,46,24,true,C.ink,'center');});
circle(s,73,336,108,C.cyan);text(s,'教师',73,369,108,44,32,true,C.blue,'center');
arrow(s,199,390,519,390,C.blue,2.5);text(s,'发起咨询 / 继续讨论',202,340,330,43,24,false,C.gray);
rect(s,946,205,260,83,C.cyan);text(s,'课程知识 / RAG',958,221,238,47,24,true,C.blue,'center');
arrow(s,985,297,985,373,C.blue,2);text(s,'按授权供所选专家检索',913,310,297,43,24,false,C.blue,'center');
text(s,'专家建议进入共享历史，主导师在后续对话中继续整合',111,636,1002,40,24,false,C.gray,'center');
note(s,55,'当前协作方式是一个持续主导师加五个独立角色提示词专家，共用模型配置。教师显式传入 expert_id 发起单次咨询；主导师可以建议选择哪位专家，但系统没有自主选择并并行调度多个专家的实现。专家只回答当轮，不改动阶段或替教师批准草案，且回答后不自动追加主导师回复。专家信息进入共享历史，后续主导师沿原流程继续。右侧知识库是专业咨询的资源，不是第六个专家。图中连线表示职责与资源关系，不是同时执行。',['app/agents/config/agents.yaml','app/agents/prompts/main_tutor.md','app/agents/service.py','app/api/chat.py','app/services/prompt_service.py']);
}

// 07：真正的分层架构，明确 SQLite 与文件/向量存储的关系。
{
const s=base('一套工作台，连接流程、AI 与可保存的成果','当前实现：Vue 3 + FastAPI + SQLite + 本地课程检索');
const rows=[
 ['前端工作台','Vue 3','Chat  ·  Draft  ·  Session  ·  File  ·  Export',C.white],
 ['服务编排层','FastAPI','会话与权限  ·  工作流  ·  SSE / 中断  ·  Agent 路由',C.pale],
 ['AI 能力层','角色 + 模型','主导师 / 五位专家  →  LLM       所选专家  →  RAG',C.mint],
 ['数据与资源','本地持久化','SQLite：会话、草案、知识片段、检索记录\n本地文件：上传资料       Chroma：课程向量索引',C.cyan]
];
rows.forEach(([a,b,c,fill],i)=>{const y=205+i*101;rect(s,65,y,1148,88,fill,C.line,1);text(s,a,85,y+12,199,38,24,true,C.teal);text(s,b,85,y+47,199,30,24,false,C.gray);line(s,298,y+14,298,y+72,C.line,1.5);text(s,c,324,y+11,864,67,24,false,C.ink);if(i<3)arrow(s,636,y+89,636,y+100,C.teal,2);});
text(s,'会话级参考资料进入共享上下文；课程 RAG 在专家权限范围内检索',66,627,1119,38,24,false,C.gray);
note(s,55,'架构围绕当前项目展开，没有加入尚不存在的组织服务、任务队列或专用微服务。前端提供对话、草案、会话和资料交互；FastAPI负责鉴权、阶段状态、请求路由与流式事件；主导师和专家使用不同提示词，但共用现有OpenAI兼容模型配置。SQLite保存业务数据、知识片段与审计，上传文件和Chroma向量索引存储在本地。课程库检索与会话资料上下文是两条不同通路。数据库迁移与异步任务队列属于后续演进建议。',['PROJECT_STRUCTURE.md','frontend/package.json','app/main.py','app/db/models.py','app/db/database.py','app/services/curriculum_vector_service.py','app/services/session_file_service.py']);
}

// 08：真实 Vue 组件截图，数据来源写在页内，所有讲解文字可编辑。
{
const s=base('对话、草案与审阅，汇入同一个工作台','真实项目界面 · 演示数据');
const imgPath=path.join(build,'ui/workbench.png');
const bytes=await fs.readFile(imgPath);
rect(s,62,201,856,425,C.white,C.line,1.5);
s.images.add({blob:bytes,contentType:'image/png',alt:'真实 Vue 教师工作台截图；全部会话、草案与用户信息均为隔离演示数据',fit:'contain',position:{left:64,top:203,width:852,height:421}});
const callouts=[['01','创建与组织','会话、阶段、参考资料'],['02','讨论与咨询','主导师、专家、流式对话'],['03','审阅与交付','修改草案、回滚、导出 .md']];
callouts.forEach(([n,h,b],i)=>{const y=215+i*143;circle(s,947,y+2,44,i===1?C.cyan:C.mint);text(s,n,947,y+3,44,40,24,true,C.teal,'center');text(s,h,1008,y,208,43,32,true);text(s,b,951,y+61,263,62,24,false,C.gray);if(i<2)line(s,949,y+126,1212,y+126,C.line,1);});
note(s,55,'这是仓库真实Vue组件在隔离浏览器中的截图，API响应由本次制作的演示数据驱动，未连接真实账号或调用模型。左侧组织会话与阶段，中间进行主导师或专家咨询，右侧编辑草案。用户可上传参考资料，审阅修改提案，撤销聊天轮次或返回上一阶段，最后导出Markdown。截图用于展示已存在的产品界面，不作为后端端到端验证、模型质量或课堂效果证据。',['frontend/src/App.vue','frontend/src/api.ts','frontend/src/types.ts','.codex_artifacts/build_ai_inquiry_ppt_v2/ui/workbench.png','.codex_artifacts/build_ai_inquiry_ppt_v2/ui/capture_ui.py']);
}

// 09：区分入库与检索，展示分支召回和条件降级。
{
const s=base('课程知识先授权，再进入专业建议','只检索获授权的资料，结合 BM25 与本地向量召回');
text(s,'入库',66,208,84,43,24,true,C.gray);
node(s,'课程资料\nPDF / DOCX / TXT / MD',170,194,357,78,C.white);
arrow(s,536,233,580,233);node(s,'解析与切片',591,194,255,78,C.pale);arrow(s,855,233,902,233);node(s,'索引与授权',913,194,300,78,C.cyan);
text(s,'检索',66,359,84,43,24,true,C.gray);
node(s,'本轮所选专家',166,351,210,76,C.mint);arrow(s,384,389,414,389);node(s,'权限过滤',426,351,177,76,C.mint);
poly(s,[[604,389],[635,389],[635,322],[664,322]],C.teal,2.5);arrow(s,646,322,664,322);
poly(s,[[635,389],[635,451],[664,451]],C.blue,2.5);arrow(s,646,451,664,451,C.blue);
node(s,'BM25',673,291,209,62,C.pale);node(s,'本地向量检索',673,420,209,62,C.cyan);
poly(s,[[890,322],[914,322],[914,389],[945,389]],C.teal,2.5);poly(s,[[890,451],[914,451],[914,389]],C.blue,2.5);arrow(s,926,389,945,389);
node(s,'融合与重排\n高相关片段',956,351,257,76,C.white);
text(s,'向量成功时按阈值筛选；失败时回退 BM25',532,498,679,45,24,false,C.blue,'center');
rect(s,66,564,1147,63,C.pale);text(s,'专家生成建议     ·     来源与评分留痕     ·     回到后续教学讨论',85,574,1110,44,24,true,C.teal,'center');
note(s,65,'入库支持文本型PDF、DOCX、TXT和MD，解析并切片，新上传课程文件默认未授权。管理员配置哪些专家可查某份文件。检索先取得本轮所选专家的获权source，在BM25评分前和Chroma查询中分别过滤。向量查询成功时，只有达到相似度阈值的向量候选进入融合，BM25参与评分；这不是两路候选无条件合并，阈值后无候选会返回空结果，不转用BM25补齐。向量不可用或查询异常时，查询链路回退BM25。CURRICULUM_VECTOR_REQUIRED目前在入库向量化失败时决定是否报错，查询降级分支未据此阻止回退。融合后可选规则重排，选取Top K并合并相邻片段注入专家提示词。默认使用本地BGE模型与Chroma，需要部署模型和索引。主导师与草案不直接检索课程库。审计保留专家、授权来源、命中来源和各路分数，不代表答案质量已获证明。扫描PDF尚不支持OCR。',['app/services/curriculum_knowledge_service.py:195','app/services/curriculum_knowledge_service.py:320','app/services/curriculum_knowledge_service.py:379','app/services/curriculum_knowledge_service.py:419','app/services/curriculum_vector_service.py:267','app/services/curriculum_permission_service.py:46','app/services/rag_service.py:133','app/api/chat.py:373','app/core/config.py:49','README.md 本地课标混合RAG']);
}

// 10：能力状态图使用平行列，状态与验收分开。
{
const s=base('基础闭环已具备，平台化与规模验证仍待推进','当前覆盖教师设计流程，学校组织与课堂数据仍属规划');
const cols=[
 {x:65,w:365,h:'已形成基础闭环',tag:'当前',color:C.teal,fill:C.mint,lines:['登录与会话隔离','主导师与五位专家','阶段讨论与草案审阅','SSE / 中断 / 回滚','Markdown 导出']},
 {x:454,w:365,h:'已具备支撑能力',tag:'当前',color:C.blue,fill:C.cyan,lines:['会话资料解析','课程知识混合检索','文件级专家授权','检索来源与评分审计','课标管理界面']},
 {x:844,w:369,h:'进入真实试点',tag:'规划中',color:C.amber,fill:C.sand,lines:['学校、班级与项目管理','学生观察记录与时间轴','长期档案与课程包','并发与稳定性验收','教学质量系统评测']}
];
cols.forEach(o=>{rect(s,o.x,213,o.w,5,o.color);text(s,o.tag,o.x,233,o.w,35,24,true,o.color);text(s,o.h,o.x,278,o.w,47,32,true,C.ink);o.lines.forEach((a,i)=>{circle(s,o.x+2,356+i*48,7,o.color);text(s,a,o.x+22,337+i*48,o.w-25,44,24,false);});});
note(s,40,'这一页主动给出项目边界。已经形成的是教师工作流的基础闭环；文件管理、课程库授权、混合检索、审计等有实现。系统已有管理员入口和课程知识管理界面，因此不能把所有管理能力都写成未来才有。仍需建设的是学校班级组织、课堂观察记录、长期档案与平台管理，并完成真实试点的性能与质量验证。本次没有运行应用完整测试套件或真实模型，不能声称全部测试通过或达到20并发指标。',['app/api/auth.py','app/api/chat.py','app/api/sessions.py','app/api/curriculum.py','frontend/src/App.vue','平台未来发展方向与测试规划.md §11—14']);
}

// 11：四象限是价值总结，避免再次堆叠功能。
{
const s=base('价值落在教学过程，也留在可修改的成果中');
line(s,639,191,639,603,C.line,2);line(s,67,396,1212,396,C.line,2);
const q=[['01','持续迭代','围绕同一主题反复讨论，\n让一次生成成为持续设计。',78,202],['02','阶段化探究','把问题、假设、验证与解释\n组织为可推进的教学过程。',680,202],['03','专业协同','主导师保持教学主线，\n所选专家补充专业视角。',78,423],['04','成果沉淀','对话、草案与检索记录可留存，\n教学方案可以修改与导出。',680,423]];
q.forEach(([n,h,b,x,y],i)=>{text(s,n,x,y,76,50,44,true,i%2?C.blue:C.teal);text(s,h,x+91,y,421,50,32,true);text(s,b,x+91,y+77,436,95,24,false,C.gray);});
note(s,35,'总结四个产品特点：持续迭代、阶段化探究、专业协同、成果沉淀。这里讲的是已实现机制带来的使用方式，不能把它扩张为经过对照实验验证的教学增益。过程留存也主要指会话、草案、检索日志等现有数据，并不意味着已经具备完整版本历史或学生成长档案。',['README.md','PROJECT_STRUCTURE.md','app/db/models.py','平台未来发展方向与测试规划.md §3—4']);
}

// 12：真正的时间方向与试点门槛；数字全部标为建议目标。
{
const s=base('下一步，让备课成果进入真实自然探究项目','发展路线 · 以下均为规划，先做标杆场景，再进入多人试点');
arrow(s,95,304,1181,304,C.line,7);
const steps=[{x:113,y:304,tag:'NOW',h:'打磨标杆场景',body:'昆虫生命周期观察\n课程包与工作台样例',color:C.teal},{x:535,y:304,tag:'NEXT',h:'扩展平台管理',body:'学校、班级、项目\n组织权限与知识库扩展',color:C.blue},{x:964,y:304,tag:'FUTURE',h:'形成课堂数据闭环',body:'学生记录、图片与传感器\n长期档案与区域项目',color:C.amber}];
steps.forEach(o=>{circle(s,o.x-14,o.y-14,28,C.paper,o.color,4);text(s,o.tag,o.x-15,212,290,43,32,true,o.color);text(s,o.h,o.x-16,343,296,45,32,true);text(s,o.body,o.x-16,403,306,87,24,false,C.gray);});
rect(s,65,548,1148,85,C.pale);text(s,'试点前验证',84,562,192,48,24,true,C.teal);line(s,279,563,279,616,C.line,2);
text(s,'建议目标：20 并发教师 · 核心流程成功率 ≥95%\n重点：会话隔离、SSE 中断、权限变更、索引重建与降级',301,553,884,73,24,false);
note(s,60,'路线图的NOW指近期建设重点，不是已经完成的标杆项目。先打磨昆虫生命周期长期观察课程包与演示工作台，然后建设学校班级项目、组织权限与知识后台，最后将学生观察、图片、传感器和长期档案连接起来。多人试点应先通过并发与稳定性验证。文档建议20名并发教师、核心流程成功率至少95%、普通非模型接口P95低于1秒，这些都是建议验收目标，并非测试结果。重点还包括跨用户隔离、SSE中断后数据一致性、课程授权变更生效、索引重建和可选BM25降级，以及2/8/24小时稳定性测试。测试工具选择和数据库迁移属于实施规划，本页不将其当成果。',['平台未来发展方向与测试规划.md §5、§11.8、§12—14']);
}

// 13：极简结束页。
{
const s=p.slides.add();s.background.fill=C.paper;
rect(s,65,166,65,6,C.teal);
text(s,'让每一个好问题，\n都成为探究的起点。',65,224,1129,163,60,true,C.ink);
text(s,'AI 探究式教学助手\nInquiryTeachingPythonService',68,458,864,87,24,false,C.gray);
text(s,'感谢聆听',70,586,401,44,24,true,C.teal);
note(s,15,'结束时重申三点：这是阶段化教学设计工作台；教师始终在环，主导师与专业角色协同；当前对话、知识支撑、草案审阅与导出已经有基础实现，平台化与真实课堂数据闭环仍有清晰建设任务。',['用户提供的结束页文案']);
}

await fs.mkdir(path.join(build,'preview'),{recursive:true});
await fs.writeFile(path.join(build,'speaker_notes.json'),JSON.stringify(manifests,null,2),'utf8');
const candidate=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
console.log(`Draft exported: ${candidate}`);
const revision=process.env.DECK_REVISION || 'v2';
const finalPath=path.join(root,'outputs',`AI探究式教学助手成果展示_${revision}.pptx`);
await fs.mkdir(path.dirname(finalPath), { recursive: true });
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,pythonExecutable:path.join(runtime,'python/python.exe'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:13,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'user_request',families:[FONT],scriptFonts:{ea:FONT}},verifyArtifactToolImport:true,receiptPath:path.join(build,`${revision}.validation.json`)});
console.log(`Finalized: ${finalPath}`);
// 渲染最终文件重新导入后的全部页面，核验交付文件本身。
const rendered=await PresentationFile.importPptx(await FileBlob.load(finalPath));
for(let i=0;i<rendered.slides.items.length;i++){
 const slide=rendered.slides.items[i];
 const png=await rendered.export({slide,format:'png',scale:1.5});
 await fs.writeFile(path.join(build,'preview',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 const layout=await slide.export({format:'layout'});
 await fs.writeFile(path.join(build,'preview',`slide-${String(i+1).padStart(2,'0')}.json`),await layout.text());
 console.log(`Rendered ${i+1}/13`);
}
console.log(JSON.stringify({finalPath,slideCount:p.slides.items.length,speakingSeconds:manifests.reduce((a,v)=>a+v.seconds,0)},null,2));
