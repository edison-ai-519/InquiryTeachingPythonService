<template>
  <section class="full-graph-view">
    <div class="full-graph-toolbar">
      <label class="graph-search">
        <Search :size="15" />
        <input v-model.trim="searchText" type="search" placeholder="搜索节点名称或别名" />
      </label>
      <select v-model="entityType" aria-label="实体类型筛选">
        <option value="">全部节点类型</option>
        <option v-for="item in entityTypeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-model="predicate" aria-label="关系类型筛选">
        <option value="">全部关系类型</option>
        <option v-for="item in predicateOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-model="relationState" aria-label="关系状态筛选">
        <option value="">全部证据状态</option>
        <option value="verified">证据完整</option>
        <option value="unverified">待补证</option>
        <option value="suppressed">已屏蔽</option>
      </select>
      <select v-model="managementMode" aria-label="管理方式筛选">
        <option value="">全部管理方式</option>
        <option value="manual">手工</option>
        <option value="auto">自动</option>
        <option value="manual_override">手工覆盖</option>
      </select>
      <button type="button" @click="fitGraph"><ScanSearch :size="15" />适应画布</button>
      <button type="button" @click="runLayout"><RefreshCw :size="15" />重新布局</button>
    </div>

    <div class="full-graph-summary">
      <span>当前显示 {{ visibleEntities.length }} / {{ graph.entities.length }} 个节点 · {{ visibleRelations.length }} / {{ graph.relations.length }} 条关系</span>
      <div class="graph-legend">
        <i class="insect"></i>昆虫
        <i class="plant"></i>植物
        <i class="habitat"></i>栖息地
        <i class="season"></i>季节
        <i class="concept"></i>概念
        <b class="verified"></b>已验证
        <b class="unverified"></b>待补证
        <b class="suppressed"></b>已屏蔽
      </div>
    </div>

    <div class="full-graph-content">
      <div class="graph-canvas-wrap">
        <div ref="containerRef" class="graph-canvas" aria-label="全量知识图谱交互画布"></div>
        <div v-if="!visibleEntities.length" class="graph-canvas-empty">当前筛选条件下没有可展示的节点</div>
      </div>

      <aside class="graph-inspector">
        <template v-if="selectedEntity">
          <p class="section-kicker">节点详情</p>
          <h3>{{ selectedEntity.name }}</h3>
          <div class="inspector-tags">
            <span>{{ entityTypeLabel(selectedEntity.entity_type) }}</span>
            <span>{{ entityOriginLabel(selectedEntity) }}</span>
            <span>{{ selectedEntity.mention_count }} 个片段</span>
          </div>
          <p>{{ selectedEntity.description || "暂无节点说明" }}</p>
          <dl>
            <div><dt>别名</dt><dd>{{ selectedEntity.aliases.join("、") || "无" }}</dd></div>
            <div><dt>分类标识</dt><dd>{{ selectedEntity.taxa?.map((item) => item.external_id).join("、") || "无" }}</dd></div>
            <div><dt>知识文件</dt><dd>{{ selectedEntity.rag_sources.join("、") || "未绑定" }}</dd></div>
          </dl>
          <button class="primary-button" type="button" @click="$emit('edit-entity', selectedEntity.id)">编辑节点</button>
        </template>
        <template v-else-if="selectedRelation">
          <p class="section-kicker">关系详情</p>
          <h3>{{ entityName(selectedRelation.subject_entity_id) }} → {{ entityName(selectedRelation.object_entity_id) }}</h3>
          <div class="inspector-tags">
            <span>{{ selectedRelation.predicate_label || selectedRelation.predicate }}</span>
            <span>{{ evidenceLabel(selectedRelation) }}</span>
            <span>{{ managementLabel(selectedRelation) }}</span>
          </div>
          <p>{{ selectedRelation.description || "暂无关系说明" }}</p>
          <dl>
            <div><dt>置信度</dt><dd>{{ confidenceLabel(selectedRelation.confidence) }}</dd></div>
            <div><dt>本地证据片段</dt><dd>{{ selectedRelation.evidence.length }} 个</dd></div>
            <div><dt>GloBI 证据</dt><dd>{{ selectedRelation.globi_evidence_count || 0 }} 条</dd></div>
            <div><dt>地域范围</dt><dd>{{ selectedRelation.global_only ? "全球关系（非本地观察）" : selectedRelation.geographic_scope }}</dd></div>
            <div><dt>提取模型</dt><dd>{{ selectedRelation.extractor_model || "—" }}</dd></div>
          </dl>
          <button class="primary-button" type="button" @click="$emit('edit-relation', selectedRelation.id)">编辑关系与证据</button>
        </template>
        <div v-else class="inspector-empty">
          <MousePointer2 :size="24" />
          <strong>选择图谱元素</strong>
          <span>点击节点或关系查看详情，并可跳转到对应管理表单。</span>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { MousePointer2, RefreshCw, ScanSearch, Search } from "lucide-vue-next";
