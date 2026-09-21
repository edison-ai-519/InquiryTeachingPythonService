<template>
  <div class="focus-graph-shell" :class="{ dragging: isDragging }">
    <div class="graph-overview-strip">
      <button type="button" :class="{ active: selectedType === '' }" @click="selectedType = ''">
        全部 <strong>{{ graph.entities.length }}</strong>
      </button>
      <button
        v-for="item in typeSummary"
        :key="item.type"
        type="button"
        :class="{ active: selectedType === item.type }"
        @click="selectType(item.type)"
      >
        {{ typeLabel(item.type) }} <strong>{{ item.count }}</strong>
      </button>
    </div>

    <div class="graph-explorer-layout">
      <aside class="graph-node-catalog">
        <div class="graph-catalog-head">
          <strong>节点目录</strong>
          <span>{{ filteredCatalogEntities.length }} 个</span>
        </div>
        <input v-model.trim="searchText" class="input" placeholder="搜索节点" />
        <div class="graph-node-list">
          <button
            v-for="entity in filteredCatalogEntities"
            :key="entity.id"
            type="button"
            :class="{ active: entity.id === activeEntityId, selected: isNodeSelected(entity.id) }"
            @click="activateEntity(entity.id)"
          >
            <span :title="entity.name">{{ entity.name }}</span>
            <small>{{ typeLabel(entity.entity_type) }} · {{ degreeByEntity.get(entity.id) || 0 }} 条关系</small>
          </button>
        </div>
      </aside>

      <section class="graph-map-pane">
        <div class="focus-graph-toolbar">
          <span>{{ focusLabel }}</span>
          <div>
            <button type="button" @click="zoomBy(0.12)">放大</button>
            <button type="button" @click="zoomBy(-0.12)">缩小</button>
            <button type="button" @click="resetViewport">重置</button>
          </div>
        </div>
        <svg
          class="knowledge-graph-svg focus-graph-svg"
          viewBox="0 0 620 380"
          role="img"
          :aria-label="ariaLabel"
          @pointerdown="startPan"
          @pointermove="movePan"
          @pointerup="endPan"
          @pointerleave="endPan"
          @wheel.prevent="onWheel"
        >
          <g :transform="viewportTransform">
            <line
              v-for="edge in visibleEdges"
              :key="edge.id"
              :x1="edge.x1"
              :y1="edge.y1"
              :x2="edge.x2"
              :y2="edge.y2"
              class="knowledge-edge"
              :class="{ selected: isEdgeSelected(edge.id), muted: edge.muted }"
              @click.stop="selectRelation(edge.id)"
            />
            <text
              v-for="edge in labelledEdges"
              :key="`${edge.id}-label`"
              :x="(edge.x1 + edge.x2) / 2"
              :y="(edge.y1 + edge.y2) / 2 - 5"
              class="knowledge-edge-label"
              :class="{ selected: isEdgeSelected(edge.id) }"
            >
              {{ edge.label }}
            </text>
            <g
              v-for="node in visibleNodes"
              :key="node.id"
              class="knowledge-node focus-graph-node"
              :class="[node.entity.entity_type, node.depthClass, { selected: isNodeSelected(node.id), focused: node.id === activeEntityId }]"
              @click.stop="selectNode(node.id)"
              @dblclick.stop="$emit('focus-node', node.id)"
            >
              <circle :cx="node.x" :cy="node.y" :r="node.radius" />
              <text :x="node.x" :y="node.y + 4">
                <title>{{ node.entity.name }}</title>
                {{ shortLabel(node.entity.name) }}
              </text>
            </g>
          </g>
        </svg>
        <div class="focus-graph-hint">
          <span v-if="expanding">正在展开邻近节点...</span>
          <span v-else-if="overflowCount">画布显示 {{ visibleNodes.length }} 个重点节点，另有 {{ overflowCount }} 个可在目录中查看</span>
          <span v-else>单击选择，双击展开；目录可查看全部节点</span>
        </div>
      </section>

      <aside class="graph-node-detail">
        <template v-if="activeEntity">
          <div class="graph-detail-title">
            <strong :title="activeEntity.name">{{ activeEntity.name }}</strong>
            <span>{{ typeLabel(activeEntity.entity_type) }}</span>
          </div>
          <p>{{ activeEntity.description || "暂无描述" }}</p>
          <div class="graph-detail-meta">
            <span>别名：{{ activeEntity.aliases.length ? activeEntity.aliases.join("、") : "无" }}</span>
            <span>知识库：{{ activeEntity.rag_sources.length ? activeEntity.rag_sources.join("、") : "未绑定" }}</span>
            <span>来源：{{ activeEntity.source || "未填写" }}</span>
          </div>
          <button type="button" @click="$emit('focus-node', activeEntity.id)">展开邻域</button>
        </template>
        <p v-else class="graph-detail-empty">请选择一个节点查看详情</p>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import type { KnowledgeEntity, KnowledgeGraphPayload } from "@/types";

