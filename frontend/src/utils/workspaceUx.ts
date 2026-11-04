import type { UserRole } from "../types.ts";
import type { StageOutput } from "../types.ts";

export const workspaceWelcomeCopy: Record<UserRole, { title: string; description: string; nextStep: string; example: string }> = {
  teacher: {
    title: "从一个教学问题开始",
    description: "主导师会结合当前阶段，陪您逐步形成探究式教学方案。",
    nextStep: "告诉主导师学生年级、学习目标、课时和已有材料。",
    example: "三年级学生要学习光的传播，计划用一课时探究，教室有手电筒和白纸。",
  },
  parent: {
    title: "从孩子感兴趣的现象开始",
    description: "主导师会结合孩子年龄和家庭条件，陪您设计安全、适龄的亲子探究活动。",
    nextStep: "描述孩子的观察、年龄、可用时间和家里现有材料。",
    example: "孩子八岁，在阳台看到雨后叶片上的水珠，我们有放大镜，可以一起观察半小时。",
  },
  study_travel: {
    title: "从基地场景和活动目标开始",
    description: "先整理项目场景、物料和目标，再为教师或家长工作台发布任务。",
    nextStep: "说明活动地点、参与对象、研学目标和可用物料。",
    example: "基地有古道和林地，计划开展半天自然观察，物料有放大镜和记录板，请帮我拆分成教师可执行的观察任务。",
  },
};

export type DraftSaveStateInput = {
  hasSession: boolean;
  dirty: boolean;
  saving: boolean;
  error: string;
};

export function getDraftSaveState(input: DraftSaveStateInput & { hasContent: boolean }) {
  if (!input.hasSession) return { label: "尚未创建草案", hint: "创建或打开草案后即可编辑阶段内容。", tone: "muted" as const };
  if (input.saving) return { label: "保存中", hint: "正在将当前阶段内容保存到服务器。", tone: "pending" as const };
  if (input.error) return { label: "保存失败", hint: `${input.error}。内容仍保留在编辑区，请重试保存。`, tone: "error" as const };
  if (input.dirty) return { label: "未保存", hint: "当前编辑尚未保存；进入下一阶段时会一并提交为本阶段定稿。", tone: "unsaved" as const };
  if (!input.hasContent) return { label: "暂无内容", hint: "此阶段还没有方案内容；在对话区描述目标后，主导师会提供建议。", tone: "muted" as const };
  return { label: "已保存", hint: "当前阶段内容已保存到服务器。", tone: "saved" as const };
}

export function getSessionProgressLabel(status: string, currentStageIndex: number, stageCount: number) {
  if (status === "completed") return "已完成";
  if (stageCount <= 0) return "待开始";
  return `阶段 ${Math.max(0, currentStageIndex) + 1} / ${stageCount}`;
}

export function updateStageDraftOutput(outputs: StageOutput[], stageId: string, content: string): StageOutput[] {
  const index = outputs.findIndex((output) => output.stage_id === stageId);
  if (index < 0) {
    return [...outputs, {
      stage_id: stageId,
      stage_name: stageId,
      order_index: outputs.length,
      draft_content: content,
      final_content: "",
      confirmed: false,
    }];
  }
  return outputs.map((output, outputIndex) => outputIndex === index
    ? { ...output, draft_content: content }
    : output);
}

export function resolveStageSelectionAfterRefresh(
  preferredStageId: string | undefined,
  availableStageIds: string[],
  activeStageId: string,
) {
  return preferredStageId && availableStageIds.includes(preferredStageId)
    ? preferredStageId
    : activeStageId;
}

export async function saveDraftBeforeAction(
  dirty: boolean,
  save: () => Promise<boolean>,
) {
  return !dirty || await save();
}

export function getStageAdvanceFailureNotice(error: string, actionCommitted: boolean) {
  if (actionCommitted) {
    return `本阶段已经提交，但刷新状态失败：${error}。请先重试刷新状态，不要重复提交。`;
  }
  return `阶段推进失败：${error}。当前内容仍保留，可以重试推进。`;
}

export function getSendDisabledReason(input: {
  hasSession: boolean;
  streaming: boolean;
  saving: boolean;
  committedPendingRefresh?: boolean;
  hasRequestId: boolean;
  draftMode: boolean;
  hasDraft: boolean;
  hasSelection: boolean;
  expertSelected: boolean;
}) {
  if (!input.hasSession) return "请先创建草案或领取一个任务。";
  if (input.committedPendingRefresh) return "阶段已提交，请先刷新工作区状态后再继续。";
  if (input.saving) return "正在保存阶段内容，请稍候。";
  if (input.streaming && !input.hasRequestId) return "当前操作正在处理，请稍候。";
  if (!input.expertSelected && input.draftMode && input.hasDraft && !input.hasSelection) {
    return "修订已有草案前，请先在右侧选中要修改的段落。";
  }
  return "";
}

export function getAdvanceDisabledReason(input: {
  hasSession: boolean;
  completed: boolean;
  streaming: boolean;
  selectedCurrent: boolean;
  saving?: boolean;
  committedPendingRefresh?: boolean;
}) {
  if (!input.hasSession) return "请先创建草案或领取一个任务。";
  if (input.completed) return "当前流程已经完成。";
  if (input.committedPendingRefresh) return "本阶段已提交，请先刷新状态后再继续。";
  if (input.saving) return "正在保存阶段内容，请稍候。";
  if (input.streaming) return "导师生成完成后才能推进阶段。";
  if (!input.selectedCurrent) return "请先切回当前阶段，再定稿推进。";
  return "";
}