import type { KnowledgeEntity, KnowledgeGraphPayload, KnowledgeRelation } from "@/types";

const props = defineProps<{ graph: KnowledgeGraphPayload }>();

defineEmits<{
  "edit-entity": [entityId: string];
  "edit-relation": [relationId: string];
}>();

const containerRef = ref<HTMLElement | null>(null);
const searchText = ref("");
const entityType = ref("");
const predicate = ref("");
const relationState = ref("");
const managementMode = ref("");
const selectedKind = ref<"entity" | "relation" | "">("");
const selectedId = ref("");
let graphCore: Core | null = null;
let resizeObserver: ResizeObserver | null = null;

const entityTypeOptions = [
  { value: "insect", label: "昆虫" },
  { value: "plant", label: "植物" },
  { value: "habitat", label: "栖息地" },
  { value: "season", label: "季节" },
  { value: "behavior", label: "行为" },
  { value: "concept", label: "概念" },
];

const predicateOptions = computed(() => {
  const seen = new Map<string, string>();
  for (const relation of props.graph.relations) {
    seen.set(relation.predicate, relation.predicate_label || relation.predicate);
  }
  return Array.from(seen, ([value, label]) => ({ value, label })).sort((left, right) => left.label.localeCompare(right.label, "zh-CN"));
});

function relationManagementValue(relation: KnowledgeRelation): "manual" | "auto" | "manual_override" {
  if (relation.management_mode === "manual_override") return "manual_override";
  if (["lightrag", "globi"].includes(relation.origin)) return "auto";
  return "manual";
}

function relationMatches(relation: KnowledgeRelation): boolean {
  if (predicate.value && relation.predicate !== predicate.value) return false;
  if (managementMode.value && relationManagementValue(relation) !== managementMode.value) return false;
  if (relationState.value === "suppressed") return relation.status === "suppressed";
  if (relationState.value === "verified") return relation.status !== "suppressed" && relation.evidence_status === "verified";
  if (relationState.value === "unverified") return relation.status !== "suppressed" && relation.evidence_status === "unverified";
  return true;
}

const visibleEntities = computed(() => {
  const query = searchText.value.trim().toLocaleLowerCase("zh-CN");
  const directIds = new Set(
    props.graph.entities
      .filter((entity) => !entityType.value || entity.entity_type === entityType.value)
      .filter((entity) => !query || [
        entity.name,
        ...entity.aliases,
        ...(entity.taxa || []).flatMap((item) => [item.scientific_name, item.external_id, ...item.common_names]),
      ].some((name) => name.toLocaleLowerCase("zh-CN").includes(query)))
      .map((entity) => entity.id),
  );
  if (!query) return props.graph.entities.filter((entity) => directIds.has(entity.id));
  const contextualIds = new Set(directIds);
  for (const relation of props.graph.relations) {
    if (!relationMatches(relation)) continue;
    if (directIds.has(relation.subject_entity_id) || directIds.has(relation.object_entity_id)) {
      for (const entityId of [relation.subject_entity_id, relation.object_entity_id]) {
        const entity = props.graph.entities.find((item) => item.id === entityId);
        if (entity && (!entityType.value || entity.entity_type === entityType.value)) {
          contextualIds.add(entityId);
        }
      }
    }
  }
  return props.graph.entities.filter((entity) => contextualIds.has(entity.id));
});

const visibleEntityIds = computed(() => new Set(visibleEntities.value.map((entity) => entity.id)));
const visibleRelations = computed(() => props.graph.relations.filter((relation) =>
  visibleEntityIds.value.has(relation.subject_entity_id)
  && visibleEntityIds.value.has(relation.object_entity_id)
  && relationMatches(relation),
));

const selectedEntity = computed(() => selectedKind.value === "entity"
  ? props.graph.entities.find((entity) => entity.id === selectedId.value) || null
  : null,
);
const selectedRelation = computed(() => selectedKind.value === "relation"
  ? props.graph.relations.find((relation) => relation.id === selectedId.value) || null
  : null,
);

function graphElements(): ElementDefinition[] {
  return [
    ...visibleEntities.value.map((entity) => ({
      data: { id: entity.id, label: entity.name },
      classes: `entity-${entity.entity_type} origin-${entity.origin}`,
    })),
    ...visibleRelations.value.map((relation) => ({
      data: {
        id: relation.id,
        source: relation.subject_entity_id,
        target: relation.object_entity_id,
        label: relation.predicate_label || relation.predicate,
      },
      classes: [
        relation.status === "suppressed" ? "relation-suppressed" : `relation-${relation.evidence_status}`,
        `management-${relationManagementValue(relation)}`,
      ].join(" "),
    })),
  ];
}

