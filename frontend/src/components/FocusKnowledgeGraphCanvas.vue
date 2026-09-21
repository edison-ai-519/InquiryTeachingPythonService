<template>
  <div class="focus-graph-shell" :class="{ dragging: isDragging, 'map-only': variant === 'map' }">
    <div v-if="variant === 'full'" class="graph-overview-strip">
      <button type="button" :class="{ active: selectedType === '' }" @click="selectedType = ''">全部 <strong>{{ graph.entities.length }}</strong></button>
      <button v-for="item in typeSummary" :key="item.type" type="button" :class="{ active: selectedType === item.type }" @click="selectType(item.type)">
        {{ typeLabel(item.type) }} <strong>{{ item.count }}</strong>
      </button>
    </div>

    <div class="graph-explorer-layout">
      <aside v-if="variant === 'full'" class="graph-node-catalog">
        <div class="graph-catalog-head"><strong>节点目录</strong><span>{{ filteredCatalogEntities.length }} 个</span></div>
        <input v-model.trim="searchText" class="input" placeholder="搜索节点" />
        <div class="graph-node-list">
          <button v-for="entity in filteredCatalogEntities" :key="entity.id" type="button" :class="{ selected: isNodeSelected(entity.id) }" @click="activateEntity(entity.id)">
            <span :title="entity.name">{{ entity.name }}</span>
            <small>{{ typeLabel(entity.entity_type) }} · {{ degreeByEntity.get(entity.id) || 0 }} 条关系</small>
          </button>
        </div>
      </aside>

      <section class="graph-map-pane">
        <div class="focus-graph-toolbar">
          <span>{{ selectionLabel }}</span>
          <div>
            <button type="button" @click="zoomBy(0.12)">放大</button>
            <button type="button" @click="zoomBy(-0.12)">缩小</button>
            <button type="button" @click="resetViewport">重置</button>
          </div>
        </div>
        <svg
          ref="svgRef"
          class="knowledge-graph-svg focus-graph-svg"
          :viewBox="`0 0 ${canvasSize.width} ${canvasSize.height}`"
          role="img"
          :aria-label="ariaLabel"
          @pointerdown="startPan"
          @pointermove="movePan"
          @pointerup="endPan"
          @pointercancel="endPan"
          @wheel.prevent="onWheel"
        >
          <defs>
            <marker :id="markerId" viewBox="0 0 6 6" refX="5.5" refY="3" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
              <path d="M 0 0 L 6 3 L 0 6 z" fill="context-stroke" />
            </marker>
          </defs>
          <g :transform="viewportTransform">
            <path
              v-for="edge in visibleEdges"
              :key="edge.id"
              :d="edge.path"
              :marker-end="`url(#${markerId})`"
              class="knowledge-edge"
              :class="{ selected: isRelationHighlighted(edge.id), 'no-filter': highlightedRelationCount > 12 }"
              @mouseenter="hoveredRelationId = edge.id"
              @mouseleave="hoveredRelationId = ''"
              @click.stop="selectRelation(edge.id)"
            />
            <g v-for="edge in labelledEdges" :key="`${edge.id}-label`" class="knowledge-edge-label" :class="{ selected: isRelationHighlighted(edge.id) }">
              <rect :x="edge.x - edge.width / 2" :y="edge.y - edge.height / 2" :width="edge.width" :height="edge.height" rx="4" />
              <text :x="edge.x" :y="edge.y + 4">{{ edge.label }}</text>
            </g>
            <g
              v-for="node in visibleNodes"
              :key="node.id"
              class="knowledge-node focus-graph-node"
              :class="[node.entity.entity_type, { selected: isNodeSelected(node.id), neighbor: isDirectNeighbor(node.id), muted: hasNodeSelection && !isNodeSelected(node.id) && !isDirectNeighbor(node.id) }]"
              @pointerdown.stop
              @click.stop="selectNode(node.id)"
              @dblclick.stop="$emit('focus-node', node.id)"
            >
              <circle :cx="node.x" :cy="node.y" :r="node.radius" />
              <circle v-if="node.id === expandingNodeId" class="knowledge-node-loading-ring" :cx="node.x" :cy="node.y" :r="node.radius + 6" />
              <text :x="node.x" :y="node.y + 4"><title>{{ node.entity.name }}</title>{{ shortLabel(node.entity.name) }}</text>
            </g>
          </g>
        </svg>
        <div class="focus-graph-hint">
          <span v-if="expanding">正在展开邻近节点...</span>
          <span v-else-if="graph.truncated">当前显示 {{ graph.entities.length }} 个节点、{{ graph.relations.length }} 条关系，可继续双击节点展开邻域</span>
          <span v-else-if="overflowCount">画布显示 {{ visibleNodes.length }} 个节点，另有 {{ overflowCount }} 个可在目录中查看</span>
          <span v-else-if="variant === 'map'">单击选择节点或关系，拖动画布查看局部结构</span>
          <span v-else>单击选择，双击展开；目录可查看全部节点</span>
        </div>
      </section>

      <aside v-if="variant === 'full'" class="graph-node-detail">
        <template v-if="activeEntity">
          <div class="graph-detail-title"><strong :title="activeEntity.name">{{ activeEntity.name }}</strong><span>{{ typeLabel(activeEntity.entity_type) }}</span></div>
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
import { computed, getCurrentInstance, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from "vue";
import { buildInitialGraphPositions, graphLayoutProfile, placeExpandedGraphPositions, toViewportPoint, type GraphLayoutPosition } from "@/lib/knowledgeGraphLayout";
import { buildCurvedEdge, placeRelationLabels } from "@/lib/knowledgeGraphGeometry";
import type { KnowledgeEntity, KnowledgeGraphPayload } from "@/types";

type VisibleNode = { id: string; entity: KnowledgeEntity; x: number; y: number; radius: number };
type GraphExpansion = { sourceId: string; addedEntityIds: string[]; revision: number };

const props = withDefaults(defineProps<{
  graph: KnowledgeGraphPayload;
  selectedEntityIds?: string[];
  selectedRelationId?: string;
  expanding?: boolean;
  expandingNodeId?: string;
  ariaLabel?: string;
  maxNodes?: number;
  variant?: "full" | "map";
  fullscreen?: boolean;
  layoutRevision?: number;
  expansion?: GraphExpansion | null;
}>(), {
  selectedEntityIds: () => [], selectedRelationId: "", expanding: false, expandingNodeId: "", ariaLabel: "知识图谱探索视图", maxNodes: 18, variant: "full", fullscreen: false, layoutRevision: 0, expansion: null,
});

const emit = defineEmits<{ "select-node": [entityId: string]; "focus-node": [entityId: string]; "select-relation": [relationId: string] }>();
const svgRef = ref<SVGSVGElement | null>(null);
const canvasSize = reactive({ width: 620, height: 380 });
const viewport = reactive({ x: 0, y: 0, scale: 1 });
const isDragging = ref(false);
const dragStart = reactive({ x: 0, y: 0, viewportX: 0, viewportY: 0 });
const selectedType = ref("");
const searchText = ref("");
const hoveredRelationId = ref("");
const positionCache = shallowRef<Map<string, GraphLayoutPosition>>(new Map());
const markerId = `knowledge-graph-arrow-${getCurrentInstance()?.uid || "canvas"}`;
let resizeObserver: ResizeObserver | null = null;
let pendingViewport: { x: number; y: number; scale: number } | null = null;
let viewportFrame = 0;
let activePointerId: number | null = null;
let panMoved = false;
let suppressClick = false;
let appliedLayoutRevision = -1;
let appliedProfile = "";

const layoutProfile = computed(() => graphLayoutProfile(canvasSize.width, canvasSize.height, props.variant, props.fullscreen));
const entitySignature = computed(() => props.graph.entities.map((entity) => entity.id).sort().join("|"));
const relationSignature = computed(() => props.graph.relations.map((relation) => relation.id).sort().join("|"));
const entityById = computed(() => new Map(props.graph.entities.map((entity) => [entity.id, entity])));
const selectedEntityIdSet = computed(() => new Set(props.selectedEntityIds));
const recommendedRelationIds = computed(() => new Set(props.graph.paths.filter((path) => props.graph.recommended_path_ids.includes(path.id)).flatMap((path) => path.relation_ids)));
const layoutFocusId = computed(() => {
  const selectedId = [...props.selectedEntityIds].reverse().find((id) => entityById.value.has(id));
  return selectedId || props.expandingNodeId || props.graph.anchor_entity_ids?.find((id) => entityById.value.has(id)) || "";
});
watch([entitySignature, relationSignature, layoutProfile, () => props.layoutRevision, () => props.expansion], syncPositionCache, { immediate: true });

const degreeByEntity = computed(() => {
  const map = new Map<string, number>();
  for (const entity of props.graph.entities) map.set(entity.id, 0);
  for (const relation of props.graph.relations) {
    map.set(relation.subject_entity_id, (map.get(relation.subject_entity_id) || 0) + 1);
    map.set(relation.object_entity_id, (map.get(relation.object_entity_id) || 0) + 1);
  }
  return map;
});
const typeSummary = computed(() => {
  const counts = new Map<string, number>();
  for (const entity of props.graph.entities) counts.set(entity.entity_type, (counts.get(entity.entity_type) || 0) + 1);
  return Array.from(counts.entries()).map(([type, count]) => ({ type, count })).sort((a, b) => b.count - a.count || typeLabel(a.type).localeCompare(typeLabel(b.type), "zh-Hans-CN"));
});
const activeEntity = computed(() => {
  const selectedId = [...props.selectedEntityIds].reverse().find((id) => entityById.value.has(id));
  return selectedId ? entityById.value.get(selectedId) || null : null;
});
const selectionLabel = computed(() => activeEntity.value ? `已选：${activeEntity.value.name}` : "完整图谱");
const rankedEntities = computed(() => {
  const recommendedEntityIds = new Set<string>();
  for (const relation of props.graph.relations) {
    if (!recommendedRelationIds.value.has(relation.id)) continue;
    recommendedEntityIds.add(relation.subject_entity_id);
    recommendedEntityIds.add(relation.object_entity_id);
  }
  const selected = new Set(props.selectedEntityIds);
  return [...props.graph.entities].sort((a, b) => entityScore(b, recommendedEntityIds, selected) - entityScore(a, recommendedEntityIds, selected) || a.name.localeCompare(b.name, "zh-Hans-CN"));
});
const filteredCatalogEntities = computed(() => rankedEntities.value.filter(matchesCatalogFilter));
const visibleLayoutEntities = computed(() => [...props.graph.entities].sort((a, b) => a.name.localeCompare(b.name, "zh-Hans-CN") || a.id.localeCompare(b.id, "zh-Hans-CN")).filter(matchesCatalogFilter).slice(0, props.maxNodes));
const nodeRadius = computed(() => Math.max(14, Math.min(23, Math.floor(Math.min(canvasSize.width, canvasSize.height) / 17))));
const visibleNodes = computed<VisibleNode[]>(() => visibleLayoutEntities.value.flatMap((entity) => {
  const position = positionCache.value.get(entity.id);
  if (!position) return [];
  const point = toViewportPoint(position, canvasSize.width, canvasSize.height);
  return [{ id: entity.id, entity, x: point.x, y: point.y, radius: nodeRadius.value }];
}));
const visibleNodeById = computed(() => new Map(visibleNodes.value.map((node) => [node.id, node])));
const overflowCount = computed(() => Math.max(0, props.graph.entities.length - visibleNodes.value.length));
const adjacencyByEntity = computed(() => {
  const adjacency = new Map<string, Set<string>>();
  for (const entity of props.graph.entities) adjacency.set(entity.id, new Set());
  for (const relation of props.graph.relations) {
    if (relation.subject_entity_id === relation.object_entity_id) continue;
    adjacency.get(relation.subject_entity_id)?.add(relation.object_entity_id);
    adjacency.get(relation.object_entity_id)?.add(relation.subject_entity_id);
  }
  return adjacency;
});
const hasNodeSelection = computed(() => props.selectedEntityIds.length > 0);
const directNeighborIds = computed(() => {
  const selectedId = activeEntity.value?.id;
  return selectedId ? adjacencyByEntity.value.get(selectedId) || new Set<string>() : new Set<string>();
});
const visibleEdges = computed(() => {
  const relations = props.graph.relations
    .filter((relation) => visibleNodeById.value.has(relation.subject_entity_id) && visibleNodeById.value.has(relation.object_entity_id) && relation.subject_entity_id !== relation.object_entity_id)
    .sort((left, right) => left.id.localeCompare(right.id));
  const pairCounts = new Map<string, number>();
  for (const relation of relations) {
    const key = [relation.subject_entity_id, relation.object_entity_id].sort().join("|");
    pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
  }
  const pairOffsets = new Map<string, number>();
  return relations.map((relation) => {
    const source = visibleNodeById.value.get(relation.subject_entity_id)!;
    const target = visibleNodeById.value.get(relation.object_entity_id)!;
    const key = [relation.subject_entity_id, relation.object_entity_id].sort().join("|");
    const offset = pairOffsets.get(key) || 0;
    pairOffsets.set(key, offset + 1);
    const lane = offset - ((pairCounts.get(key) || 1) - 1) / 2;
    return {
      id: relation.id,
      label: relationDisplayLabel(relation.predicate_label || relation.predicate),
      ...buildCurvedEdge({ id: relation.id, source, target, lane }),
    };
  });
});
const highlightedRelationIds = computed(() => new Set(props.graph.relations.flatMap((relation) => {
  if (props.selectedRelationId === relation.id || selectedEntityIdSet.value.has(relation.subject_entity_id) || selectedEntityIdSet.value.has(relation.object_entity_id)) return [relation.id];
  return [];
})));
const highlightedRelationCount = computed(() => highlightedRelationIds.value.size);
const labelledEdges = computed(() => {
  const labelled = visibleEdges.value.filter((edge) => visibleEdges.value.length <= 10 || isRelationHighlighted(edge.id) || edge.id === hoveredRelationId.value);
  const placements = new Map(placeRelationLabels(labelled.map((edge) => ({
    id: edge.id,
    label: edge.label,
    x: edge.labelX,
    y: edge.labelY,
    normalX: edge.normalX,
    normalY: edge.normalY,
  }))).map((placement) => [placement.id, placement]));
  return labelled.flatMap((edge) => {
    const placement = placements.get(edge.id);
    return placement ? [{ ...edge, ...placement }] : [];
  });
});
const viewportTransform = computed(() => `translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`);

onMounted(() => {
  if (!svgRef.value || typeof ResizeObserver === "undefined") return;
  resizeObserver = new ResizeObserver(([entry]) => {
    if (!entry?.contentRect.width || !entry.contentRect.height) return;
    canvasSize.width = Math.max(280, Math.round(entry.contentRect.width));
    canvasSize.height = Math.max(220, Math.round(entry.contentRect.height));
  });
  resizeObserver.observe(svgRef.value);
});
onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  if (viewportFrame) cancelAnimationFrame(viewportFrame);
});

