<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <section class="graph-admin-modal graph-admin-workbench" role="dialog" aria-modal="true" aria-labelledby="graph-admin-title">
      <header class="graph-admin-head">
        <div>
          <p class="section-kicker">管理员配置</p>
          <h2 id="graph-admin-title">知识图谱与证据连接</h2>
          <span>{{ graph.entities.length }} 个节点 · {{ graph.relations.length }} 条关系</span>
        </div>
        <div class="head-actions">
          <button type="button" :disabled="busy" @click="rebuildMentions">重建片段连接</button>
          <button class="close-button" type="button" @click="$emit('close')">关闭</button>
        </div>
      </header>

      <p v-if="error" class="graph-admin-error">{{ error }}</p>
      <div class="graph-admin-tabs">
        <button type="button" :class="{ active: tab === 'entities' }" @click="tab = 'entities'">节点管理</button>
        <button type="button" :class="{ active: tab === 'relations' }" @click="tab = 'relations'">关系与证据</button>
      </div>

      <div v-if="tab === 'entities'" class="admin-grid">
        <aside class="admin-list">
          <button type="button" class="list-create" @click="newEntity">＋ 新建节点</button>
          <button
            v-for="entity in graph.entities"
            :key="entity.id"
            type="button"
            :class="{ active: entity.id === editingEntityId }"
            @click="editEntity(entity)"
          >
            <span>{{ entity.name }}</span>
            <small>{{ entityTypeLabel(entity.entity_type) }} · {{ entity.mention_count || 0 }} 个片段</small>
          </button>
        </aside>

        <form class="admin-form" @submit.prevent="saveEntity">
          <label>名称<input v-model.trim="entityForm.name" required maxlength="128" /></label>
          <label>类型
            <select v-model="entityForm.entity_type">
              <option value="insect">昆虫</option>
              <option value="plant">植物</option>
              <option value="habitat">栖息地</option>
              <option value="season">季节</option>
              <option value="concept">概念</option>
            </select>
          </label>
          <label>别名<input v-model="entityAliases" placeholder="多个别名用逗号分隔" /></label>
          <label>说明<textarea v-model.trim="entityForm.description" rows="3" /></label>
          <fieldset v-if="editingEntityId">
            <legend>节点关联知识文件</legend>
            <label v-for="file in files" :key="file.source" class="check-row">
              <input v-model="entitySources" type="checkbox" :value="file.source" />
              <span>{{ file.source }}</span>
              <small>{{ knowledgeCategoryLabel(file.category) }}</small>
            </label>
            <p v-if="!files.length" class="muted">请先在知识库中上传文件。</p>
          </fieldset>
          <div class="form-actions">
            <button class="primary-button" type="submit" :disabled="busy || !entityForm.name">{{ busy ? "保存中…" : "保存节点" }}</button>
            <button v-if="editingEntityId" class="danger-button" type="button" :disabled="busy" @click="removeEntity">删除节点</button>
          </div>
        </form>
      </div>

      <div v-else class="admin-grid">
        <aside class="admin-list relation-list">
          <button type="button" class="list-create" @click="newRelation">＋ 新建关系</button>
          <button
            v-for="relation in graph.relations"
            :key="relation.id"
            type="button"
            :class="{ active: relation.id === editingRelationId }"
            @click="editRelation(relation)"
          >
            <span>{{ entityName(relation.subject_entity_id) }} → {{ entityName(relation.object_entity_id) }}</span>
            <small>{{ relation.predicate_label || relation.predicate }} · {{ relation.evidence_status === 'verified' ? '已关联证据' : '待补证' }}</small>
          </button>
        </aside>

        <form class="admin-form" @submit.prevent="saveRelation">
          <label>起点
            <select v-model="relationForm.subject_entity_id" required>
              <option value="" disabled>请选择节点</option>
              <option v-for="entity in graph.entities" :key="entity.id" :value="entity.id">{{ entity.name }}</option>
            </select>
          </label>
          <label>关系
            <select v-model="relationForm.predicate">
              <option v-for="item in predicateOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
          <label>终点
            <select v-model="relationForm.object_entity_id" required>
              <option value="" disabled>请选择节点</option>
              <option v-for="entity in graph.entities" :key="entity.id" :value="entity.id">{{ entity.name }}</option>
            </select>
          </label>
          <label>置信度
            <select v-model="relationForm.confidence">
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </label>
          <label>关系说明<textarea v-model.trim="relationForm.description" rows="3" /></label>

          <fieldset>
            <legend>知识片段证据</legend>
            <div class="evidence-toolbar">
              <select v-model="evidenceSource">
                <option value="">全部知识文件</option>
                <option v-for="file in files" :key="file.source" :value="file.source">{{ file.source }}</option>
              </select>
              <button type="button" :disabled="busy || loadingEvidence" @click="loadEvidence">
                {{ loadingEvidence ? "读取中…" : "查找候选片段" }}
              </button>
            </div>
            <p class="muted">候选片段用于把图谱关系连接到知识库原文；没有证据的关系会标记为待补证。</p>
            <label v-for="chunk in evidenceCandidates" :key="chunk.chunk_id" class="evidence-row">
              <input v-model="relationForm.evidence_chunk_ids" type="checkbox" :value="chunk.chunk_id" />
              <span><strong>{{ chunk.source }} · 片段 {{ chunk.source_index }}</strong>{{ chunk.content }}</span>
            </label>
            <p v-if="evidenceLoaded && !evidenceCandidates.length" class="muted">没有找到同时提及起点和终点的片段，可切换知识文件后查看全部片段。</p>
          </fieldset>

          <div class="form-actions">
            <button
              class="primary-button"
              type="submit"
              :disabled="busy || !relationForm.subject_entity_id || !relationForm.object_entity_id"
            >
              {{ busy ? "保存中…" : "保存关系" }}
            </button>
            <button v-if="editingRelationId" class="danger-button" type="button" :disabled="busy" @click="removeRelation">删除关系</button>
          </div>
        </form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import {
  createKnowledgeGraphEntity,
  createKnowledgeGraphRelation,
  deleteKnowledgeGraphEntity,
  deleteKnowledgeGraphRelation,
  getKnowledgeEvidenceChunks,
  rebuildKnowledgeMentions,
  updateKnowledgeGraphEntity,
  updateKnowledgeGraphEntityRagSources,
  updateKnowledgeGraphRelation,
} from "@/api";
import type {
  CurriculumFileItem,
  KnowledgeEntity,
  KnowledgeEntityInput,
  KnowledgeEvidence,
  KnowledgeGraphPayload,
  KnowledgeRelation,
  KnowledgeRelationInput,
} from "@/types";

