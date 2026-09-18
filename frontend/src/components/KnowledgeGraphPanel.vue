<template>
  <section class="knowledge-graph-panel">
    <header>
      <div>
        <strong>{{ agentName ? `${agentName} 局部知识图谱` : "局部知识图谱" }}</strong>
        <span v-if="query" :title="query">问题：{{ query }} · {{ graph.entities.length }} 个节点 · {{ graph.relations.length }} 条关系</span>
        <span v-else>{{ graph.entities.length }} 个节点 · {{ graph.relations.length }} 条关系</span>
      </div>
      <div class="graph-panel-actions">
        <button type="button" :disabled="loading || !query" @click="$emit('refresh')"><RefreshCw :size="14" />刷新</button>
        <button type="button" @click="$emit('close')"><X :size="15" />关闭</button>
      </div>
    </header>
    <div v-if="loading" class="knowledge-graph-empty"><LoaderCircle class="spin-icon" :size="18" />正在解析局部图谱</div>
    <div v-else-if="error" class="knowledge-graph-empty graph-error">图谱加载失败：{{ error }}</div>
    <div v-else-if="!query" class="knowledge-graph-empty">请先向昆虫或自然生态专家发送问题</div>
    <div v-else-if="!graph.entities.length" class="knowledge-graph-empty">当前问题没有匹配到可展示的图谱关系</div>
    <div v-else class="knowledge-graph-body">
      <svg class="knowledge-graph-svg" viewBox="0 0 520 320" role="img" aria-label="知识图谱局部关系">
        <defs>
          <marker id="knowledge-arrow" viewBox="0 0 10 10" refX="26" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" />
          </marker>
          <marker id="knowledge-arrow-selected" viewBox="0 0 10 10" refX="26" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" />
          </marker>
        </defs>
        <line
          v-for="edge in graphEdges"
          :key="`${edge.id}-hit`"
          :x1="edge.x1"
          :y1="edge.y1"
          :x2="edge.x2"
          :y2="edge.y2"
          class="knowledge-edge-hit"
          @click.stop="emit('toggle-relation', edge.id)"
        />
        <line
          v-for="edge in graphEdges"
          :key="edge.id"
          :x1="edge.x1"
          :y1="edge.y1"
          :x2="edge.x2"
          :y2="edge.y2"
          class="knowledge-edge"
          :class="[{ selected: isEdgeSelected(edge.id) }, edge.evidenceStatus]"
          :marker-end="isEdgeSelected(edge.id) ? 'url(#knowledge-arrow-selected)' : 'url(#knowledge-arrow)'"
          @click.stop="emit('toggle-relation', edge.id)"
        />
        <text
          v-for="edge in graphEdges"
          :key="`${edge.id}-label`"
          :x="(edge.x1 + edge.x2) / 2"
          :y="(edge.y1 + edge.y2) / 2 - 5"
          class="knowledge-edge-label"
          :class="[{ selected: isEdgeSelected(edge.id) }, edge.evidenceStatus]"
        >
          {{ edge.predicateLabel }}{{ edge.evidenceStatus === "unverified" ? " · 待补证" : "" }}
        </text>
        <g
          v-for="node in graphNodes"
          :key="node.id"
          class="knowledge-node"
          :class="[node.entity.entity_type, { selected: isNodeSelected(node.id) }]"
          @click.stop="emit('toggle-node', node.id)"
        >
          <circle :cx="node.x" :cy="node.y" r="26" />
          <text :x="node.x" :y="node.y + 4">{{ node.entity.name }}</text>
        </g>
      </svg>

      <section v-if="recommendedPaths.length" class="knowledge-recommendations">
        <strong>推荐链路</strong>
        <button
          v-for="path in recommendedPaths"
          :key="path.id"
          type="button"
          :class="{ active: isPathSelected(path.id) }"
          @click="emit('select-path', path.id)"
        >
          <span>{{ pathLabel(path) }}</span>
          <small :class="path.evidence_status">{{ evidenceLabel(path.evidence_status) }} · {{ path.reason }}</small>
        </button>
        <p>共享植物仅表示生态关联，不能据此推断两种昆虫存在直接作用。</p>
      </section>
    </div>
    <footer>
      <span>{{ selectedEntityIds.length ? `已选择 ${selectedEntityIds.length} 个节点、${selectedRelationIds.length} 条关系` : "点击节点或关系选择回答依据" }}</span>
      <button type="button" :disabled="!selectedEntityIds.length || streaming" @click="$emit('answer')">
        <GitBranch :size="15" />按选中链路重新回答
      </button>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { GitBranch, LoaderCircle, RefreshCw, X } from "lucide-vue-next";
import type { KnowledgeGraphPayload, KnowledgePath } from "@/types";

const props = defineProps<{
  graph: KnowledgeGraphPayload;
  selectedEntityIds: string[];
  selectedRelationIds: string[];
  loading: boolean;
  streaming: boolean;
  agentName: string;
  query: string;
  error: string;
}>();

const emit = defineEmits<{
  close: [];
  refresh: [];
  answer: [];
  "toggle-node": [entityId: string];
  "toggle-relation": [relationId: string];
  "select-path": [pathId: string];
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

const nodeById = computed(() => new Map(graphNodes.value.map((node) => [node.id, node])));

const graphEdges = computed(() => props.graph.relations.flatMap((relation) => {
  const source = nodeById.value.get(relation.subject_entity_id);
  const target = nodeById.value.get(relation.object_entity_id);
  if (!source || !target) return [];
  return [{
    id: relation.id,
    predicateLabel: relation.predicate_label || relation.predicate,
    evidenceStatus: relation.evidence_status,
    x1: source.x,
    y1: source.y,
    x2: target.x,
    y2: target.y,
  }];
}));

const recommendedPaths = computed(() => props.graph.recommended_path_ids
  .map((pathId) => props.graph.paths.find((path) => path.id === pathId))
  .filter((path): path is KnowledgePath => Boolean(path))
  .slice(0, 5));

function isEdgeSelected(relationId: string): boolean {
  return props.selectedRelationIds.includes(relationId);
}

function isNodeSelected(entityId: string): boolean {
  return props.selectedEntityIds.includes(entityId);
}

function isPathSelected(pathId: string): boolean {
  const path = props.graph.paths.find((item) => item.id === pathId);
  return Boolean(path
    && path.entity_ids.every((id) => props.selectedEntityIds.includes(id))
    && path.relation_ids.every((id) => props.selectedRelationIds.includes(id)));
}

function pathLabel(path: KnowledgePath): string {
  const entityName = (id: string) => props.graph.entities.find((entity) => entity.id === id)?.name || id;
  if (!path.entity_ids.length) return "";
  let label = entityName(path.entity_ids[0]);
  for (let index = 0; index < path.relation_ids.length; index += 1) {
    const currentId = path.entity_ids[index];
    const nextId = path.entity_ids[index + 1];
    const relation = props.graph.relations.find((item) => item.id === path.relation_ids[index]);
    if (!relation) {
      label += ` — ${entityName(nextId)}`;
      continue;
    }
    const predicate = relation.predicate_label || relation.predicate;
    label += relation.subject_entity_id === currentId && relation.object_entity_id === nextId
      ? ` —${predicate}→ ${entityName(nextId)}`
      : ` ←${predicate}— ${entityName(nextId)}`;
  }
  return label;
}

function evidenceLabel(status: KnowledgePath["evidence_status"]): string {
  if (status === "verified") return "证据完整";
  if (status === "partial") return "部分有证据";
  return "待补证";
}
</script>
