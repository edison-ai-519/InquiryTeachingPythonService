<template>
  <section class="conversation-panel">
    <header class="conversation-header">
      <div>
        <p class="section-kicker">当前阶段</p>
        <h1>{{ stage?.name || '开始探究' }}</h1>
        <span>{{ stage?.display_direction || stage?.direction || (roleCategory === 'parent' ? '创建家庭探究活动后，主导师会陪您逐步设计亲子活动。' : roleCategory === 'study_travel' ? '在项目协同中设置场景并发布任务，或创建独立研学方案。' : '创建教案后，主导师会陪您逐步完成教学设计。') }}</span>
      </div>
      <button class="text-button" type="button" :disabled="!session || streaming" @click="$emit('rollback')"><Undo2 :size="16" />回滚</button>
    </header>
    <p v-if="workflowStatus" class="conversation-workflow-status" role="status" aria-live="polite">{{ workflowStatus }}</p>
    <p v-if="warning" class="stream-warning">{{ warning }}</p>
    <div ref="feed" class="message-feed">
      <article v-for="message in messages" :key="message.id || message.created_at || `${message.message_type}-${message.content}`" class="message-row" :class="[message.role, message.message_type || 'chat']">
        <div v-if="message.role === 'assistant'" class="message-avatar"><Bot v-if="message.message_type === 'expert_advice'" :size="16" /><GraduationCap v-else :size="16" /></div>
        <div class="message-body">
          <div class="message-meta">
            <strong>{{ messageRoleLabel(message) }}</strong>
            <span v-if="message.message_type === 'expert_advice'" class="expert-badge">专家</span>
            <small v-if="message.agent_role">{{ message.agent_role }}</small>
            <small>{{ stageNames[message.stage_id] || message.stage_id }}</small>
          </div>
          <div class="message-content markdown-content" v-html="render(message.content)"></div>
          <span v-if="message.interrupted" class="message-interrupted"><Square :size="11" />已停止生成</span>
        </div>
      </article>
      <div v-if="!messages.length" class="conversation-empty">
        <GraduationCap :size="28" />
        <template v-if="!session">
          <strong>{{ roleCategory === 'parent' ? '先创建家庭探究活动' : roleCategory === 'study_travel' ? '先创建研学项目' : '先创建一个教学课题' }}</strong>
          <span>{{ roleCategory === 'study_travel' ? '在项目协同中设置场景和物料，再向教师或家长工作台发布任务。' : '创建后，主导师会结合当前阶段陪您逐步完成方案。' }}</span>
          <button v-if="roleCategory === 'study_travel'" class="conversation-example-button" type="button" @click="$emit('open-tasks')">打开项目协同</button>
          <button v-if="roleCategory !== 'study_travel'" class="conversation-example-button" type="button" @click="$emit('create-session')">开始创建</button>
        </template>
        <template v-else>
          <strong>{{ welcomeCopy.title }}</strong>
          <span>{{ welcomeCopy.description }}</span>
          <p class="conversation-next-step">{{ welcomeCopy.nextStep }}</p>
          <button class="conversation-example-button" type="button" @click="$emit('use-example', welcomeCopy.example)">用示例填入输入框</button>
        </template>
      </div>
    </div>
    <slot />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Bot, GraduationCap, Square, Undo2 } from "lucide-vue-next";
import type { FlowStage, MessageItem, SessionDetail, UserRole } from "@/types";
import { workspaceWelcomeCopy } from "@/utils/workspaceUx";

const props = defineProps<{
  session: SessionDetail | null;
  roleCategory?: string;
  stage: FlowStage | null;
  messages: MessageItem[];
  stageNames: Record<string, string>;
  warning: string;
  workflowStatus: string;
  streaming: boolean;
  render: (text: string) => string;
  messageRoleLabel: (message: MessageItem) => string;
}>();
const emit = defineEmits<{ rollback: []; 'feed-ready': [element: HTMLElement]; 'create-session': []; 'open-tasks': []; 'use-example': [text: string] }>();
const welcomeCopy = computed(() => workspaceWelcomeCopy[(props.roleCategory as UserRole) || "teacher"]);
const feed = ref<HTMLElement | null>(null);
onMounted(() => { if (feed.value) emit('feed-ready', feed.value); });
</script>
