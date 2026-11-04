<template>
  <aside class="workspace-sidebar" :class="{ collapsed }">
    <div class="sidebar-actions">
      <button class="sidebar-action primary" type="button" title="新建会话" @click="$emit('new-session')"><Plus :size="18" /><span>{{ labels.newSession }}</span></button>
      <label class="sidebar-search" title="搜索会话">
        <Search :size="17" />
        <input v-model="searchText" type="search" :placeholder="labels.searchPlaceholder" />
      </label>
    </div>

    <template v-if="!collapsed">
      <section class="sidebar-session-section">
        <div class="sidebar-section-head"><span>{{ labels.mySessions }}</span><button v-if="session && !session.task_session" class="sidebar-delete-button" type="button" :disabled="uploading" @click="$emit('delete-session')"><Trash2 :size="14" />删除草案</button></div>
        <div class="sidebar-session-list" aria-label="我的草案">
          <button v-for="item in filteredSessions" :key="item.id" class="sidebar-session-card" :class="{ active: item.id === selectedSessionId }" type="button" :disabled="uploading" :aria-current="item.id === selectedSessionId ? 'page' : undefined" @click="$emit('select-session', item.id)">
            <strong>{{ item.topic || item.title }}</strong>
            <span>{{ item.flow_display_name }}</span>
            <small>{{ getSessionProgressLabel(item.status, item.current_stage_index, flowStageCounts[item.flow_name] || 0) }}</small>
          </button>
          <div v-if="!sessions.length" class="sidebar-empty">{{ labels.noSessions }}</div>
          <div v-else-if="!filteredSessions.length" class="sidebar-empty">{{ labels.noMatch }}</div>
        </div>
        <p v-if="operationError" class="sidebar-operation-error" role="alert">{{ operationError }}</p>
      </section>
      <div class="sidebar-section-head stage-section-head"><span>{{ labels.flowLabel }}</span><small v-if="session">{{ progress }}</small></div>
    </template>

    <StageTimeline
      v-if="session"
      :stages="stages"
      :selected-stage-id="selectedStageId"
      :current-stage-id="currentStageId"
      :output="output"
      :disabled="uploading"
      @select-stage="$emit('select-stage', $event)"
    />
    <div v-else class="sidebar-blank"><BookOpen :size="20" /><span>{{ labels.selectOrCreate }}</span></div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { BookOpen, Plus, Search, Trash2 } from "lucide-vue-next";
import StageTimeline from "@/components/StageTimeline.vue";
import type { FlowStage, SessionDetail, SessionListItem, StageOutput } from "@/types";
import { getSessionProgressLabel } from "@/utils/workspaceUx";

const props = defineProps<{
  collapsed: boolean;
  session: SessionDetail | null;
  sessions: SessionListItem[];
  selectedSessionId: string;
  stages: FlowStage[];
  selectedStageId: string;
  currentStageId: string;
  progress: string;
  uploading: boolean;
  search: string;
  role_category?: "teacher" | "study_travel" | "parent";
  flowStageCounts: Record<string, number>;
  operationError: string;
  output: (stageId: string) => StageOutput | undefined;
}>();

const emit = defineEmits<{
  'update:search': [value: string];
  'new-session': [];
  'delete-session': [];
  'select-session': [id: string];
  'select-stage': [id: string];
}>();

const labels = computed(() => ({
  newSession: props.role_category === "parent" ? "新建活动" : props.role_category === "study_travel" ? "新建研学方案" : "新建草案",
  searchPlaceholder: "搜索草案名称或流程",
  mySessions: props.role_category === "parent" ? "我的活动" : props.role_category === "study_travel" ? "我的研学方案" : "我的草案",
  noSessions: props.role_category === "parent" ? "新建家庭探究活动后会显示在这里。" : props.role_category === "study_travel" ? "新建研学方案后会显示在这里。" : "新建课题后会显示在这里。",
  flowLabel: "流程",
  noMatch: "没有匹配的草案",
  selectOrCreate: props.role_category === "parent" ? "选择或新建家庭活动" : props.role_category === "study_travel" ? "选择或新建研学方案" : "选择或新建课题",
}));

const searchText = computed({ get: () => props.search, set: (value: string) => emit('update:search', value) });
const filteredSessions = computed(() => {
  const query = props.search.trim().toLowerCase();
  if (!query) return props.sessions;
  return props.sessions.filter((item) => `${item.topic} ${item.flow_display_name}`.toLowerCase().includes(query));
});
</script>
