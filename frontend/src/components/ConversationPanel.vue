<template>
  <section class="conversation-panel">
    <header class="conversation-header">
      <div>
        <p class="section-kicker">当前阶段</p>
        <h1>{{ stage?.name || '开始探究' }}</h1>
        <span>{{ stage?.display_direction || stage?.direction || '创建教案后，主导师会陪您逐步完成教学设计。' }}</span>
      </div>
      <button class="text-button" type="button" :disabled="!session || streaming" @click="$emit('rollback')"><Undo2 :size="16" />回滚</button>
    </header>
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
      <div v-if="!messages.length" class="conversation-empty"><GraduationCap :size="28" /><strong>从一个教学问题开始</strong><span>主导师会根据当前阶段，协助您逐步形成教学方案。</span></div>
    </div>
    <slot />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Bot, GraduationCap, Square, Undo2 } from "lucide-vue-next";
import type { FlowStage, MessageItem, SessionDetail } from "@/types";

const props = defineProps<{
  session: SessionDetail | null;
  stage: FlowStage | null;
  messages: MessageItem[];
  stageNames: Record<string, string>;
  warning: string;
  streaming: boolean;
  render: (text: string) => string;
  messageRoleLabel: (message: MessageItem) => string;
}>();
const emit = defineEmits<{ rollback: []; 'feed-ready': [element: HTMLElement] }>();
const feed = ref<HTMLElement | null>(null);
onMounted(() => { if (feed.value) emit('feed-ready', feed.value); });
</script>