const props = defineProps<{
  graph: KnowledgeGraphPayload;
  files: CurriculumFileItem[];
  saving?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  refresh: [];
}>();

const predicateOptions = [
  { value: "feeds_on", label: "取食" },
  { value: "visits", label: "访花" },
  { value: "pollinates", label: "授粉" },
  { value: "lives_on", label: "栖息" },
  { value: "lays_eggs_on", label: "产卵于" },
  { value: "damages", label: "危害" },
  { value: "predator_of", label: "捕食" },
  { value: "parasite_of", label: "寄生" },
  { value: "attracted_by", label: "被吸引" },
  { value: "associated_with", label: "相关" },
] as const;

const tab = ref<"entities" | "relations">("entities");
const busy = ref(false);
const error = ref("");
const editingEntityId = ref("");
const entityAliases = ref("");
const entitySources = ref<string[]>([]);
const entityForm = reactive<KnowledgeEntityInput>({
  name: "",
  entity_type: "insect",
  aliases: [],
  description: "",
  source: "manual",
});

const editingRelationId = ref("");
const evidenceSource = ref("");
const evidenceCandidates = ref<KnowledgeEvidence[]>([]);
const evidenceLoaded = ref(false);
const loadingEvidence = ref(false);
const relationForm = reactive<KnowledgeRelationInput>({
  subject_entity_id: "",
  predicate: "feeds_on",
  object_entity_id: "",
  description: "",
  confidence: "medium",
  evidence_chunk_ids: [],
});

