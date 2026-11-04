import assert from "node:assert/strict";
import test from "node:test";

import { commonGuideSteps, commonHelpItems, userGuideByRole } from "../src/userGuide.ts";

test("user guide provides a practical workflow for every workspace role", () => {
  for (const role of ["teacher", "parent", "study_travel"] as const) {
    const guide = userGuideByRole[role];
    assert.ok(guide.title);
    assert.ok(guide.steps.length >= 3);
    assert.ok(guide.steps.every((step) => step.title && step.description));
  }
});

test("parent guide covers family context and age appropriate safety", () => {
  const text = userGuideByRole.parent.steps.map((step) => `${step.title} ${step.description}`).join(" ");
  assert.match(text, /家庭|孩子/);
  assert.match(text, /安全|年龄/);
});

test("study travel guide explains claiming work and report submission", () => {
  const text = userGuideByRole.study_travel.steps.map((step) => `${step.title} ${step.description}`).join(" ");
  assert.match(text, /领取/);
  assert.match(text, /报告|提交/);
});

test("common help covers expert consultation, draft edits and save actions", () => {
  const text = commonHelpItems.map((item) => `${item.title} ${item.description}`).join(" ");
  assert.match(text, /领域专家/);
  assert.match(text, /草案/);
  assert.match(text, /保存/);
  assert.match(text, /参考资料/);
});

test("guides explain visible save states, recovery, and the study travel project entry", () => {
  const guideText = [...commonGuideSteps, ...commonHelpItems].map((item) => `${item.title} ${item.description}`).join(" ");
  assert.match(guideText, /未保存|保存中|已保存/);
  assert.match(guideText, /重新发送|重试/);
  assert.match(userGuideByRole.study_travel.steps.map((step) => step.description).join(" "), /项目协同/);
});
