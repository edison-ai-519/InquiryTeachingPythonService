<template>
  <header class="workspace-header">
    <div class="header-brand">
      <button class="header-icon-button" type="button" :title="sidebarCollapsed ? '展开侧栏' : '收起侧栏'" @click="$emit('toggle-sidebar')">
        <PanelLeftOpen v-if="sidebarCollapsed" :size="19" />
        <PanelLeftClose v-else :size="19" />
      </button>
      <div class="brand-mark"><GraduationCap :size="19" /></div>
      <div class="brand-copy">
        <strong>探究式教学工作台</strong>
        <span>Inquiry Teaching Studio</span>
      </div>
    </div>

    <div class="header-context" v-if="session">
      <strong>{{ session.topic }}</strong>
      <span>{{ session.flow_display_name }} · {{ stageProgress }} · {{ stage?.name || '准备开始' }}</span>
    </div>
    <div v-else class="header-context header-context-empty">创建一个课题，开始协同设计</div>

    <div class="header-actions">
      <ExpertSelector v-model="expertId" :experts="experts" :disabled="streaming || !session" />
      <span class="connection-status" :class="{ streaming }"><i></i>{{ streaming ? '正在生成' : '已连接' }}</span>
      <button class="header-icon-button" type="button" :title="themeMode === 'light' ? '切换深色模式' : '切换浅色模式'" @click="$emit('toggle-theme')">
        <Moon v-if="themeMode === 'light'" :size="17" />
        <Sun v-else :size="17" />
      </button>
      <details class="user-menu">
        <summary>{{ user?.username }}<ChevronDown :size="14" /></summary>
        <button type="button" @click="$emit('logout')"><LogOut :size="15" />退出登录</button>
      </details>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ChevronDown, GraduationCap, LogOut, Moon, PanelLeftClose, PanelLeftOpen, Sun } from "lucide-vue-next";
import ExpertSelector from "@/components/ExpertSelector.vue";
import type { AuthUser, ExpertAgentItem, FlowStage, SessionDetail } from "@/types";

const props = defineProps<{
  modelValue: string;
  experts: ExpertAgentItem[];
  user: AuthUser | null;
  session: SessionDetail | null;
  stage: FlowStage | null;
  stageProgress: string;
  streaming: boolean;
  sidebarCollapsed: boolean;
  themeMode: 'light' | 'dark';
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
  'toggle-sidebar': [];
  'toggle-theme': [];
  logout: [];
}>();

const expertId = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
});
</script>