function entityName(entityId: string): string {
  return props.graph.entities.find((item) => item.id === entityId)?.name || entityId;
}

function entityTypeLabel(type: string): string {
  return ({ insect: "昆虫", plant: "植物", habitat: "栖息地", season: "季节", concept: "概念" } as Record<string, string>)[type] || type;
}

function knowledgeCategoryLabel(category: CurriculumFileItem["category"]): string {
  return ({
    curriculum: "课标",
    ecology: "生态资料",
    rural_revitalization: "乡村振兴资料",
  })[category];
}

function newEntity() {
  editingEntityId.value = "";
  entityForm.name = "";
  entityForm.entity_type = "insect";
  entityAliases.value = "";
  entityForm.description = "";
  entityForm.source = "manual";
  entitySources.value = [];
  error.value = "";
}

function editEntity(entity: KnowledgeEntity) {
  editingEntityId.value = entity.id;
  entityForm.name = entity.name;
  entityForm.entity_type = entity.entity_type as KnowledgeEntityInput["entity_type"];
  entityAliases.value = entity.aliases.join("，");
  entityForm.description = entity.description;
  entityForm.source = entity.source || "manual";
  entitySources.value = [...entity.rag_sources];
  error.value = "";
}

function normalizedAliases(): string[] {
  return Array.from(new Set(entityAliases.value.split(/[，,]/).map((item) => item.trim()).filter(Boolean)));
}

async function saveEntity() {
  busy.value = true;
  error.value = "";
  try {
    const payload = { ...entityForm, aliases: normalizedAliases() };
    if (editingEntityId.value) {
      await updateKnowledgeGraphEntity(editingEntityId.value, payload);
      await updateKnowledgeGraphEntityRagSources(editingEntityId.value, entitySources.value);
    } else {
      await createKnowledgeGraphEntity(payload);
    }
    emit("refresh");
    newEntity();
  } catch (cause: any) {
    error.value = cause.message || String(cause);
  } finally {
    busy.value = false;
  }
}

async function removeEntity() {
  if (!editingEntityId.value || !window.confirm("删除节点会同时删除与它连接的关系，确认继续吗？")) return;
  busy.value = true;
  error.value = "";
  try {
    await deleteKnowledgeGraphEntity(editingEntityId.value);
    emit("refresh");
    newEntity();
  } catch (cause: any) {
    error.value = cause.message || String(cause);
  } finally {
    busy.value = false;
  }
}

function newRelation() {
  editingRelationId.value = "";
  relationForm.subject_entity_id = "";
  relationForm.predicate = "feeds_on";
  relationForm.object_entity_id = "";
  relationForm.description = "";
  relationForm.confidence = "medium";
  relationForm.evidence_chunk_ids = [];
  evidenceSource.value = "";
  evidenceCandidates.value = [];
  evidenceLoaded.value = false;
  error.value = "";
}

function editRelation(relation: KnowledgeRelation) {
  editingRelationId.value = relation.id;
  relationForm.subject_entity_id = relation.subject_entity_id;
  relationForm.predicate = relation.predicate;
  relationForm.object_entity_id = relation.object_entity_id;
  relationForm.description = relation.description;
  relationForm.confidence = relation.confidence as KnowledgeRelationInput["confidence"];
  relationForm.evidence_chunk_ids = relation.evidence.map((item) => item.chunk_id);
  evidenceCandidates.value = [...relation.evidence];
  evidenceSource.value = relation.evidence[0]?.source || "";
  evidenceLoaded.value = Boolean(relation.evidence.length);
  error.value = "";
}

async function loadEvidence() {
  loadingEvidence.value = true;
  error.value = "";
  try {
    const relationId = editingRelationId.value;
    const chunks = await getKnowledgeEvidenceChunks(relationId, evidenceSource.value);
    const selected = new Map(evidenceCandidates.value.map((item) => [item.chunk_id, item]));
    for (const chunk of chunks) selected.set(chunk.chunk_id, chunk);
    evidenceCandidates.value = Array.from(selected.values());
    evidenceLoaded.value = true;
  } catch (cause: any) {
    error.value = cause.message || String(cause);
  } finally {
    loadingEvidence.value = false;
  }
}

