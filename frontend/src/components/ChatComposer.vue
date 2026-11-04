<template>
  <section class="chat-composer">
    <div class="composer-chips" v-if="expert || selectionLabel">
        <button v-if="expert" class="composer-chip expert" type="button" :disabled="busy || streaming" @click="$emit('clear-expert')"><Bot :size="14" />{{ expert.name }}<X :size="14" /></button>
        <button v-if="selectionLabel" class="composer-chip" type="button" :disabled="busy" @click="$emit('clear-selection')"><AtSign :size="14" />{{ selectionLabel }}<X :size="14" /></button>
    </div>
    <div v-if="files.length" class="composer-reference-list" aria-label="已上传参考资料">
      <article v-for="item in files" :key="item.id" class="composer-reference-card">
        <FileText :size="17" />
        <span :title="item.name">{{ item.name }}</span>
        <small :class="`status-${item.status}`">{{ fileStatusLabel(item) }}</small>
        <button type="button" :title="`删除 ${item.name}`" :disabled="busy || streaming || deletingIds.includes(item.id)" @click="$emit('remove-file', item)"><LoaderCircle v-if="deletingIds.includes(item.id)" class="spin-icon" :size="14" /><X v-else :size="15" /></button>
      </article>
    </div>
    <div class="composer-shell">
        <textarea ref="inputRef" v-model="inputText" rows="2" :disabled="busy" :placeholder="session?.role_category === 'parent' ? '描述孩子感兴趣的问题、家庭观察或修改想法…' : session?.role_category === 'study_travel' ? '描述研学目标、活动地点、参与对象和现有物料…' : '输入教学目标、学生情况、已有条件或修改要求…'" @input="$emit('resize')" @keydown="$emit('keydown', $event)" />
      <div class="composer-toolbar">
        <div class="composer-tools">
          <button type="button" title="上传参考资料" :disabled="busy || streaming || uploading || files.length >= 10 || !session" @click="$emit('open-file')"><LoaderCircle v-if="uploading" class="spin-icon" :size="17" /><Paperclip v-else :size="17" /></button>
          <button type="button" title="知识库" :disabled="busy" @click="$emit('open-curriculum')"><BookOpen :size="17" /></button>
          <slot name="file-input" />
          <small v-if="fileError" class="composer-file-error">{{ fileError }}</small>
        </div>
        <div class="composer-actions">
          <button class="draft-toggle" type="button" :class="{ active: draftMode }" :disabled="busy || streaming || !session" title="草案模式用于生成初稿或修订选中内容；不会直接推进阶段。" @click="$emit('toggle-draft')"><FilePenLine :size="16" />草案</button>
          <div class="send-action">
            <button class="send-button" type="button" :class="{ stop: streaming && requestId }" :disabled="sendDisabled" :title="disabledReason || '发送当前问题给主导师或所选专家'" @click="streaming && requestId ? $emit('stop') : $emit('send')"><Square v-if="streaming && requestId" :size="15" /><Send v-else :size="16" />{{ streaming && requestId ? '停止' : '发送' }}</button>
            <small v-if="sendDisabled && disabledReason" class="composer-action-hint">{{ disabledReason }}</small>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { AtSign, BookOpen, Bot, FilePenLine, FileText, LoaderCircle, Paperclip, Send, Square, X } from "lucide-vue-next";
import type { ExpertAgentItem, SessionDetail, SessionFileItem } from "@/types";

const props = defineProps<{
  modelValue: string;
  expert: ExpertAgentItem | null;
  selectionLabel: string;
  files: SessionFileItem[];
  deletingIds: string[];
  streaming: boolean;
  busy: boolean;
  uploading: boolean;
  session: SessionDetail | null;
  draftMode: boolean;
  requestId: string | null;
  fileError: string;
  sendDisabled: boolean;
  disabledReason: string;
  fileStatusLabel: (file: SessionFileItem) => string;
}>();
const emit = defineEmits<{
  'update:modelValue': [value: string];
  'input-ready': [element: HTMLTextAreaElement]; resize: []; keydown: [event: KeyboardEvent];
  'clear-expert': []; 'clear-selection': []; 'remove-file': [file: SessionFileItem]; 'open-file': []; 'open-curriculum': []; 'toggle-draft': []; send: []; stop: [];
}>();
const inputRef = ref<HTMLTextAreaElement | null>(null);
onMounted(() => { if (inputRef.value) emit('input-ready', inputRef.value); });
const inputText = computed({ get: () => props.modelValue, set: (value: string) => emit('update:modelValue', value) });
</script>