type VisibleNode = {
  id: string;
  entity: KnowledgeEntity;
  x: number;
  y: number;
  radius: number;
  depth: number;
  depthClass: string;
};

const props = withDefaults(defineProps<{
  graph: KnowledgeGraphPayload;
  selectedEntityIds?: string[];
  focusedEntityId?: string;
  selectedRelationId?: string;
  expanding?: boolean;
  ariaLabel?: string;
  maxNodes?: number;
}>(), {
  selectedEntityIds: () => [],
  focusedEntityId: "",
  selectedRelationId: "",
  expanding: false,
  ariaLabel: "知识图谱探索视图",
  maxNodes: 18,
});

const emit = defineEmits<{
  "select-node": [entityId: string];
  "focus-node": [entityId: string];
  "select-relation": [relationId: string];
}>();

const viewport = reactive({ x: 0, y: 0, scale: 1 });
const isDragging = ref(false);
const dragStart = reactive({ x: 0, y: 0, viewportX: 0, viewportY: 0 });
const selectedType = ref("");
const searchText = ref("");
const localFocusedEntityId = ref("");

const entityById = computed(() => new Map(props.graph.entities.map((entity) => [entity.id, entity])));
const recommendedRelationIds = computed(() => new Set(
  props.graph.paths
    .filter((path) => props.graph.recommended_path_ids.includes(path.id))
    .flatMap((path) => path.relation_ids),
));

const degreeByEntity = computed(() => {
  const map = new Map<string, number>();
  for (const entity of props.graph.entities) map.set(entity.id, 0);
  for (const relation of props.graph.relations) {
    map.set(relation.subject_entity_id, (map.get(relation.subject_entity_id) || 0) + 1);
    map.set(relation.object_entity_id, (map.get(relation.object_entity_id) || 0) + 1);
  }
  return map;
});

const relatedEntityIds = computed(() => {
  const map = new Map<string, Set<string>>();
  for (const relation of props.graph.relations) {
    if (!map.has(relation.subject_entity_id)) map.set(relation.subject_entity_id, new Set());
    if (!map.has(relation.object_entity_id)) map.set(relation.object_entity_id, new Set());
    map.get(relation.subject_entity_id)?.add(relation.object_entity_id);
    map.get(relation.object_entity_id)?.add(relation.subject_entity_id);
  }
  return map;
});

