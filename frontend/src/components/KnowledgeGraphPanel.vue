<template>
  <section class="knowledge-graph-panel">
    <header>
      <div>
        <strong>{{ agentName ? `${agentName} 知识图谱` : "知识图谱" }}</strong>
        <span>{{ graph.entities.length }} 个节点 · {{ graph.relations.length }} 条关系</span>
      </div>
      <div class="knowledge-graph-panel-actions">
        <button type="button" :disabled="loading || !graph.entities.length" @click="openGraphStage"><Maximize2 :size="15" />放大</button>
      </div>
    </header>
    <div v-if="loading" class="knowledge-graph-empty"><LoaderCircle class="spin-icon" :size="18" />正在解析局部图谱</div>
    <div v-else-if="!graph.entities.length" class="knowledge-graph-empty">没有找到可展示的图谱关系</div>
    <div v-else class="knowledge-graph-body">
      <FocusKnowledgeGraphCanvas
        :graph="graph"
        :selected-entity-ids="selectedEntityIds"
        :selected-relation-id="selectedRelationId"
        :expanding="expanding"
        :expanding-node-id="expandingNodeId"
        :max-nodes="graph.entities.length || 18"
        :layout-revision="layoutRevision"
        :expansion="expansion"
        aria-label="知识图谱局部关系"
        @select-node="$emit('toggle-node', $event)"
        @focus-node="$emit('focus-node', $event)"
        @select-relation="$emit('select-relation', $event)"
      />
    </div>
    <footer>
      <span>{{ selectedEntityIds.length ? `已选择 ${selectedEntityIds.length} 个节点` : "点击节点选择回答依据" }}</span>
      <button type="button" :disabled="!selectedEntityIds.length || streaming" @click="$emit('answer')">
        <GitBranch :size="15" />按选中节点回答
      </button>
    </footer>

    <Teleport to="body">
      <div v-if="expanded" class="graph-stage-overlay" role="dialog" aria-modal="true" aria-label="知识图谱大幕布" @keydown.esc.prevent="closeGraphStage">
        <section class="graph-stage-panel">
          <header class="graph-stage-head">
            <div>
              <strong>{{ agentName ? `${agentName} 知识图谱` : "知识图谱" }}</strong>
              <span>{{ graph.entities.length }} 个节点 · {{ graph.relations.length }} 条关系</span>
            </div>
            <button ref="graphStageCloseRef" type="button" @click="closeGraphStage"><X :size="16" />关闭</button>
          </header>
          <div class="graph-stage-body">
            <FocusKnowledgeGraphCanvas
              :graph="graph"
              :selected-entity-ids="selectedEntityIds"
              :selected-relation-id="selectedRelationId"
              :expanding="expanding"
              :expanding-node-id="expandingNodeId"
              :max-nodes="graph.entities.length || 18"
              :fullscreen="true"
              :layout-revision="layoutRevision"
              :expansion="expansion"
              variant="map"
              aria-label="知识图谱大幕布"
              @select-node="$emit('toggle-node', $event)"
              @focus-node="$emit('focus-node', $event)"
              @select-relation="$emit('select-relation', $event)"
            />
          </div>
        </section>
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { GitBranch, LoaderCircle, Maximize2, X } from "lucide-vue-next";
import FocusKnowledgeGraphCanvas from "@/components/FocusKnowledgeGraphCanvas.vue";
import type { KnowledgeGraphPayload } from "@/types";

const props = defineProps<{
  graph: KnowledgeGraphPayload;
  selectedEntityIds: string[];
  selectedRelationId: string;
  loading: boolean;
  expanding: boolean;
  expandingNodeId: string;
  streaming: boolean;
  agentName: string;
  layoutRevision: number;
  expansion: { sourceId: string; addedEntityIds: string[]; revision: number } | null;
}>();

const emit = defineEmits<{
  answer: [];
  'toggle-node': [entityId: string];
  'focus-node': [entityId: string];
  'select-relation': [relationId: string];
}>();

const expanded = ref(false);
const graphStageCloseRef = ref<HTMLButtonElement | null>(null);
let graphStageReturnFocus: HTMLElement | null = null;
let graphStagePreviousOverflow = "";

watch(expanded, async (visible) => {
  if (visible) {
    graphStageReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    graphStagePreviousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    await nextTick();
    graphStageCloseRef.value?.focus();
    return;
  }
  document.body.style.overflow = graphStagePreviousOverflow;
  graphStageReturnFocus?.focus();
  graphStageReturnFocus = null;
});

onBeforeUnmount(() => {
  document.body.style.overflow = graphStagePreviousOverflow;
});

function openGraphStage() {
  expanded.value = true;
}

function closeGraphStage() {
  expanded.value = false;
}
</script>