async function saveRelation() {
  if (relationForm.subject_entity_id === relationForm.object_entity_id) {
    error.value = "关系起点和终点不能相同";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const payload = {
      ...relationForm,
      evidence_chunk_ids: [...relationForm.evidence_chunk_ids],
    };
    if (editingRelationId.value) {
      await updateKnowledgeGraphRelation(editingRelationId.value, payload);
    } else {
      await createKnowledgeGraphRelation(payload);
    }
    emit("refresh");
    newRelation();
  } catch (cause: any) {
    error.value = cause.message || String(cause);
  } finally {
    busy.value = false;
  }
}

async function removeRelation() {
  if (!editingRelationId.value || !window.confirm("确认删除这条图谱关系吗？")) return;
  busy.value = true;
  error.value = "";
  try {
    await deleteKnowledgeGraphRelation(editingRelationId.value);
    emit("refresh");
    newRelation();
  } catch (cause: any) {
    error.value = cause.message || String(cause);
  } finally {
    busy.value = false;
  }
}

async function rebuildMentions() {
  busy.value = true;
  error.value = "";
  try {
    const count = await rebuildKnowledgeMentions();
    emit("refresh");
    window.alert(`已重建 ${count} 条实体—知识片段连接`);
  } catch (cause: any) {
    error.value = cause.message || String(cause);
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.graph-admin-workbench { width: min(1040px, calc(100vw - 36px)); max-height: min(820px, calc(100vh - 36px)); overflow: hidden; display: flex; flex-direction: column; }
.head-actions, .form-actions, .evidence-toolbar, .graph-admin-tabs { display: flex; gap: 10px; align-items: center; }
.graph-admin-tabs { padding: 12px 20px 0; }
.graph-admin-tabs button.active { color: var(--accent, #3e8a68); border-color: currentColor; }
.graph-admin-error { margin: 10px 20px 0; padding: 9px 12px; color: #a53b3b; background: rgba(190, 66, 66, .1); border-radius: 8px; }
.admin-grid { min-height: 0; flex: 1; display: grid; grid-template-columns: 280px 1fr; gap: 16px; padding: 16px 20px 20px; overflow: hidden; }
.admin-list { overflow: auto; display: flex; flex-direction: column; gap: 7px; padding-right: 4px; }
.admin-list button { text-align: left; display: grid; gap: 3px; padding: 10px 12px; }
.admin-list button span { font-weight: 600; }
.admin-list button small { opacity: .7; }
.admin-list button.active { border-color: var(--accent, #3e8a68); background: rgba(62, 138, 104, .1); }
.admin-list .list-create { text-align: center; color: var(--accent, #3e8a68); }
.admin-form { overflow: auto; display: grid; align-content: start; gap: 12px; padding: 2px 8px 12px 2px; }
.admin-form > label { display: grid; gap: 6px; font-weight: 600; }
.admin-form input:not([type="checkbox"]), .admin-form select, .admin-form textarea { width: 100%; box-sizing: border-box; padding: 9px 10px; border: 1px solid rgba(128, 128, 128, .28); border-radius: 8px; color: inherit; background: rgba(255, 255, 255, .04); }
.admin-form fieldset { display: grid; gap: 8px; border: 1px solid rgba(128, 128, 128, .22); border-radius: 10px; padding: 12px; }
.check-row { display: grid; grid-template-columns: auto 1fr auto; gap: 8px; align-items: center; font-weight: 400; }
.evidence-toolbar select { flex: 1; }
.evidence-row { display: grid; grid-template-columns: auto 1fr; gap: 8px; align-items: start; font-weight: 400; }
.evidence-row span { display: grid; gap: 3px; max-height: 94px; overflow: auto; font-size: 12px; line-height: 1.45; }
.muted { margin: 0; opacity: .65; font-size: 12px; }
.danger-button { color: #b44949; }
@media (max-width: 760px) { .admin-grid { grid-template-columns: 1fr; overflow: auto; } .admin-list { max-height: 220px; } }
</style>
