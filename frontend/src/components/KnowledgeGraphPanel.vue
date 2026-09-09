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
      <svg class="knowledge-graph-svg" viewBox="0 0 520 320" role="img" aria-label="知识图谱局部关系">
        <line
          v-for="edge in graphEdges"
          :key="edge.id"
          :x1="edge.x1"
          :y1="edge.y1"
          :x2="edge.x2"
          :y2="edge.y2"
          class="knowledge-edge"
          :class="{ selected: isEdgeSelected(edge.id) }"
        />
        <text
          v-for="edge in graphEdges"
          :key="`${edge.id}-label`"
          :x="(edge.x1 + edge.x2) / 2"
          :y="(edge.y1 + edge.y2) / 2 - 4"
          class="knowledge-edge-label"
          :class="{ selected: isEdgeSelected(edge.id) }"
        >
          {{ edge.predicate_label || edge.predicate }}
        </text>
        <g
          v-for="node in graphNodes"
          :key="node.id"
          class="knowledge-node"
          :class="[node.entity.entity_type, { selected: isNodeSelected(node.id) }]"
          @click.stop="onNodeClick(node.id)"
        >
          <circle :cx="node.x" :cy="node.y" r="26" />
          <text :x="node.x" :y="node.y + 4">{{ node.entity.name }}</text>
        </g>
      </svg>
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
import { computed } from "vue";
import { GitBranch, LoaderCircle, X } from "lucide-vue-next";
import type { KnowledgeGraphPayload } from "@/types";

const props = defineProps<{
  graph: KnowledgeGraphPayload;
  selectedEntityIds: string[];
  loading: boolean;
  streaming: boolean;
  agentName: string;
}>();

const emit = defineEmits<{
  close: [];
  answer: [];
  'toggle-node': [entityId: string];
}>();

const graphNodes = computed(() => {
  const count = Math.max(props.graph.entities.length, 1);
  const centerX = 260;
  const centerY = 160;
  const radiusX = 190;
  const radiusY = 105;
  return props.graph.entities.map((entity, index) => {
    const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
    return {
      id: entity.id,
      entity,
      x: centerX + Math.cos(angle) * radiusX,
      y: centerY + Math.sin(angle) * radiusY,
    };
  });
});

const nodeById = computed(() => {
  const map = new Map<string, (typeof graphNodes.value)[number]>();
  for (const node of graphNodes.value) {
    map.set(node.id, node);
  }
  return map;
});

const graphEdges = computed(() => {
  return props.graph.relations.flatMap((relation) => {
    const source = nodeById.value.get(relation.subject_entity_id);
    const target = nodeById.value.get(relation.object_entity_id);
    if (!source || !target) return [];
    return [{
      id: relation.id,
      predicate: relation.predicate,
      predicate_label: relation.predicate_label,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
    }];
  });
});

const selectedRelationIds = computed(() => {
  const ids = new Set<string>();
  const selectedIds = new Set(props.selectedEntityIds);
  for (const relation of props.graph.relations) {
    if (selectedIds.has(relation.subject_entity_id) && selectedIds.has(relation.object_entity_id)) {
      ids.add(relation.id);
    }
  }
  return ids;
});

function isEdgeSelected(relationId: string): boolean {
  return selectedRelationIds.value.has(relationId);
}

function isNodeSelected(entityId: string): boolean {
  return props.selectedEntityIds.includes(entityId);
}

function onNodeClick(entityId: string) {
  emit("toggle-node", entityId);
}
</script>