function syncPositionCache() {
  const entities = props.graph.entities;
  if (!entities.length) {
    positionCache.value = new Map();
    return;
  }
  if (appliedLayoutRevision !== props.layoutRevision || appliedProfile !== layoutProfile.value || !positionCache.value.size) {
    positionCache.value = buildInitialGraphPositions(entities, layoutProfile.value, props.graph.relations, layoutFocusId.value);
    appliedLayoutRevision = props.layoutRevision;
    appliedProfile = layoutProfile.value;
    return;
  }
  const existing = new Map(positionCache.value);
  const missing = entities.filter((entity) => !existing.has(entity.id));
  if (!missing.length) return;
  const expansion = props.expansion;
  if (expansion?.addedEntityIds.length && existing.has(expansion.sourceId)) {
    const addedIds = new Set(expansion.addedEntityIds);
    const additions = missing.filter((entity) => addedIds.has(entity.id));
    if (additions.length === missing.length) {
      positionCache.value = placeExpandedGraphPositions(existing, expansion.sourceId, additions, layoutProfile.value);
      return;
    }
  }
  positionCache.value = buildInitialGraphPositions(entities, layoutProfile.value, props.graph.relations, layoutFocusId.value);
}
function entityScore(entity: KnowledgeEntity, recommendedEntityIds: Set<string>, selectedIds: Set<string>): number {
  let score = degreeByEntity.value.get(entity.id) || 0;
  if (selectedIds.has(entity.id)) score += 800;
  if (recommendedEntityIds.has(entity.id)) score += 120;
  return score;
}
function typeLabel(value: string): string {
  const labels: Record<string, string> = { insect: "昆虫", plant: "植物", habitat: "栖息地", season: "季节", behavior: "行为", concept: "概念" };
  return labels[value] || value || "未分类";
}
function relationDisplayLabel(value: string): string {
  const labels: Record<string, string> = {
    uses_habitat: "栖息于",
    located_in: "位于",
    feeds_on: "取食",
    eats: "取食",
    performs: "进行",
    affects: "影响",
  };
  return labels[value] || value || "关联";
}
function shortLabel(value: string): string {
  const limit = nodeRadius.value >= 20 ? 6 : 4;
  return value.length > limit ? `${value.slice(0, limit)}...` : value;
}
function isNodeSelected(entityId: string): boolean { return props.selectedEntityIds.includes(entityId); }
function isDirectNeighbor(entityId: string): boolean { return directNeighborIds.value.has(entityId); }
function isRelationHighlighted(relationId: string): boolean {
  return highlightedRelationIds.value.has(relationId);
}
function selectType(type: string) { selectedType.value = type; }
function activateEntity(entityId: string) { emit("select-node", entityId); }
function selectNode(entityId: string) {
  if (suppressClick) { suppressClick = false; return; }
  emit("select-node", entityId);
}
function matchesCatalogFilter(entity: KnowledgeEntity): boolean {
  const keyword = searchText.value.toLowerCase();
  const matchesType = !selectedType.value || entity.entity_type === selectedType.value;
  const haystack = `${entity.name} ${entity.id} ${entity.entity_type} ${entity.aliases.join(" ")}`.toLowerCase();
  return matchesType && (!keyword || haystack.includes(keyword));
}
function selectRelation(relationId: string) {
  if (suppressClick) { suppressClick = false; return; }
  emit("select-relation", relationId);
}
function zoomBy(delta: number) { applyZoomAt(canvasSize.width / 2, canvasSize.height / 2, delta); }
function resetViewport() { scheduleViewport({ x: 0, y: 0, scale: 1 }); }
function startPan(event: PointerEvent) {
  if (event.button !== 0) return;
  activePointerId = event.pointerId;
  panMoved = false;
  isDragging.value = true;
  dragStart.x = event.clientX;
  dragStart.y = event.clientY;
  dragStart.viewportX = viewport.x;
  dragStart.viewportY = viewport.y;
  svgRef.value?.setPointerCapture(event.pointerId);
}
function movePan(event: PointerEvent) {
  if (!isDragging.value || activePointerId !== event.pointerId || !svgRef.value) return;
  const rect = svgRef.value.getBoundingClientRect();
  const dx = (event.clientX - dragStart.x) * (canvasSize.width / rect.width);
  const dy = (event.clientY - dragStart.y) * (canvasSize.height / rect.height);
  if (Math.hypot(dx, dy) > 5) panMoved = true;
  scheduleViewport({ x: dragStart.viewportX + dx, y: dragStart.viewportY + dy, scale: viewport.scale });
}
function endPan(event: PointerEvent) {
  if (activePointerId !== event.pointerId) return;
  if (svgRef.value?.hasPointerCapture(event.pointerId)) svgRef.value.releasePointerCapture(event.pointerId);
  suppressClick = panMoved;
  activePointerId = null;
  isDragging.value = false;
}
function onWheel(event: WheelEvent) {
  const point = eventPoint(event);
  applyZoomAt(point.x, point.y, event.deltaY > 0 ? -0.08 : 0.08);
}
function eventPoint(event: MouseEvent): { x: number; y: number } {
  const rect = svgRef.value?.getBoundingClientRect();
  if (!rect) return { x: canvasSize.width / 2, y: canvasSize.height / 2 };
  return { x: (event.clientX - rect.left) * (canvasSize.width / rect.width), y: (event.clientY - rect.top) * (canvasSize.height / rect.height) };
}
function applyZoomAt(x: number, y: number, delta: number) {
  const current = pendingViewport || viewport;
  const nextScale = Math.min(2, Math.max(0.6, current.scale + delta));
  if (nextScale === current.scale) return;
  const worldX = (x - current.x) / current.scale;
  const worldY = (y - current.y) / current.scale;
  scheduleViewport({ x: x - worldX * nextScale, y: y - worldY * nextScale, scale: nextScale });
}
function scheduleViewport(next: { x: number; y: number; scale: number }) {
  pendingViewport = clampViewport(next);
  if (viewportFrame) return;
  viewportFrame = requestAnimationFrame(() => {
    viewportFrame = 0;
    if (!pendingViewport) return;
    Object.assign(viewport, pendingViewport);
    pendingViewport = null;
  });
}
function clampViewport(next: { x: number; y: number; scale: number }) {
  const horizontalLimit = canvasSize.width * Math.max(0.18, next.scale * 0.78);
  const verticalLimit = canvasSize.height * Math.max(0.18, next.scale * 0.78);
  return { x: Math.min(horizontalLimit, Math.max(-horizontalLimit, next.x)), y: Math.min(verticalLimit, Math.max(-verticalLimit, next.y)), scale: next.scale };
}
</script>
