<template>
  <aside class="document-workbench" :class="{ drafting }">
    <header class="document-header">
      <div><p class="section-kicker">教学方案</p><h2>教学方案</h2><span>{{ session ? `${session.topic} · ${stage?.name || '未选择阶段'}` : '选择一个教案开始编辑' }}</span></div>
      <div v-if="session" class="document-actions">
        <button class="icon-text-button" type="button" title="上一阶段" :disabled="stageIndex === 0 || streaming" @click="$emit('previous')"><ChevronLeft :size="16" /><span>上一阶段</span></button>
        <button class="icon-text-button" type="button" title="保存" :disabled="!selectedStageId" @click="$emit('save')"><Save :size="16" /><span>保存</span></button>
        <button class="icon-text-button" type="button" title="导出教案" @click="$emit('export')"><Download :size="16" /><span>导出</span></button>
        <button class="advance-button" type="button" :disabled="streaming || session.status === 'completed' || selectedStageId !== currentStageId" @click="$emit('next')">定稿并进入下一阶段<ChevronRight :size="16" /></button>
      </div>
    </header>
    <div v-if="session && selectedStageId" class="paper-workspace">
      <div class="paper-toolbar"><div><strong>编辑模式</strong><small>{{ proposal ? proposalLabel : '所有更改可随时保存；开启草案后可发起 AI 修订。' }}</small></div><button type="button" @click="$emit('preview')"><Eye :size="16" />预览与审阅</button></div>
      <DraftEditor
        v-model="content"
        :visual-lines="visualLines"
        :scroll-top="scrollTop"
        :line-height="lineHeight"
        :cursor-line="cursorLine"
        :selection-label="selectionLabel"
        :attached-label="attachedLabel"
        @editor-ready="$emit('editor-ready', $event)"
        @input="$emit('editor-input')"
        @scroll="$emit('editor-scroll')"
        @capture-selection="$emit('capture-selection')"
        @add-selection="$emit('add-selection')"
        @clear-selection="$emit('clear-selection')"
      />
    </div>
    <div v-else class="document-empty"><FileText :size="28" /><span>从左侧选择一个阶段查看教学方案</span></div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ChevronLeft, ChevronRight, Download, Eye, FileText, Save } from "lucide-vue-next";
import DraftEditor from "@/components/DraftEditor.vue";
import type { DraftProposal, FlowStage, SessionDetail } from "@/types";

type VisualLine = { key: string; label: string; logicalLine: number; continuation: boolean };
const props = defineProps<{
  modelValue: string; session: SessionDetail | null; stage: FlowStage | null; selectedStageId: string; currentStageId: string; stageIndex: number; streaming: boolean; drafting: boolean;
  proposal: DraftProposal | null; proposalLabel: string; visualLines: VisualLine[]; scrollTop: number; lineHeight: number; cursorLine: number; selectionLabel: string; attachedLabel: string;
}>();
const emit = defineEmits<{
  'update:modelValue': [value: string]; previous: []; next: []; save: []; export: []; preview: []; 'editor-ready': [element: HTMLTextAreaElement]; 'editor-input': []; 'editor-scroll': []; 'capture-selection': []; 'add-selection': []; 'clear-selection': [];
}>();
const content = computed({ get: () => props.modelValue, set: (value: string) => emit('update:modelValue', value) });
</script>
