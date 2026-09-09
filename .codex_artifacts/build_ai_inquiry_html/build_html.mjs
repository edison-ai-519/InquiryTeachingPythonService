import fs from 'node:fs/promises';
import path from 'node:path';

const root = 'D:/javacode/InquiryTeachingPythonService';
const imagePath = path.join(root, '.codex_artifacts/build_ai_inquiry_ppt_v2/ui/workbench.png');
const outputPath = path.join(root, 'outputs/AI探究式教学助手成果展示_交互预览.html');
const imageData = `data:image/png;base64,${(await fs.readFile(imagePath)).toString('base64')}`;

const html = String.raw`<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>AI 探究式教学助手｜成果展示</title>
  <style>
    :root{--paper:#fbfcf8;--ink:#163a37;--muted:#627571;--green:#13806d;--green2:#19a486;--mint:#dff3e9;--mint2:#eef8f3;--blue:#397e9a;--sky:#e3f2f5;--gold:#a17625;--sand:#f5eedc;--line:#c8ddd4;--white:#fff;--shadow:0 20px 70px rgba(27,67,58,.12)}
    *{box-sizing:border-box}
    html,body{height:100%;margin:0;overflow:hidden;background:#e9efea;color:var(--ink);font-family:"Microsoft YaHei","Noto Sans SC",system-ui,sans-serif}
    body{background:radial-gradient(circle at 18% 15%,rgba(255,255,255,.9),transparent 35%),linear-gradient(135deg,#eef3ef,#dfe9e4)}
    button{font:inherit}
    .viewport{height:100%;display:grid;place-items:center;padding:42px 28px 70px}
    .deck{position:relative;width:1280px;height:720px;transform-origin:center;box-shadow:var(--shadow);background:var(--paper);overflow:hidden}
    .slide{position:absolute;inset:0;padding:54px 68px 48px;background:var(--paper);opacity:0;visibility:hidden;transform:translateX(48px) scale(.985);transition:opacity .38s ease,transform .5s cubic-bezier(.2,.8,.2,1),visibility .38s;overflow:hidden}
    .slide.active{opacity:1;visibility:visible;transform:none;z-index:2}
    .slide.exit-left{transform:translateX(-48px) scale(.985)}
    .slide::before{content:"";position:absolute;inset:0;pointer-events:none;background-image:linear-gradient(rgba(19,128,109,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(19,128,109,.025) 1px,transparent 1px);background-size:40px 40px;mask-image:linear-gradient(to bottom,rgba(0,0,0,.7),transparent 82%)}
    .slide>*{position:relative;z-index:1}
    h1,h2,h3,p{margin:0}
    h2{font-size:45px;line-height:1.18;letter-spacing:-1.4px;max-width:1120px}
    .sub{font-size:21px;color:var(--muted);margin-top:12px;line-height:1.5}
    .kicker{font-size:13px;color:var(--green);font-weight:800;letter-spacing:.12em;text-transform:uppercase}
    .page{position:absolute;right:69px;bottom:37px;font-size:15px;color:#85938f;letter-spacing:.14em}
    .tag{display:inline-flex;align-items:center;gap:8px;padding:8px 13px;border:1px solid var(--line);border-radius:999px;background:rgba(255,255,255,.68);font-size:14px;font-weight:700;color:var(--green)}
    .tag i{display:block;width:7px;height:7px;border-radius:50%;background:var(--green2)}
    .panel{background:rgba(255,255,255,.78);border:1px solid var(--line);border-radius:18px}
    .soft{background:var(--mint2)}
    .blue{background:var(--sky)}
    .gold{background:var(--sand)}
    .line{height:1px;background:var(--line)}
    .muted{color:var(--muted)}
    .accent{color:var(--green)}
    .blue-t{color:var(--blue)}
    .gold-t{color:var(--gold)}
    .big-number{font-size:66px;font-weight:800;line-height:1;color:var(--green)}
    .reveal{opacity:0;transform:translateY(14px);transition:opacity .5s ease,transform .5s ease}
    .active .reveal{opacity:1;transform:none}
    .active .reveal:nth-child(2){transition-delay:.08s}.active .reveal:nth-child(3){transition-delay:.14s}.active .reveal:nth-child(4){transition-delay:.2s}.active .reveal:nth-child(5){transition-delay:.26s}

    /* Cover */
    .cover{display:grid;grid-template-columns:1.04fr .96fr;align-items:center;padding-left:76px}
    .cover h1{font-size:76px;line-height:1.1;letter-spacing:-3px;margin:35px 0 28px}
    .cover .identity{font-size:22px;color:var(--muted);line-height:1.55}
    .cover .claim{font-size:29px;font-weight:800;line-height:1.45;color:var(--green);margin-top:54px}
    .cover-art{height:100%;position:relative}
    .halo{position:absolute;width:400px;height:400px;border-radius:50%;background:var(--mint2);left:66px;top:118px}
    .journey{position:absolute;inset:94px 10px 82px 22px;width:520px;height:520px}
    .teacher-mark{position:absolute;left:60px;bottom:96px;width:116px;height:116px;border:2px solid var(--green);border-radius:50%;background:white;display:grid;place-items:center}
    .teacher-mark::before{content:"";width:28px;height:28px;border-radius:50%;background:var(--green);transform:translateY(-12px)}
    .teacher-mark::after{content:"";position:absolute;width:55px;height:34px;border-radius:14px 14px 8px 8px;background:var(--green);bottom:20px}
    .ai-mark{position:absolute;right:34px;bottom:126px;width:128px;height:88px;background:var(--sky);display:grid;place-items:center;font-size:32px;font-weight:800;color:var(--blue)}

    /* slide 2 */
    .compare{display:grid;grid-template-columns:340px 1fr;gap:44px;margin-top:45px;height:378px}
    .linear{padding:26px 35px;background:#f0f3f0}
    .linear h3,.continuum h3{font-size:27px;margin-bottom:34px}
    .linear-flow{display:grid;gap:13px;text-align:center;color:var(--muted);font-size:20px}
    .linear-flow .down{font-size:25px;color:#97a49f}
    .continuum{padding:26px 32px}
    .loop-grid{display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:1fr 1fr;gap:50px 36px;align-items:center}
    .loop-node{height:76px;border-radius:50%;background:var(--mint);display:grid;place-items:center;font-size:22px;font-weight:800;position:relative}
    .loop-node:not(:nth-child(4))::after{content:"→";position:absolute;right:-31px;color:var(--green);font-size:28px}
    .loop-node:nth-child(5){grid-column:4;grid-row:2}.loop-node:nth-child(6){grid-column:3;grid-row:2}.loop-node:nth-child(7){grid-column:2;grid-row:2}
    .loop-node:nth-child(5)::after,.loop-node:nth-child(6)::after,.loop-node:nth-child(7)::after{content:"←";right:auto;left:-31px}
    .insight{position:absolute;left:68px;right:68px;bottom:72px;font-size:29px;font-weight:800}

    /* slide 3 */
    .logic{margin-top:70px;display:grid;grid-template-columns:repeat(4,1fr);gap:32px;align-items:center}
    .logic-node{height:108px;padding:22px 18px;display:grid;place-items:center;text-align:center;font-size:23px;font-weight:800;position:relative}
    .logic-node:not(:last-child)::after{content:"→";position:absolute;right:-27px;color:var(--green);font-size:30px}
    .feedback{height:74px;margin:29px 126px 0 314px;border-left:2px solid var(--green);border-right:2px solid var(--green);border-bottom:2px solid var(--green);position:relative}
    .feedback::before{content:"↑";position:absolute;left:-10px;top:-16px;font-size:26px;color:var(--green);background:var(--paper)}
    .feedback span{position:absolute;left:50%;bottom:-16px;transform:translateX(-50%);background:var(--paper);padding:0 20px;color:var(--green);font-size:19px;white-space:nowrap}
    .support{margin-top:38px;padding:23px 26px;display:flex;align-items:center;gap:42px;font-size:20px}
    .support strong{font-size:21px;color:var(--green);margin-right:10px}

    /* slide 4 */
    .route{position:relative;margin-top:32px;height:405px}
    .route svg{position:absolute;inset:0;width:100%;height:100%}
    .route-step{position:absolute;width:155px;text-align:center;transform:translate(-50%,-50%)}
    .route-step b{display:grid;place-items:center;width:50px;height:50px;margin:0 auto 11px;border:2px solid var(--green);border-radius:50%;background:white;color:var(--green);font-size:22px}
    .route-step span{display:block;font-size:20px;font-weight:800;line-height:1.28}
    .r1{left:6%;top:66%}.r2{left:22%;top:30%}.r3{left:38%;top:24%}.r4{left:53%;top:54%}.r5{left:68%;top:80%}.r6{left:83%;top:75%}.r7{left:96%;top:46%}
    .stage-rule{display:flex;justify-content:center;gap:17px;align-items:center;padding:17px;background:var(--mint2);color:var(--green);font-size:19px;margin-top:0}
    .stage-rule i{font-style:normal;color:#8ab2a6}

    /* slide 5 */
    .teacher-layout{display:grid;grid-template-columns:720px 1fr;gap:46px;margin-top:12px}
    .teacher-loop{height:445px;position:relative}
    .teacher-loop svg{position:absolute;inset:0;width:100%;height:100%}
    .teacher-core{position:absolute;left:275px;top:150px;width:175px;height:175px;border-radius:50%;background:var(--mint);display:grid;place-items:center;text-align:center}
    .teacher-core strong{font-size:39px;color:var(--green)}.teacher-core span{font-size:18px;color:var(--green)}
    .orbit{position:absolute;width:145px;height:52px;background:white;display:grid;place-items:center;font-size:18px;font-weight:800}
    .o1{left:290px;top:14px}.o2{left:510px;top:114px}.o3{left:510px;top:292px}.o4{left:288px;top:382px}.o5{left:72px;top:292px}.o6{left:72px;top:114px}
    .controls{border-left:1px solid var(--line);padding:34px 0 0 48px}
    .controls h3{font-size:29px;margin-bottom:48px}.controls p{font-size:20px;margin:0 0 28px;padding-left:20px;position:relative}.controls p::before{content:"";position:absolute;left:0;top:10px;width:7px;height:7px;border-radius:50%;background:var(--green2)}

    /* slide 6 */
    .hub{height:430px;position:relative;margin-top:18px}
    .hub svg{position:absolute;inset:0;width:100%;height:100%}
    .hub-core{position:absolute;left:476px;top:128px;width:205px;height:205px;border:2px solid var(--green);border-radius:50%;background:var(--mint);display:grid;place-items:center;text-align:center}
    .hub-core strong{font-size:31px;color:var(--green)}.hub-core span{font-size:17px;color:var(--green)}
    .expert{position:absolute;width:205px;height:62px;border:1px solid var(--line);background:white;display:grid;place-items:center;font-size:19px;font-weight:800}
    .e1{left:214px;top:40px}.e2{right:220px;top:40px}.e3{right:116px;top:244px}.e4{right:337px;bottom:4px}.e5{left:270px;bottom:4px}
    .teacher-entry{position:absolute;left:0;top:175px;display:flex;align-items:center;gap:14px;font-size:21px;color:var(--blue);font-weight:800}
    .teacher-entry i{width:68px;height:68px;border-radius:50%;background:var(--sky);display:grid;place-items:center;font-style:normal}
    .rag{position:absolute;right:0;top:3px;width:202px;padding:17px;text-align:center;background:var(--sky);color:var(--blue);font-weight:800;font-size:19px}
    .hub-foot{text-align:center;font-size:19px;color:var(--muted)}

    /* slide 7 */
    .layers{margin-top:25px;display:grid;gap:10px}
    .layer{height:88px;display:grid;grid-template-columns:230px 1fr;align-items:center;border:1px solid var(--line);padding:0 26px}
    .layer .label{border-right:1px solid var(--line);height:58px;display:flex;flex-direction:column;justify-content:center}.layer .label strong{font-size:21px;color:var(--green)}.layer .label span{font-size:16px;color:var(--muted)}
    .layer .content{padding-left:30px;font-size:20px}.layer:nth-child(2){background:var(--mint2)}.layer:nth-child(3){background:var(--mint)}.layer:nth-child(4){background:var(--sky)}
    .arch-note{font-size:17px;color:var(--muted);margin-top:17px}

    /* slide 8 */
    .product{display:grid;grid-template-columns:850px 1fr;gap:32px;margin-top:21px}
    .screen{height:414px;border:1px solid var(--line);border-radius:16px;background:white;padding:8px;box-shadow:0 10px 35px rgba(31,74,64,.09);overflow:hidden}
    .screen img{width:100%;height:100%;display:block;object-fit:contain;border-radius:10px}
    .callouts{display:grid;gap:0}.callout{padding:13px 0 17px;border-bottom:1px solid var(--line)}.callout:last-child{border:0}.callout-head{display:flex;align-items:center;gap:13px;margin-bottom:10px}.callout-head b{width:44px;height:44px;border-radius:50%;background:var(--mint);display:grid;place-items:center;color:var(--green);font-size:18px}.callout-head strong{font-size:24px}.callout p{font-size:18px;color:var(--muted);line-height:1.5;padding-left:57px}

    /* slide 9 */
    .pipeline{margin-top:28px;display:grid;grid-template-rows:118px 240px 72px;gap:20px}
    .ingest{display:grid;grid-template-columns:100px 1.2fr 45px .88fr 45px 1fr;align-items:center;gap:12px}.retrieve{display:grid;grid-template-columns:100px 190px 34px 170px 1fr 34px 238px;align-items:center;gap:12px}
    .pipe-label{font-size:20px;color:var(--muted);font-weight:800}.box{height:82px;display:grid;place-items:center;text-align:center;background:white;border:1px solid var(--line);font-size:20px;font-weight:800;padding:10px}.arr{text-align:center;color:var(--green);font-size:28px}
    .branches{height:220px;display:grid;grid-template-rows:1fr 1fr;gap:18px;position:relative}.branches::before{content:"";position:absolute;left:-18px;top:50%;width:18px;height:1px;background:var(--green)}.branch{display:grid;place-items:center;background:var(--mint2);font-size:20px;font-weight:800}.branch:last-child{background:var(--sky)}
    .fallback{text-align:center;font-size:17px;color:var(--blue);margin-top:4px}.audit{display:grid;place-items:center;background:var(--mint2);color:var(--green);font-size:19px;font-weight:800}

    /* slide 10 */
    .capabilities{display:grid;grid-template-columns:repeat(3,1fr);gap:34px;margin-top:51px}.cap{border-top:5px solid var(--green);padding-top:20px}.cap.blue-cap{border-color:var(--blue)}.cap.gold-cap{border-color:var(--gold)}.cap .state{font-size:15px;font-weight:800;color:var(--green);margin-bottom:14px}.cap.blue-cap .state{color:var(--blue)}.cap.gold-cap .state{color:var(--gold)}.cap h3{font-size:27px;margin-bottom:25px}.cap ul{list-style:none;padding:0;margin:0;display:grid;gap:18px}.cap li{font-size:19px;padding-left:21px;position:relative}.cap li::before{content:"";position:absolute;left:0;top:11px;width:7px;height:7px;border-radius:50%;background:currentColor}.cap.gold-cap{color:var(--gold)}.cap.gold-cap li span{color:var(--ink)}

    /* slide 11 */
    .quadrants{margin-top:40px;display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--line);border-left:1px solid var(--line)}.quad{min-height:190px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:27px 31px;display:grid;grid-template-columns:95px 1fr;gap:11px}.quad .num{font-size:42px;font-weight:800;color:var(--green)}.quad:nth-child(even) .num{color:var(--blue)}.quad h3{font-size:27px;margin:6px 0 18px}.quad p{font-size:18px;color:var(--muted);line-height:1.5}

    /* slide 12 */
    .roadmap{height:340px;position:relative;margin-top:34px}.road-line{position:absolute;left:40px;right:40px;top:116px;height:6px;background:#cbddd5}.road-line::after{content:"";position:absolute;right:-5px;top:-8px;border-left:18px solid #cbddd5;border-top:11px solid transparent;border-bottom:11px solid transparent}.road-step{position:absolute;width:300px;top:0}.road-step:nth-child(2){left:22px}.road-step:nth-child(3){left:436px}.road-step:nth-child(4){right:0}.road-step .phase{font-size:28px;font-weight:800;color:var(--green)}.road-step:nth-child(3) .phase{color:var(--blue)}.road-step:nth-child(4) .phase{color:var(--gold)}.road-step .pin{width:29px;height:29px;border:5px solid currentColor;border-radius:50%;background:var(--paper);margin:51px 0 28px}.road-step h3{font-size:26px}.road-step p{font-size:18px;color:var(--muted);line-height:1.55;margin-top:17px}.gate{display:grid;grid-template-columns:205px 1fr;align-items:center;background:var(--mint2);padding:17px 23px}.gate strong{font-size:22px;color:var(--green);border-right:1px solid var(--line)}.gate p{font-size:17px;padding-left:27px;line-height:1.55}

    /* ending */
    .ending{display:flex;flex-direction:column;justify-content:center;padding-left:82px}.ending h2{font-size:69px;line-height:1.22;max-width:900px}.ending .brand{margin-top:90px;font-size:20px;color:var(--muted);line-height:1.6}.ending .thanks{margin-top:48px;color:var(--green);font-weight:800;font-size:18px}

    .chrome{position:fixed;inset:0;pointer-events:none;z-index:10}.progress{position:absolute;left:0;top:0;height:4px;background:var(--green);transition:width .35s ease}.nav{position:absolute;left:50%;bottom:17px;transform:translateX(-50%);display:flex;align-items:center;gap:12px;padding:8px 10px;border:1px solid rgba(22,58,55,.1);border-radius:999px;background:rgba(255,255,255,.88);backdrop-filter:blur(10px);box-shadow:0 4px 24px rgba(21,55,48,.1);pointer-events:auto}.nav button{width:36px;height:36px;border:0;border-radius:50%;background:transparent;color:var(--ink);font-size:20px;cursor:pointer}.nav button:hover{background:var(--mint)}.counter{font-size:13px;color:var(--muted);min-width:64px;text-align:center}.dots{display:flex;gap:5px}.dot{width:6px;height:6px;border:0;padding:0;border-radius:50%;background:#c4d2cc;cursor:pointer}.dot.on{width:18px;border-radius:9px;background:var(--green)}.help{position:absolute;right:20px;bottom:22px;font-size:12px;color:#71817c;background:rgba(255,255,255,.65);padding:7px 11px;border-radius:8px;pointer-events:auto}.notes{position:fixed;right:20px;top:20px;width:min(410px,calc(100vw - 40px));padding:18px 20px;border-radius:14px;background:rgba(15,45,41,.94);color:white;z-index:20;box-shadow:var(--shadow);font-size:14px;line-height:1.65;transform:translateY(-130%);transition:transform .3s ease}.notes.open{transform:none}.notes b{display:block;color:#9ee3cf;margin-bottom:8px}
    @media (max-width:720px){.help{display:none}.viewport{padding:14px 8px 63px}.nav{bottom:10px}.slide{padding:54px 68px 48px}}
    @media (prefers-reduced-motion:reduce){.slide,.reveal,.progress,.notes{transition:none!important}}
  </style>
</head>
<body>
  <main class="viewport" aria-label="AI 探究式教学助手演示文稿">
    <div class="deck" id="deck">
      <section class="slide cover active" data-note="核心定位：AI 沿真实探究过程陪教师完成设计，教师保留最终教学判断。">
        <div>
          <div class="kicker reveal">Inquiry learning × AI agent</div>
          <h1 class="reveal">AI 探究式<br>教学助手</h1>
          <div class="identity reveal">InquiryTeachingPythonService<br>项目成果展示</div>
          <div class="claim reveal">让 AI 从“生成教案”走向<br>“陪教师完成探究设计”</div>
        </div>
        <div class="cover-art reveal">
          <div class="halo"></div>
          <svg class="journey" viewBox="0 0 520 520" aria-hidden="true"><path d="M38 456 C74 431 93 399 105 349 S176 260 232 249 S334 238 365 190 S421 101 458 42" fill="none" stroke="#cbe4da" stroke-width="24"/><path d="M38 456 C74 431 93 399 105 349 S176 260 232 249 S334 238 365 190 S421 101 458 42" fill="none" stroke="#13806d" stroke-width="4"/><g fill="#fbfcf8" stroke="#13806d" stroke-width="3"><circle cx="105" cy="349" r="12"/><circle cx="232" cy="249" r="12"/><circle cx="365" cy="190" r="12"/><circle cx="425" cy="91" r="12"/><circle cx="458" cy="42" r="25"/></g></svg>
          <div class="teacher-mark"></div><div class="ai-mark">AI</div>
        </div>
        <span class="page">01</span>
      </section>

      <section class="slide" data-note="左侧是一种概念化的一次生成交互；右侧展示探究教学中的连续决策，不代表竞品实测。">
        <h2 class="reveal">探究教学，需要持续做判断</h2><p class="sub reveal">从“一次拿到文本”到“逐步形成教学方案”</p>
        <div class="compare reveal">
          <div class="linear"><h3>一次生成式交互</h3><div class="linear-flow"><span>输入主题</span><span class="down">↓</span><span>生成完整教案</span><span class="down">↓</span><span>教师事后调整</span></div></div>
          <div class="continuum"><h3 class="accent">探究设计中的连续决策</h3><div class="loop-grid"><div class="loop-node">问题</div><div class="loop-node">猜想</div><div class="loop-node">方案</div><div class="loop-node">实验</div><div class="loop-node">观察</div><div class="loop-node">讨论</div><div class="loop-node">迭代</div></div></div>
        </div>
        <div class="insight reveal">探究式教学不是一次内容生成，而是一段持续决策过程</div><span class="page">02</span>
      </section>

      <section class="slide" data-note="主导师维持阶段主流程；课程知识只供本轮显式选择且获授权的专家检索。">
        <h2 class="reveal">让教学设计在同一个工作台持续推进</h2><p class="sub reveal">教师在环 · 阶段化推进 · 专业能力协同</p>
        <div class="logic reveal"><div class="logic-node panel">教师提出需求</div><div class="logic-node panel soft">主导师<br>阶段化讨论</div><div class="logic-node panel">阶段草案</div><div class="logic-node panel blue">教师审阅</div></div>
        <div class="feedback reveal"><span>追问、修改、继续推进</span></div>
        <div class="support panel soft reveal"><strong>为当前任务提供支撑</strong><span>会话资料</span><span>专家咨询</span><span>获授权课程知识</span><span>→ 导出 Markdown 教学方案</span></div><span class="page">03</span>
      </section>

      <section class="slide" data-note="七个阶段名称来自代码。草案按需生成，推进与回退由教师触发。">
        <h2 class="reveal">一个观察，沿七个阶段长成教学方案</h2><p class="sub reveal">七阶段探究流 · 每段都有目标，推进与回退由教师触发</p>
        <div class="route reveal"><svg viewBox="0 0 1144 405" preserveAspectRatio="none" aria-hidden="true"><path d="M65 265 C220 95 400 75 585 218 S895 358 1098 175" fill="none" stroke="#dff3e9" stroke-width="28"/><path d="M65 265 C220 95 400 75 585 218 S895 358 1098 175" fill="none" stroke="#13806d" stroke-width="4"/></svg>
          <div class="route-step r1"><b>1</b><span>观察起点</span></div><div class="route-step r2"><b>2</b><span>循疑问题</span></div><div class="route-step r3"><b>3</b><span>可能的猜想</span></div><div class="route-step r4"><b>4</b><span>实验设计</span></div><div class="route-step r5"><b>5</b><span>实验中的<br>新问题</span></div><div class="route-step r6"><b>6</b><span>可能的结论</span></div><div class="route-step r7"><b>7</b><span>延伸与<br>新问题</span></div>
        </div>
        <div class="stage-rule reveal"><span>阶段目标</span><i>→</i><span>对话与追问</span><i>→</i><span>按需生成草案</span><i>→</i><span>确认推进 / 回退修改</span></div><span class="page">04</span>
      </section>

      <section class="slide" data-note="教师选择本轮专家、审阅已有草案的修改提案，并决定推进或回退。首次草案可直接写入。">
        <h2 class="reveal">关键教学判断，始终留在教师手中</h2><p class="sub reveal">AI 负责整理、建议与生成，教师决定内容是否适用</p>
        <div class="teacher-layout reveal"><div class="teacher-loop"><svg viewBox="0 0 720 445" aria-hidden="true"><ellipse cx="362" cy="222" rx="245" ry="178" fill="none" stroke="#c8ddd4" stroke-width="4"/><path d="M353 43l17 7-15 10M607 211l8 16-17-1M378 399l-17 7 3-18M117 236l-9-17 18 3" fill="none" stroke="#13806d" stroke-width="4"/></svg><div class="teacher-core"><div><strong>教师</strong><br><span>最终判断</span></div></div><div class="orbit o1">设定目标</div><div class="orbit o2">AI 建议</div><div class="orbit o3">生成草案</div><div class="orbit o4">审阅修改</div><div class="orbit o5">确认推进</div><div class="orbit o6">继续追问</div></div><div class="controls"><h3>三处明确的控制点</h3><p>选择本轮专家</p><p>接受或拒绝草案修改</p><p>推进阶段或回退重做</p></div></div><span class="page">05</span>
      </section>

      <section class="slide" data-note="专家由教师逐轮选择，没有自动并行会诊；回答进入共享历史，供后续主导师继续整合。">
        <h2 class="reveal">主导师管流程，专家回答本轮专业问题</h2><p class="sub reveal">教师按需选择一位专家；下一轮未再次选择时回到主导师</p>
        <div class="hub reveal"><svg viewBox="0 0 1144 430" aria-hidden="true"><g stroke="#c8ddd4" stroke-width="3"><line x1="578" y1="230" x2="315" y2="70"/><line x1="578" y1="230" x2="827" y2="70"/><line x1="578" y1="230" x2="927" y2="275"/><line x1="578" y1="230" x2="705" y2="405"/><line x1="578" y1="230" x2="371" y2="405"/></g></svg><div class="hub-core"><div><strong>Main Tutor</strong><br><span>维护主流程与上下文</span></div></div><div class="expert e1">昆虫专家</div><div class="expert e2">自然生态专家</div><div class="expert e3">物理探究专家</div><div class="expert e4">安全伦理专家</div><div class="expert e5">数学数据专家</div><div class="teacher-entry"><i>教师</i><span>发起咨询 →</span></div><div class="rag">课程知识 / RAG<br><small>按授权供所选专家检索</small></div></div><p class="hub-foot reveal">专家建议进入共享历史，主导师在后续对话中继续整合</p><span class="page">06</span>
      </section>

      <section class="slide" data-note="当前架构使用 Vue 3、FastAPI、SQLite、本地文件与 Chroma。组织服务和任务队列仍属规划。">
        <h2 class="reveal">一套工作台，连接流程、AI 与可保存的成果</h2><p class="sub reveal">当前实现：Vue 3 + FastAPI + SQLite + 本地课程检索</p>
        <div class="layers reveal"><div class="layer"><div class="label"><strong>前端工作台</strong><span>Vue 3</span></div><div class="content">Chat　·　Draft　·　Session　·　File　·　Export</div></div><div class="layer"><div class="label"><strong>服务编排层</strong><span>FastAPI</span></div><div class="content">会话与权限　·　工作流　·　SSE / 中断　·　Agent 路由</div></div><div class="layer"><div class="label"><strong>AI 能力层</strong><span>角色 + 模型</span></div><div class="content">主导师 / 五位专家 → LLM　　　所选专家 → RAG</div></div><div class="layer"><div class="label"><strong>数据与资源</strong><span>本地持久化</span></div><div class="content">SQLite：会话、草案、知识片段、检索记录<br>本地文件：上传资料　　　Chroma：课程向量索引</div></div></div><p class="arch-note reveal">会话级参考资料进入共享上下文；课程 RAG 在专家权限范围内检索</p><span class="page">07</span>
      </section>

      <section class="slide" data-note="真实 Vue 组件由隔离的演示数据驱动，未调用真实账号、数据库或模型。">
        <h2 class="reveal">对话、草案与审阅，汇入同一个工作台</h2><p class="sub reveal">真实项目界面 · 演示数据</p>
        <div class="product reveal"><div class="screen"><img src="${imageData}" alt="真实 Vue 教师工作台截图，使用演示数据"></div><div class="callouts"><div class="callout"><div class="callout-head"><b>01</b><strong>创建与组织</strong></div><p>会话、阶段、参考资料</p></div><div class="callout"><div class="callout-head"><b>02</b><strong>讨论与咨询</strong></div><p>主导师、专家、流式对话</p></div><div class="callout"><div class="callout-head"><b>03</b><strong>审阅与交付</strong></div><p>修改草案、回滚、导出 .md</p></div></div></div><span class="page">08</span>
      </section>

      <section class="slide" data-note="课程文件默认未授权。向量检索成功时按阈值保留候选；向量不可用或异常时查询链路回退 BM25。">
        <h2 class="reveal">课程知识先授权，再进入专业建议</h2><p class="sub reveal">只检索获授权的资料，结合 BM25 与本地向量召回</p>
        <div class="pipeline reveal"><div class="ingest"><span class="pipe-label">入库</span><div class="box">课程资料<br>PDF / DOCX / TXT / MD</div><span class="arr">→</span><div class="box soft">解析与切片</div><span class="arr">→</span><div class="box blue">索引与授权</div></div><div class="retrieve"><span class="pipe-label">检索</span><div class="box soft">本轮所选专家</div><span class="arr">→</span><div class="box soft">权限过滤</div><div class="branches"><div class="branch">BM25</div><div class="branch">本地向量检索</div><div class="fallback">成功时按阈值筛选；异常时回退 BM25</div></div><span class="arr">→</span><div class="box">融合与重排<br>高相关片段</div></div><div class="audit">专家生成建议　　·　　来源与评分留痕　　·　　回到后续教学讨论</div></div><span class="page">09</span>
      </section>

      <section class="slide" data-note="当前能力来自源码与界面核对，不等于学校试点、性能验收或教学成效已经验证。">
        <h2 class="reveal">基础闭环已具备，平台化与规模验证仍待推进</h2><p class="sub reveal">当前覆盖教师设计流程，学校组织与课堂数据仍属规划</p>
        <div class="capabilities reveal"><div class="cap"><div class="state">当前</div><h3>已形成基础闭环</h3><ul><li>登录与会话隔离</li><li>主导师与五位专家</li><li>阶段讨论与草案审阅</li><li>SSE / 中断 / 回滚</li><li>Markdown 导出</li></ul></div><div class="cap blue-cap"><div class="state">当前</div><h3>已具备支撑能力</h3><ul><li>会话资料解析</li><li>课程知识混合检索</li><li>文件级专家授权</li><li>检索来源与评分审计</li><li>课标管理界面</li></ul></div><div class="cap gold-cap"><div class="state">规划中</div><h3><span>进入真实试点</span></h3><ul><li><span>学校、班级与项目管理</span></li><li><span>学生观察记录与时间轴</span></li><li><span>长期档案与课程包</span></li><li><span>并发与稳定性验收</span></li><li><span>教学质量系统评测</span></li></ul></div></div><span class="page">10</span>
      </section>

      <section class="slide" data-note="这里总结的是已实现机制带来的产品使用方式，不宣称已经通过对照研究证明教学增益。">
        <h2 class="reveal">价值落在教学过程，也留在可修改的成果中</h2>
        <div class="quadrants reveal"><div class="quad"><div class="num">01</div><div><h3>持续迭代</h3><p>围绕同一主题反复讨论，让一次生成成为持续设计。</p></div></div><div class="quad"><div class="num">02</div><div><h3>阶段化探究</h3><p>把问题、假设、验证与解释组织为可推进的教学过程。</p></div></div><div class="quad"><div class="num">03</div><div><h3>专业协同</h3><p>主导师保持教学主线，所选专家补充专业视角。</p></div></div><div class="quad"><div class="num">04</div><div><h3>成果沉淀</h3><p>对话、草案与检索记录可留存，教学方案可以修改与导出。</p></div></div></div><span class="page">11</span>
      </section>

      <section class="slide" data-note="20并发、成功率≥95%、普通非模型接口P95低于1秒均为建议验收目标，不是已经取得的测试结果。">
        <h2 class="reveal">下一步，让备课成果进入真实自然探究项目</h2><p class="sub reveal">发展路线 · 以下均为规划，先做标杆场景，再进入多人试点</p>
        <div class="roadmap reveal"><div class="road-line"></div><div class="road-step"><div class="phase">NOW</div><div class="pin"></div><h3>打磨标杆场景</h3><p>昆虫生命周期观察<br>课程包与工作台样例</p></div><div class="road-step blue-t"><div class="phase">NEXT</div><div class="pin"></div><h3>扩展平台管理</h3><p>学校、班级、项目<br>组织权限与知识库扩展</p></div><div class="road-step gold-t"><div class="phase">FUTURE</div><div class="pin"></div><h3>形成课堂数据闭环</h3><p>学生记录、图片与传感器<br>长期档案与区域项目</p></div></div><div class="gate reveal"><strong>试点前验证</strong><p>建议目标：20 并发教师 · 核心流程成功率 ≥95%<br>重点：会话隔离、SSE 中断、权限变更、索引重建与降级</p></div><span class="page">12</span>
      </section>

      <section class="slide ending" data-note="重申：阶段化工作台、教师在环、当前基础闭环与清晰的平台化路线。">
        <div class="kicker reveal">Inquiry starts with a question</div><h2 class="reveal">让每一个好问题，<br>都成为探究的起点。</h2><div class="brand reveal">AI 探究式教学助手<br>InquiryTeachingPythonService</div><div class="thanks reveal">感谢聆听</div><span class="page">13</span>
      </section>
    </div>
  </main>
  <aside class="notes" id="notes"><b>演讲提示</b><span></span></aside>
  <div class="chrome"><div class="progress" id="progress"></div><div class="nav"><button id="prev" aria-label="上一页">←</button><div class="dots" id="dots"></div><span class="counter" id="counter">01 / 13</span><button id="next" aria-label="下一页">→</button><button id="full" aria-label="全屏">⛶</button></div><div class="help">← → 翻页　N 备注　F 全屏</div></div>
  <script>
    const deck=document.getElementById('deck');const slides=[...document.querySelectorAll('.slide')];const dots=document.getElementById('dots');const counter=document.getElementById('counter');const progress=document.getElementById('progress');const notes=document.getElementById('notes');let index=0;
    slides.forEach(function(_,i){const b=document.createElement('button');b.className='dot';b.setAttribute('aria-label','第 '+(i+1)+' 页');b.addEventListener('click',function(){show(i)});dots.appendChild(b)});
    function fit(){const chromeY=112;const scale=Math.min((innerWidth-24)/1280,(innerHeight-chromeY)/720);deck.style.transform='scale('+Math.max(.2,scale)+')'}
    function show(next){next=Math.max(0,Math.min(slides.length-1,next));slides.forEach(function(s,i){s.classList.toggle('active',i===next);s.classList.toggle('exit-left',i<next)});index=next;counter.textContent=String(index+1).padStart(2,'0')+' / '+String(slides.length).padStart(2,'0');progress.style.width=((index+1)/slides.length*100)+'%';[...dots.children].forEach(function(d,i){d.classList.toggle('on',i===index)});notes.querySelector('span').textContent=slides[index].dataset.note||''}
    function go(delta){show(index+delta)}
    document.getElementById('prev').onclick=function(){go(-1)};document.getElementById('next').onclick=function(){go(1)};document.getElementById('full').onclick=function(){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()};
    addEventListener('resize',fit);addEventListener('keydown',function(e){if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();go(1)}else if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();go(-1)}else if(e.key==='Home')show(0);else if(e.key==='End')show(slides.length-1);else if(e.key.toLowerCase()==='n')notes.classList.toggle('open');else if(e.key.toLowerCase()==='f')document.getElementById('full').click()});
    let touchX=0;addEventListener('touchstart',function(e){touchX=e.changedTouches[0].clientX},{passive:true});addEventListener('touchend',function(e){const dx=e.changedTouches[0].clientX-touchX;if(Math.abs(dx)>50)go(dx<0?1:-1)},{passive:true});fit();show(0);
  </script>
</body>
</html>`;

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, html, 'utf8');
console.log(JSON.stringify({ outputPath, bytes: Buffer.byteLength(html), slides: (html.match(/<section class="slide/g) || []).length }, null, 2));
