# AI 探究式教学助手成果预览重设计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重做单文件成果展示 HTML，并加入底部可拖动页面时间轴。

**Architecture:** 保持单 HTML 文件结构，以 CSS 变量和语义化 section 组织 10 个全屏 slide；使用原生 JavaScript 统一维护当前页状态、键盘/触摸/拖拽导航和备注面板。

**Tech Stack:** HTML5、CSS3、原生 JavaScript、内联 SVG。

---

### Task 1: 重写展示页面与视觉系统

**Files:**
- Modify: `outputs/AI探究式教学助手成果展示_交互预览.html`

- [ ] 用 10 个 section 重组 Markdown 重点内容，区分当前能力、未来规划与测试目标。
- [ ] 使用自然教育工作台的暖白/墨绿/湖蓝/琥珀色视觉系统，补充流程、数据卡片和路线图组件。
- [ ] 保留全屏、备注、键盘和触摸交互。

### Task 2: 添加底部可拖动时间轴

**Files:**
- Modify: `outputs/AI探究式教学助手成果展示_交互预览.html`

- [ ] 在底部导航中加入 `input[type=range]`，为每个页面提供刻度和标题。
- [ ] 拖拽时实时更新页码、进度和当前页面；点击刻度跳转对应页。
- [ ] 增加移动端和 reduced-motion 样式。

### Task 3: 浏览器级验证

**Files:**
- Verify: `outputs/AI探究式教学助手成果展示_交互预览.html`

- [ ] 用浏览器/无头浏览器打开文件并检查控制台无错误。
- [ ] 验证滑块拖动、键盘右箭头、页面数量与关键文案存在。