function createGraph(): void {
  if (!containerRef.value) return;
  graphCore?.destroy();
  graphCore = cytoscape({
    container: containerRef.value,
    elements: graphElements(),
    minZoom: 0.15,
    maxZoom: 3,
    wheelSensitivity: 0.22,
    style: [
      { selector: "node", style: { "background-color": "#77664a", label: "data(label)", color: "#26342d", "font-size": 11, "font-weight": "bold", "text-valign": "bottom", "text-margin-y": 7, width: 34, height: 34, "border-width": 2, "border-color": "#ffffff", "text-wrap": "wrap", "text-max-width": "88px" } },
      { selector: ".entity-insect", style: { "background-color": "#198f86" } },
      { selector: ".entity-plant", style: { "background-color": "#5c9829" } },
      { selector: ".entity-habitat", style: { "background-color": "#bb7b2b" } },
      { selector: ".entity-season", style: { "background-color": "#5b78b8" } },
      { selector: ".entity-behavior", style: { "background-color": "#b55f87" } },
      { selector: ".entity-concept", style: { "background-color": "#7c57b7" } },
      { selector: "edge", style: { width: 1.7, "line-color": "#7f9288", "target-arrow-color": "#7f9288", "target-arrow-shape": "triangle", "curve-style": "bezier", label: "data(label)", color: "#52635a", "font-size": 9, "text-background-color": "#f6f8f6", "text-background-opacity": 0.86, "text-background-padding": "2px", "text-rotation": "autorotate" } },
      { selector: ".relation-unverified", style: { "line-style": "dashed", "line-color": "#c38a31", "target-arrow-color": "#c38a31" } },
      { selector: ".relation-suppressed", style: { "line-style": "dashed", "line-color": "#bb5555", "target-arrow-color": "#bb5555", opacity: 0.48 } },
      { selector: ".management-manual_override", style: { width: 3 } },
      { selector: ":selected", style: { "overlay-color": "#d0a339", "overlay-opacity": 0.18, "overlay-padding": 7, "border-color": "#9a7214", "line-color": "#9a7214", "target-arrow-color": "#9a7214" } },
      { selector: ".dimmed", style: { opacity: 0.14 } },
    ],
  });
  graphCore.on("tap", "node", (event) => {
    selectedKind.value = "entity";
    selectedId.value = event.target.id();
    focusElement(event.target.id());
  });
  graphCore.on("tap", "edge", (event) => {
    selectedKind.value = "relation";
    selectedId.value = event.target.id();
    focusElement(event.target.id());
  });
  graphCore.on("tap", (event) => {
    if (event.target === graphCore) {
      selectedKind.value = "";
      selectedId.value = "";
      graphCore?.elements().removeClass("dimmed");
    }
  });
  runLayout();
}

function focusElement(id: string): void {
  if (!graphCore) return;
  const element = graphCore.getElementById(id);
  graphCore.elements().addClass("dimmed");
  element.closedNeighborhood().removeClass("dimmed");
  element.select();
}

function runLayout(): void {
  if (!graphCore || !graphCore.elements().length) return;
  graphCore.layout({
    name: "cose",
    animate: false,
    fit: true,
    padding: 36,
    idealEdgeLength: 90,
    nodeRepulsion: 8000,
    nodeOverlap: 18,
  }).run();
}

function fitGraph(): void {
  graphCore?.fit(undefined, 36);
}

function entityName(entityId: string): string {
  return props.graph.entities.find((entity) => entity.id === entityId)?.name || entityId;
}

function entityTypeLabel(type: string): string {
  return entityTypeOptions.find((item) => item.value === type)?.label || type;
}

function evidenceLabel(relation: KnowledgeRelation): string {
  if (relation.status === "suppressed") return "已屏蔽";
  if (relation.global_only) return "GloBI 全球证据";
  if (relation.geographic_scope === "mixed") return "本地 + GloBI 证据";
  return relation.evidence_status === "verified" ? "证据完整" : "待补证";
}

function entityOriginLabel(entity: KnowledgeEntity): string {
  if (entity.origin === "lightrag") return "LightRAG 自动";
  if (entity.origin === "globi") return "GloBI 自动";
  return "手工创建";
}

function managementLabel(relation: KnowledgeRelation): string {
  return ({ manual: "手工", auto: "自动", manual_override: "手工覆盖" })[relationManagementValue(relation)];
}