const typeSummary = computed(() => {
  const counts = new Map<string, number>();
  for (const entity of props.graph.entities) {
    counts.set(entity.entity_type, (counts.get(entity.entity_type) || 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count || typeLabel(a.type).localeCompare(typeLabel(b.type), "zh-Hans-CN"));
});

const activeEntityId = computed(() => {
  if (props.focusedEntityId && entityById.value.has(props.focusedEntityId)) return props.focusedEntityId;
  if (localFocusedEntityId.value && entityById.value.has(localFocusedEntityId.value)) return localFocusedEntityId.value;
  const selected = props.selectedEntityIds.find((id) => entityById.value.has(id));
  if (selected) return selected;
  return rankedEntities.value[0]?.id || "";
});

const activeEntity = computed(() => entityById.value.get(activeEntityId.value) || null);
const focusLabel = computed(() => activeEntity.value ? `焦点：${activeEntity.value.name}` : "暂无焦点节点");

const rankedEntities = computed(() => {
  const recommendedEntityIds = new Set<string>();
  for (const relation of props.graph.relations) {
    if (!recommendedRelationIds.value.has(relation.id)) continue;
    recommendedEntityIds.add(relation.subject_entity_id);
    recommendedEntityIds.add(relation.object_entity_id);
  }
  const selected = new Set(props.selectedEntityIds);
  return [...props.graph.entities].sort((a, b) => {
    const scoreA = entityScore(a, recommendedEntityIds, selected);
    const scoreB = entityScore(b, recommendedEntityIds, selected);
    return scoreB - scoreA || a.name.localeCompare(b.name, "zh-Hans-CN");
  });
});

const filteredCatalogEntities = computed(() => {
  const keyword = searchText.value.toLowerCase();
  return rankedEntities.value.filter((entity) => {
    const matchesType = !selectedType.value || entity.entity_type === selectedType.value;
    const haystack = `${entity.name} ${entity.id} ${entity.entity_type} ${entity.aliases.join(" ")}`.toLowerCase();
    return matchesType && (!keyword || haystack.includes(keyword));
  });
});

const visibleEntityIds = computed(() => {
  const ids = new Set<string>();
  if (activeEntityId.value) ids.add(activeEntityId.value);
  for (const id of props.selectedEntityIds) ids.add(id);
  for (const id of relatedEntityIds.value.get(activeEntityId.value) || []) ids.add(id);
  for (const entity of filteredCatalogEntities.value) {
    if (ids.size >= props.maxNodes) break;
    ids.add(entity.id);
  }
  return ids;
});

const visibleNodes = computed<VisibleNode[]>(() => {
  const centerX = 310;
  const centerY = 190;
  const ids = [...visibleEntityIds.value].filter((id) => entityById.value.has(id)).slice(0, props.maxNodes);
  const centerId = activeEntityId.value || ids[0] || "";
  const firstHop = new Set(relatedEntityIds.value.get(centerId) || []);
  const ordered = ids.sort((a, b) => nodeDepth(a, centerId, firstHop) - nodeDepth(b, centerId, firstHop) || entityById.value.get(a)!.name.localeCompare(entityById.value.get(b)!.name, "zh-Hans-CN"));
  const ringNodes = ordered.filter((id) => id !== centerId);
  return ordered.map((id) => {
    const entity = entityById.value.get(id)!;
    if (id === centerId) return { id, entity, x: centerX, y: centerY, radius: 34, depth: 0, depthClass: "depth-0" };
    const index = ringNodes.indexOf(id);
    const count = Math.max(ringNodes.length, 1);
    const depth = firstHop.has(id) || props.selectedEntityIds.includes(id) ? 1 : 2;
    const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
    const radiusX = depth === 1 ? 205 : 270;
    const radiusY = depth === 1 ? 118 : 152;
    return {
      id,
      entity,
      x: centerX + Math.cos(angle) * radiusX,
      y: centerY + Math.sin(angle) * radiusY,
      radius: depth === 1 ? 25 : 18,
      depth,
      depthClass: depth === 1 ? "depth-1" : "depth-2",
    };
  });
});

const visibleNodeById = computed(() => new Map(visibleNodes.value.map((node) => [node.id, node])));
const overflowCount = computed(() => Math.max(0, props.graph.entities.length - visibleNodes.value.length));

const visibleEdges = computed(() => {
  return props.graph.relations.flatMap((relation) => {
    const source = visibleNodeById.value.get(relation.subject_entity_id);
    const target = visibleNodeById.value.get(relation.object_entity_id);
    if (!source || !target) return [];
    const selected = isEdgeSelected(relation.id);
    const touchesFocus = relation.subject_entity_id === activeEntityId.value || relation.object_entity_id === activeEntityId.value;
    if (!touchesFocus && !selected && (source.depth > 1 || target.depth > 1)) return [];
    return [{
      id: relation.id,
      label: relation.predicate_label || relation.predicate,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
      muted: !touchesFocus && !selected,
    }];
  });
});

const labelledEdges = computed(() => visibleEdges.value.filter((edge) => isEdgeSelected(edge.id)));
const viewportTransform = computed(() => `translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`);

watch(() => props.focusedEntityId, (entityId) => {
  if (entityId) localFocusedEntityId.value = entityId;
}, { immediate: true });

function entityScore(entity: KnowledgeEntity, recommendedEntityIds: Set<string>, selectedIds: Set<string>): number {
  let score = degreeByEntity.value.get(entity.id) || 0;
  if (entity.id === props.focusedEntityId) score += 1000;
  if (selectedIds.has(entity.id)) score += 800;
  if (recommendedEntityIds.has(entity.id)) score += 120;
  return score;
}

function nodeDepth(entityId: string, centerId: string, firstHop: Set<string>): number {
  if (entityId === centerId) return 0;
  if (firstHop.has(entityId) || props.selectedEntityIds.includes(entityId)) return 1;
  return 2;
}

function typeLabel(value: string): string {
  const labels: Record<string, string> = {
    insect: "昆虫",
    plant: "植物",
    habitat: "栖息地",
    season: "季节",
    behavior: "行为",
    concept: "概念",
  };
  return labels[value] || value || "未分类";
}

function shortLabel(value: string): string {
  return value.length > 5 ? `${value.slice(0, 5)}...` : value;
}

function isNodeSelected(entityId: string): boolean {
  return props.selectedEntityIds.includes(entityId);
}

function isEdgeSelected(relationId: string): boolean {
  if (props.selectedRelationId === relationId) return true;
  const selectedIds = new Set(props.selectedEntityIds);
  const relation = props.graph.relations.find((item) => item.id === relationId);
  return Boolean(relation && selectedIds.has(relation.subject_entity_id) && selectedIds.has(relation.object_entity_id));
}

function selectType(type: string) {
  selectedType.value = type;
  const first = rankedEntities.value.find((entity) => entity.entity_type === type);
  if (first) activateEntity(first.id);
}

function activateEntity(entityId: string) {
  localFocusedEntityId.value = entityId;
  emit("select-node", entityId);
}

function selectNode(entityId: string) {
  localFocusedEntityId.value = entityId;
  emit("select-node", entityId);
}

function selectRelation(relationId: string) {
  emit("select-relation", relationId);
}

function zoomBy(delta: number) {
  viewport.scale = Math.min(1.8, Math.max(0.65, viewport.scale + delta));
}

function resetViewport() {
  viewport.x = 0;
  viewport.y = 0;
  viewport.scale = 1;
}

function startPan(event: PointerEvent) {
  isDragging.value = true;
  dragStart.x = event.clientX;
  dragStart.y = event.clientY;
  dragStart.viewportX = viewport.x;
  dragStart.viewportY = viewport.y;
}

function movePan(event: PointerEvent) {
  if (!isDragging.value) return;
  viewport.x = dragStart.viewportX + event.clientX - dragStart.x;
  viewport.y = dragStart.viewportY + event.clientY - dragStart.y;
}

function endPan() {
  isDragging.value = false;
}

function onWheel(event: WheelEvent) {
  zoomBy(event.deltaY > 0 ? -0.08 : 0.08);
}
</script>
