<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <section class="graph-admin-modal" role="dialog" aria-modal="true" aria-labelledby="graph-admin-title">
      <header class="graph-admin-head">
        <div>
          <p class="section-kicker">管理员配置</p>
          <h2 id="graph-admin-title">知识图谱与节点 RAG</h2>
          <span>{{ graph.entities.length }} 个节点 · {{ graph.relations.length }} 条中文关系</span>
        </div>
        <button class="close-button" type="button" @click="$emit('close')">关闭</button>
      </header>
      <div class="graph-admin-layout">
        <aside class="graph-admin-nodes">
          <strong>选择节点</strong>
          <button
            v-for="entity in graph.entities"
            :key="entity.id"
            type="button"
            class="graph-admin-node"
            :class="{ active: entity.id === selectedEntityId }"
            @click="selectEntity(entity.id)"
          >
            <span>{{ entity.name }}</span>
            <small>{{ entity.rag_sources.length ? `${entity.rag_sources.length} 个知识库` : "未配置" }}</small>
          </button>
        </aside>
        <div class="graph-admin-visual">
          <svg viewBox="0 0 620 360" role="img" aria-label="知识图谱中文关系图">
            <line
              v-for="edge in edges"
              :key="edge.id"
              :x1="edge.x1"
              :y1="edge.y1"
              :x2="edge.x2"
              :y2="edge.y2"
              class="knowledge-edge"
            />
            <text v-for="edge in edges" :key="`${edge.id}-label`" :x="(edge.x1 + edge.x2) / 2" :y="(edge.y1 + edge.y2) / 2 - 5" class="knowledge-edge-label">
              {{ edge.label }}
            </text>
            <g v-for="node in nodes" :key="node.id" class="knowledge-node" :class="{ selected: node.id === selectedEntityId }">
              <circle :cx="node.x" :cy="node.y" r="27" />
              <text :x="node.x" :y="node.y + 4">{{ node.name }}</text>
            </g>
          </svg>
          <div v-if="selectedEntity" class="graph-admin-source-panel">
            <div class="graph-admin-source-title">
              <strong>{{ selectedEntity.name }}</strong>
              <span>绑定可检索知识库</span>
            </div>
            <label v-for="file in files" :key="file.source" class="graph-admin-source-option">
              <input v-model="draftSources" type="checkbox" :value="file.source" />
              <span>{{ file.source }}</span>
            </label>
            <p v-if="!files.length" class="graph-admin-empty">请先在课标知识库中上传文件。</p>
            <button class="primary-button" type="button" :disabled="saving" @click="saveSources">
              {{ saving ? "保存中…" : "保存节点配置" }}
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { CurriculumFileItem, KnowledgeGraphPayload } from "@/types";

const props = defineProps<{
  graph: KnowledgeGraphPayload;
  files: CurriculumFileItem[];
  saving: boolean;
}>();

const emit = defineEmits<{
  close: [];
  save: [entityId: string, sources: string[]];
}>();

const selectedEntityId = ref(props.graph.entities[0]?.id || "");
const draftSources = ref<string[]>([]);
const selectedEntity = computed(() => props.graph.entities.find((entity) => entity.id === selectedEntityId.value));

watch(selectedEntity, (entity) => {
  draftSources.value = [...(entity?.rag_sources || [])];
}, { immediate: true });

const nodes = computed(() => {
  const count = Math.max(props.graph.entities.length, 1);
  return props.graph.entities.map((entity, index) => {
    const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
    return { ...entity, x: 310 + Math.cos(angle) * 225, y: 180 + Math.sin(angle) * 125 };
  });
});

const nodeById = computed(() => new Map(nodes.value.map((node) => [node.id, node])));
const edges = computed(() => props.graph.relations.flatMap((relation) => {
  const source = nodeById.value.get(relation.subject_entity_id);
  const target = nodeById.value.get(relation.object_entity_id);
  if (!source || !target) return [];
  return [{ id: relation.id, x1: source.x, y1: source.y, x2: target.x, y2: target.y, label: relation.predicate_label || relation.predicate }];
}));

function selectEntity(entityId: string) {
  selectedEntityId.value = entityId;
}

function saveSources() {
  if (selectedEntityId.value) emit("save", selectedEntityId.value, [...draftSources.value]);
}
</script>
