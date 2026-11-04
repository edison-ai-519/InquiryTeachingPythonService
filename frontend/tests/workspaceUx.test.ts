import assert from "node:assert/strict";
import test from "node:test";

import { getDraftSaveState, getSendDisabledReason, getAdvanceDisabledReason, getSessionProgressLabel, getStageAdvanceFailureNotice, resolveStageSelectionAfterRefresh, saveDraftBeforeAction, updateStageDraftOutput, workspaceWelcomeCopy } from "../src/utils/workspaceUx.ts";

test("workspace welcome copy gives each role a practical first action", () => {
  assert.match(workspaceWelcomeCopy.teacher.nextStep, /年级|目标|课时/);
  assert.match(workspaceWelcomeCopy.parent.nextStep, /孩子|观察|材料/);
  assert.match(workspaceWelcomeCopy.study_travel.nextStep, /任务|场景|物料/);
});

test("draft save state distinguishes unsaved, saving, saved, and failed states", () => {
  assert.equal(getDraftSaveState({ hasSession: true, hasContent: true, dirty: true, saving: false, error: "" }).label, "未保存");
  assert.equal(getDraftSaveState({ hasSession: true, hasContent: true, dirty: true, saving: true, error: "" }).label, "保存中");
  assert.equal(getDraftSaveState({ hasSession: true, hasContent: false, dirty: false, saving: false, error: "" }).label, "暂无内容");
  assert.equal(getDraftSaveState({ hasSession: true, hasContent: true, dirty: false, saving: false, error: "" }).label, "已保存");
  assert.equal(getDraftSaveState({ hasSession: true, hasContent: true, dirty: true, saving: false, error: "网络断开" }).label, "保存失败");
  assert.match(getDraftSaveState({ hasSession: true, hasContent: true, dirty: true, saving: false, error: "网络断开" }).hint, /重试/);
});

test("session progress label distinguishes completed and active sessions", () => {
  assert.equal(getSessionProgressLabel("completed", 3, 5), "已完成");
  assert.equal(getSessionProgressLabel("active", 1, 5), "阶段 2 / 5");
});

test("disabled chat and stage actions explain how to continue", () => {
  assert.match(getSendDisabledReason({ hasSession: false, saving: false, streaming: false, hasRequestId: false, draftMode: false, hasDraft: false, hasSelection: false, expertSelected: false }), /创建草案|领取/);
  assert.match(getSendDisabledReason({ hasSession: true, saving: false, streaming: false, hasRequestId: false, draftMode: true, hasDraft: true, hasSelection: false, expertSelected: false }), /选中/);
  assert.match(getSendDisabledReason({ hasSession: true, saving: true, streaming: false, hasRequestId: false, draftMode: false, hasDraft: false, hasSelection: false, expertSelected: false }), /保存阶段/);
  assert.match(getSendDisabledReason({ hasSession: true, saving: false, streaming: true, hasRequestId: false, draftMode: false, hasDraft: false, hasSelection: false, expertSelected: false }), /操作正在处理/);
  assert.match(getSendDisabledReason({ hasSession: true, saving: false, committedPendingRefresh: true, streaming: false, hasRequestId: false, draftMode: false, hasDraft: false, hasSelection: false, expertSelected: false }), /阶段已提交.*刷新/);
  assert.match(getAdvanceDisabledReason({ hasSession: true, completed: false, streaming: false, selectedCurrent: false }), /当前阶段/);
  assert.equal(getAdvanceDisabledReason({ hasSession: true, completed: false, streaming: false, selectedCurrent: true }), "");
  assert.match(getAdvanceDisabledReason({ hasSession: true, completed: false, streaming: false, selectedCurrent: true, committedPendingRefresh: true }), /阶段已提交.*刷新/);
});

test("stage advancement distinguishes a failed action from a committed action with a failed refresh", () => {
  assert.match(getStageAdvanceFailureNotice("timeout", false), /推进失败.*重试/);
  assert.match(getStageAdvanceFailureNotice("timeout", true), /已经提交.*刷新.*不要重复提交/);
});

test("saved draft output stays current when the session refresh cannot complete", () => {
  const outputs = [{ stage_id: "stage-1", stage_name: "观察", order_index: 0, draft_content: "旧内容", final_content: "", confirmed: false }];
  const updated = updateStageDraftOutput(outputs, "stage-1", "已保存的新内容");
  assert.equal(updated[0].draft_content, "已保存的新内容");
  assert.equal(outputs[0].draft_content, "旧内容");
});

test("session refresh keeps the viewed stage when it still exists and otherwise selects the active stage", () => {
  const stageIds = ["stage-1", "stage-2", "stage-3"];
  assert.equal(resolveStageSelectionAfterRefresh("stage-2", stageIds, "stage-1"), "stage-2");
  assert.equal(resolveStageSelectionAfterRefresh("deleted-stage", stageIds, "stage-3"), "stage-3");
  assert.equal(resolveStageSelectionAfterRefresh(undefined, stageIds, "stage-3"), "stage-3");
});

test("workspace actions wait for dirty draft saves and stop when saving fails", async () => {
  let saveCalls = 0;
  assert.equal(await saveDraftBeforeAction(false, async () => { saveCalls += 1; return true; }), true);
  assert.equal(saveCalls, 0);
  assert.equal(await saveDraftBeforeAction(true, async () => { saveCalls += 1; return true; }), true);
  assert.equal(saveCalls, 1);
  assert.equal(await saveDraftBeforeAction(true, async () => { saveCalls += 1; return false; }), false);
  assert.equal(saveCalls, 2);
});
