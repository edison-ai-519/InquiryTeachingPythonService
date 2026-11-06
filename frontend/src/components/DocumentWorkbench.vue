<template>
  <aside class="document-workbench" :class="{ drafting }">
    <header class="document-header">
      <div><p class="section-kicker">{{ labels.planLabel }}</p><h2>{{ labels.planLabel }}</h2><span>{{ session ? `${session.topic} · ${stage?.name || '未选择阶段'}` : labels.selectPrompt }}</span></div>
      <div v-if="session" class="document-actions">
        <button class="icon-text-button" type="button" title="上一阶段" :disabled="stageIndex === 0 || streaming" @click="$emit('previous')"><ChevronLeft :size="16" /><span>上一阶段</span></button>
        <button class="icon-text-button" type="button" :title="saveState.hint" :disabled="!selectedStageId || saving" @click="$emit('save')"><LoaderCircle v-if="saving" class="spin-icon" :size="16" /><Save v-else :size="16" /><span>{{ saving ? '保存中' : '保存' }}</span></button>
        <button class="icon-text-button" type="button" :title="labels.exportTitle" :disabled="saving" @click="$emit('export')"><Download :size="16" /><span>导出</span></button>
        <button class="advance-button" type="button" :title="advanceDisabledReason || advanceHelp" :disabled="Boolean(advanceDisabledReason)" @click="$emit('next')">{{ advanceLabel }}<ChevronRight :size="16" /></button>
        <small class="advance-action-hint">{{ advanceDisabledReason || advanceHelp }}</small>
      </div>
    </header>
    <div v-if="session && selectedStageId" class="paper-workspace">
      <div class="paper-toolbar"><div><strong>编辑模式</strong><small>{{ proposal ? proposalLabel : '编辑后请保存；开启草案模式可生成初稿或修订选中内容。' }}</small><span class="draft-save-state" :class="`tone-${saveState.tone}`" role="status" :aria-label="`${saveState.label}。${saveState.hint}`"><strong>{{ saveState.label }}</strong><small>{{ saveState.hint }}</small><button v-if="saveState.tone === 'error'" type="button" @click="$emit('save')">重试保存</button></span></div><button type="button" @click="$emit('preview')"><Eye :size="16" />预览与审阅</button></div>
      <DraftEditor
        v-model="content"
        :visual-lines="visualLines"
        :scroll-top="scrollTop"
        :line-height="lineHeight"
        :cursor-line="cursorLine"
        :selection-label="selectionLabel"
        :attached-label="attachedLabel"
        :disabled="saving"
        :role-category="roleCategory"
        @editor-ready="$emit('editor-ready', $event)"
        @input="$emit('editor-input')"
        @scroll="$emit('editor-scroll')"
        @capture-selection="$emit('capture-selection')"
        @add-selection="$emit('add-selection')"
        @clear-selection="$emit('clear-selection')"
      />
    </div>
    <div v-else class="document-empty"><FileText :size="28" /><span>{{ labels.emptyPrompt }}</span></div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ChevronLeft, ChevronRight, Download, Eye, FileText, LoaderCircle, Save } from "lucide-vue-next";
import DraftEditor from "@/components/DraftEditor.vue";
import type { DraftProposal, FlowStage, SessionDetail } from "@/types";

type VisualLine = { key: string; label: string; logicalLine: number; continuation: boolean };
type DraftSaveState = { label: string; hint: string; tone: "muted" | "pending" | "error" | "unsaved" | "saved" };
const props = defineProps<{
  modelValue: string; session: SessionDetail | null; stage: FlowStage | null; selectedStageId: string; currentStageId: string; stageIndex: number; stageCount: number; streaming: boolean; drafting: boolean;
  proposal: DraftProposal | null; proposalLabel: string; visualLines: VisualLine[]; scrollTop: number; lineHeight: number; cursorLine: number; selectionLabel: string; attachedLabel: string;
  saveState: DraftSaveState; saving: boolean; advanceDisabledReason: string;
  role_category?: "teacher" | "study_travel" | "parent";
}>();
const emit = defineEmits<{
  'update:modelValue': [value: string]; previous: []; next: []; save: []; export: []; preview: []; 'editor-ready': [element: HTMLTextAreaElement]; 'editor-input': []; 'editor-scroll': []; 'capture-selection': []; 'add-selection': []; 'clear-selection': [];
}>();

const roleCategory = props.role_category || "teacher";
const isLastStage = computed(() => props.stageCount > 0 && props.stageIndex >= props.stageCount - 1);
const advanceLabel = computed(() => {
  if (!isLastStage.value) return "定稿并进入下一阶段";
  if (props.role_category === "study_travel") return "完成并提交报告";
  if (props.role_category === "parent") return "完成家庭活动方案";
  return "完成教案";
});
const advanceHelp = computed(() => isLastStage.value
  ? "提交当前阶段内容并完成本次流程。"
  : "当前内容会作为本阶段定稿保存，然后进入下一阶段。未手动保存的编辑也会一并提交。");

const labels = computed(() => ({
  planLabel: props.role_category === "parent" ? "家庭活动方案" : "草案制定",
  selectPrompt: props.role_category === "parent" ? "选择一个阶段开始编辑家庭活动方案" : "选择一个阶段开始编辑草案",
  exportTitle: props.role_category === "parent" ? "导出家庭探究活动方案" : "导出草案",
  emptyPrompt: props.role_category === "parent" ? "从左侧选择一个阶段查看活动方案" : "从左侧选择一个阶段查看草案内容",
}));

const content = computed({ get: () => props.modelValue, set: (value: string) => emit('update:modelValue', value) });
</script>
