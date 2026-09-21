<template>
  <section class="knowledge-graph-panel">
    <header>
      <div>
        <strong>{{ agentName ? `${agentName} 知识图谱` : "知识图谱" }}</strong>
        <span>{{ graph.entities.length }} 个节点 · {{ graph.relations.length }} 条关系</span>
      </div>
      <button type="button" @click="$emit('close')"><X :size="15" />关闭</button>
    </header>
    <div v-if="loading" class="knowledge-graph-empty"><LoaderCircle class="spin-icon" :size="18" />正在解析局部图谱</div>
    <div v-else-if="!graph.entities.length" class="knowledge-graph-empty">没有找到可展示的图谱关系</div>
    <div v-else class="knowledge-graph-body">
      <FocusKnowledgeGraphCanvas
        :graph="graph"
        :selected-entity-ids="selectedEntityIds"
        :focused-entity-id="focusedEntityId"
        :expanding="expanding"
        aria-label="知识图谱局部关系"
        @select-node="$emit('toggle-node', $event)"
        @focus-node="$emit('focus-node', $event)"
      />
    </div>
    <footer>
      <span>{{ selectedEntityIds.length ? `已选择 ${selectedEntityIds.length} 个节点` : "点击节点选择回答依据" }}</span>
      <button type="button" :disabled="!selectedEntityIds.length || streaming" @click="$emit('answer')">
        <GitBranch :size="15" />按选中节点回答
      </button>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { GitBranch, LoaderCircle, X } from "lucide-vue-next";
import FocusKnowledgeGraphCanvas from "@/components/FocusKnowledgeGraphCanvas.vue";
import type { KnowledgeGraphPayload } from "@/types";

const props = defineProps<{
  graph: KnowledgeGraphPayload;
  selectedEntityIds: string[];
  loading: boolean;
  expanding: boolean;
  streaming: boolean;
  agentName: string;
  focusedEntityId: string;
}>();

const emit = defineEmits<{
  close: [];
  answer: [];
  'toggle-node': [entityId: string];
  'focus-node': [entityId: string];
}>();
</script>