function confidenceLabel(confidence: string): string {
  return ({ high: "高", medium: "中", low: "低" } as Record<string, string>)[confidence] || confidence;
}

watch(
  [() => props.graph, searchText, entityType, predicate, relationState, managementMode],
  async () => {
    await nextTick();
    createGraph();
  },
  { deep: true },
);

onMounted(() => {
  createGraph();
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => graphCore?.resize());
    resizeObserver.observe(containerRef.value);
  }
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  graphCore?.destroy();
  graphCore = null;
});
</script>

<style scoped>
.full-graph-view{display:flex;min-height:0;flex:1;flex-direction:column;gap:10px;padding:12px 20px 20px}.full-graph-toolbar{display:flex;flex-wrap:wrap;gap:7px;align-items:center}.full-graph-toolbar select,.full-graph-toolbar button,.graph-search{min-height:34px;border:1px solid var(--border-default,rgba(128,128,128,.24));border-radius:8px;color:var(--text-secondary,inherit);background:var(--surface,#fff);font-size:11px}.full-graph-toolbar select{width:auto!important;min-width:126px;padding:0 8px}.full-graph-toolbar button{display:inline-flex;align-items:center;gap:5px;padding:0 10px}.graph-search{display:grid;grid-template-columns:auto minmax(130px,1fr);align-items:center;gap:6px;flex:1;min-width:190px;padding:0 10px}.graph-search input{min-width:0;border:0;outline:0;color:var(--text-primary,inherit);background:transparent;font:inherit}.full-graph-summary{display:flex;align-items:center;justify-content:space-between;gap:12px;color:var(--text-muted,#66756d);font-size:10px}.graph-legend{display:flex;flex-wrap:wrap;align-items:center;gap:5px}.graph-legend i{width:9px;height:9px;border-radius:50%}.graph-legend i.insect{background:#198f86}.graph-legend i.plant{background:#5c9829}.graph-legend i.habitat{background:#bb7b2b}.graph-legend i.season{background:#5b78b8}.graph-legend i.concept{background:#7c57b7}.graph-legend b{width:18px;height:0;border-top:2px solid #7f9288}.graph-legend b.unverified{border-top-style:dashed;border-color:#c38a31}.graph-legend b.suppressed{border-top-style:dashed;border-color:#bb5555}.full-graph-content{display:grid;grid-template-columns:minmax(0,1fr) 250px;min-height:480px;flex:1;border:1px solid var(--border-default,rgba(128,128,128,.22));border-radius:12px;overflow:hidden}.graph-canvas-wrap{position:relative;min-width:0;background:linear-gradient(135deg,rgba(245,248,245,.96),rgba(235,241,237,.86))}.graph-canvas{position:absolute;inset:0}.graph-canvas-empty{position:absolute;inset:0;display:grid;place-items:center;color:var(--text-muted,#66756d);font-size:12px;pointer-events:none}.graph-inspector{min-width:0;padding:16px;border-left:1px solid var(--border-default,rgba(128,128,128,.22));background:var(--surface,#fff);overflow:auto}.graph-inspector h3{margin:3px 0 10px;color:var(--text-primary,#26342d);font-size:15px}.graph-inspector>p:not(.section-kicker){color:var(--text-secondary,#53645b);font-size:11px;line-height:1.6}.inspector-tags{display:flex;flex-wrap:wrap;gap:5px}.inspector-tags span{padding:3px 6px;border-radius:999px;color:#287456;background:rgba(62,138,104,.12);font-size:9px}.graph-inspector dl{display:grid;gap:8px;margin:14px 0}.graph-inspector dl div{display:grid;gap:3px}.graph-inspector dt{color:var(--text-muted,#66756d);font-size:9px}.graph-inspector dd{margin:0;color:var(--text-primary,#26342d);font-size:10px;line-height:1.5;overflow-wrap:anywhere}.graph-inspector .primary-button{width:100%;min-height:34px}.inspector-empty{display:grid;place-items:center;align-content:center;gap:7px;height:100%;min-height:240px;color:var(--text-muted,#66756d);text-align:center}.inspector-empty strong{color:var(--text-primary,#26342d);font-size:12px}.inspector-empty span{max-width:180px;font-size:10px;line-height:1.5}.section-kicker{margin:0;color:#287456;font-size:9px;font-weight:700;letter-spacing:.08em}@media(max-width:820px){.full-graph-toolbar select{width:100%!important}.full-graph-content{grid-template-columns:1fr}.graph-canvas-wrap{min-height:410px}.graph-inspector{border-top:1px solid var(--border-default,rgba(128,128,128,.22));border-left:0}.full-graph-summary{align-items:flex-start;flex-direction:column}}
</style>
