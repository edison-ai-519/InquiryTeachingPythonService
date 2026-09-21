<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <section class="knowledge-config-modal" role="dialog" aria-modal="true" aria-labelledby="knowledge-config-title">
      <header class="knowledge-config-head">
        <div>
          <p class="section-kicker">管理员配置</p>
          <h2 id="knowledge-config-title">知识配置中心</h2>
          <span>统一管理课标知识库、专家权限与知识图谱</span>
        </div>
        <button class="close-button" type="button" @click="$emit('close')"><X :size="18" />关闭</button>
      </header>

      <section class="knowledge-config-summary">
        <article><strong>{{ files.length }}</strong><span>知识库文件</span></article>
        <article><strong>{{ permissionCoverage }}%</strong><span>专家授权覆盖</span></article>
        <article><strong>{{ graph.entities.length }}</strong><span>图谱节点</span></article>
        <article><strong>{{ unboundNodeCount }}</strong><span>未绑定节点</span></article>
      </section>

      <nav class="knowledge-config-tabs" aria-label="配置类型">
        <button v-for="tab in tabs" :key="tab.id" type="button" :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">
          <component :is="tab.icon" :size="15" />
          {{ tab.label }}
        </button>
      </nav>

      <p v-if="error" class="curriculum-error">{{ error }}</p>

      <div class="knowledge-config-body">
        <section v-if="activeTab === 'files'" class="knowledge-config-panel">
          <div class="curriculum-control-panel">
            <div class="vector-summary"><Database :size="20" /><span><strong>{{ statusLabel }}</strong><small v-if="status">{{ status.model }} · {{ status.vector_count }}/{{ status.database_chunk_count }} 个向量</small><small v-else>正在读取向量服务状态</small></span></div>
            <div class="curriculum-admin-actions"><button type="button" :disabled="Boolean(operation) || loadingAdmin" @click="$emit('rebuild')"><RefreshCw :size="15" />重建索引</button><button type="button" :disabled="Boolean(operation)" @click="$emit('export')"><Download :size="15" />导出知识库</button><button type="button" :disabled="Boolean(operation)" @click="$emit('import')"><Upload :size="15" />导入知识库</button></div>
          </div>
          <button class="curriculum-dropzone" type="button" :disabled="uploading" @click="$emit('pick-files')" @dragover.prevent @drop.prevent="$emit('drop-files', $event)"><Upload :size="21" /><strong>{{ uploading ? '正在导入课标' : '上传课标文件' }}</strong><span>PDF / DOCX / TXT / MD，单文件最大 20 MB</span></button>
          <input ref="fileInput" class="visually-hidden" type="file" multiple accept=".pdf,.docx,.txt,.md" @change="$emit('files-selected', $event)" />
          <input ref="bundleInput" class="visually-hidden" type="file" accept=".zip,application/zip" @change="$emit('bundle-selected', $event)" />
          <div v-if="uploadResults.length" class="curriculum-upload-results"><span v-for="result in uploadResults" :key="result.name" :class="`status-${result.status}`">{{ result.name }} · {{ result.status === 'success' ? '完成' : result.status === 'failed' ? '失败' : '等待' }}</span></div>
          <div v-if="loading" class="curriculum-empty"><RefreshCw class="spin-icon" :size="20" />正在读取课标列表</div>
          <div v-else-if="files.length" class="curriculum-file-list">
            <article v-for="item in files" :key="item.source" class="curriculum-file-row">
              <div class="curriculum-file-icon" aria-hidden="true"><BookOpen :size="18" /></div>
              <div class="curriculum-file-copy">
                <strong :title="item.source">{{ item.source }}</strong>
                <span>{{ item.extension.replace('.', '').toUpperCase() }} · {{ item.chunk_count }} 个片段 · {{ formatDate(item.updated_at) }}</span>
                <small :class="`vector-status-${item.vector_status}`">{{ vectorLabel(item) }}</small>
              </div>
              <button type="button" @click="selectPermissionFile(item)">配置权限</button>
              <button class="delete-file-button" type="button" :disabled="deletingSources.includes(item.source) || uploading" @click="$emit('delete-file', item)"><Trash2 :size="16" /></button>
            </article>
          </div>
          <div v-else class="curriculum-empty"><BookOpen :size="24" />当前还没有导入课标</div>
        </section>

        <section v-else-if="activeTab === 'permissions'" class="knowledge-config-split">
          <aside class="config-list-pane">
            <strong>知识库文件</strong>
            <button v-for="file in files" :key="file.source" type="button" :class="{ active: selectedPermissionSource === file.source }" @click="selectPermissionFile(file)">
              <span>{{ file.source }}</span>
              <small>{{ file.allowed_expert_ids.length ? `${file.allowed_expert_ids.length} 位专家` : '未授权' }}</small>
            </button>
          </aside>
          <section class="config-detail-pane">
            <template v-if="selectedPermissionFile">
              <div class="config-detail-head"><strong>{{ selectedPermissionFile.source }}</strong><span>选择可查询该知识库的专家 Agent</span></div>
              <div class="config-check-grid">
                <label v-for="expert in experts" :key="expert.id"><input :checked="permissionDraft.includes(expert.id)" type="checkbox" @change="$emit('toggle-permission', expert.id)" /><span><strong>{{ expert.name }}</strong><small>{{ expert.role }}</small></span></label>
              </div>
              <div class="config-actions"><button class="primary-button" type="button" :disabled="savingSource === selectedPermissionFile.source" @click="$emit('save-permissions', selectedPermissionFile)">{{ savingSource === selectedPermissionFile.source ? '保存中' : '保存专家权限' }}</button><button class="ghost-button" type="button" @click="$emit('cancel-permissions')">取消</button></div>
            </template>
            <div v-else class="curriculum-empty"><ShieldCheck :size="24" />请选择一个知识库文件配置专家权限</div>
          </section>
        </section>

        <section v-else-if="activeTab === 'graph'" class="graph-config-workspace">
          <header class="graph-config-toolbar">
            <div>
              <strong>图谱配置</strong>
              <span>{{ graph.entities.length }} 个节点 · {{ graph.relations.length }} 条关系 · {{ unboundNodeCount }} 个未绑定知识库</span>
            </div>
            <div class="graph-config-actions">
              <button type="button" @click="startNewEntity"><Plus :size="15" />新增节点</button>
              <button type="button" @click="startNewRelation"><Plus :size="15" />新增关系</button>
              <button class="danger-button" type="button" :disabled="savingGraph || !graph.entities.length" @click="$emit('delete-graph')"><Trash2 :size="15" />删除图谱</button>
            </div>
          </header>

          <div class="graph-config-grid">
            <aside class="graph-config-sidebar">
              <input v-model.trim="graphSearch" class="input" placeholder="搜索节点、关系或类型" />
              <div class="graph-config-switch" role="tablist" aria-label="图谱配置列表">
                <button type="button" :class="{ active: graphListMode === 'entities' }" @click="graphListMode = 'entities'">节点 {{ filteredEntities.length }}</button>
                <button type="button" :class="{ active: graphListMode === 'relations' }" @click="graphListMode = 'relations'">关系 {{ filteredRelations.length }}</button>
              </div>
              <div v-if="graphListMode === 'entities'" class="graph-config-list">
                <button v-for="entity in filteredEntities" :key="entity.id" type="button" :class="{ active: editingKind === 'entity' && entity.id === entityForm.id }" @click="editEntity(entity)">
                  <span :title="entity.name">{{ entity.name }}</span>
                  <small>{{ entity.entity_type }} · {{ entity.rag_sources.length ? `${entity.rag_sources.length} 个知识库` : '未绑定' }}</small>
                </button>
              </div>
              <div v-else class="graph-config-list">
                <button v-for="relation in filteredRelations" :key="relation.id" type="button" :class="{ active: editingKind === 'relation' && relation.id === relationForm.id }" @click="editRelation(relation)">
                  <span :title="`${entityName(relation.subject_entity_id)} → ${entityName(relation.object_entity_id)}`">{{ entityName(relation.subject_entity_id) }} → {{ entityName(relation.object_entity_id) }}</span>
                  <small>{{ relation.predicate_label || relation.predicate }}</small>
                </button>
              </div>
            </aside>

            <div class="graph-preview-pane">
              <div class="graph-preview-pane-head">
                <strong>图谱预览</strong>
                <button class="graph-preview-expand-button" type="button" :disabled="!graph.entities.length" title="放大图谱" aria-label="放大图谱" @click="openGraphStage"><Maximize2 :size="16" /></button>
              </div>
              <FocusKnowledgeGraphCanvas
                :graph="graph"
                :selected-entity-ids="editingKind === 'entity' && entityForm.id ? [entityForm.id] : []"
                :selected-relation-id="editingKind === 'relation' ? relationForm.id : ''"
                :max-nodes="graph.entities.length || 18"
                variant="map"
                aria-label="知识图谱配置预览"
                @select-node="selectGraphNode"
                @focus-node="selectGraphNode"
                @select-relation="selectGraphRelation"
              />
            </div>

            <section class="graph-editor-pane">
            <form v-if="editingKind === 'entity'" class="config-form" @submit.prevent="$emit('save-entity', { ...entityForm, aliases: aliasesFromText(entityForm.aliasesText), rag_sources: [...entityForm.rag_sources] })">
              <div class="config-detail-head"><strong>{{ entityForm.id ? '编辑节点' : '新增节点' }}</strong><span>节点保存后可继续配置关系与知识库绑定</span></div>
              <label><span>节点 ID</span><input v-model.trim="entityForm.id" class="input" :disabled="Boolean(entityOriginalId)" placeholder="留空自动生成" /></label>
              <label><span>节点名称</span><input v-model.trim="entityForm.name" class="input" required /></label>
              <label><span>节点类型</span><input v-model.trim="entityForm.entity_type" class="input" required placeholder="concept / plant / habitat" /></label>
              <label><span>别名</span><input v-model="entityForm.aliasesText" class="input" placeholder="用逗号分隔" /></label>
              <label><span>描述</span><textarea v-model="entityForm.description" class="input" rows="3"></textarea></label>
              <label><span>来源说明</span><input v-model.trim="entityForm.source" class="input" /></label>
              <div class="config-check-grid compact">
                <label v-for="file in files" :key="file.source"><input v-model="entityForm.rag_sources" type="checkbox" :value="file.source" /><span>{{ file.source }}</span></label>
              </div>
              <div class="config-actions"><button class="primary-button" type="submit" :disabled="savingGraph">{{ savingGraph ? '保存中' : '保存节点' }}</button><button v-if="entityOriginalId" class="danger-button" type="button" :disabled="savingGraph" @click="$emit('delete-entity', entityOriginalId, relatedRelationCount(entityOriginalId))"><Trash2 :size="15" />删除节点</button></div>
            </form>

            <form v-else class="config-form" @submit.prevent="$emit('save-relation', { ...relationForm })">
              <div class="config-detail-head"><strong>{{ relationForm.id ? '编辑关系' : '新增关系' }}</strong><span>关系会显示在图谱预览和聊天图谱选择中</span></div>
              <label><span>关系 ID</span><input v-model.trim="relationForm.id" class="input" :disabled="Boolean(relationOriginalId)" placeholder="留空自动生成" /></label>
              <label><span>起点节点</span><select v-model="relationForm.subject_entity_id" class="input" required><option value="">请选择</option><option v-for="entity in graph.entities" :key="entity.id" :value="entity.id">{{ entity.name }}</option></select></label>
              <label><span>关系类型</span><input v-model.trim="relationForm.predicate" class="input" required placeholder="关联 / 影响 / 捕食" /></label>
              <label><span>终点节点</span><select v-model="relationForm.object_entity_id" class="input" required><option value="">请选择</option><option v-for="entity in graph.entities" :key="entity.id" :value="entity.id">{{ entity.name }}</option></select></label>
              <label><span>置信度</span><select v-model="relationForm.confidence" class="input"><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label>
              <label><span>描述</span><textarea v-model="relationForm.description" class="input" rows="3"></textarea></label>
              <label><span>证据来源</span><input v-model.trim="relationForm.evidence_source" class="input" /></label>
              <div class="config-actions"><button class="primary-button" type="submit" :disabled="savingGraph">{{ savingGraph ? '保存中' : '保存关系' }}</button><button v-if="relationOriginalId" class="danger-button" type="button" :disabled="savingGraph" @click="$emit('delete-relation', relationOriginalId)"><Trash2 :size="15" />删除关系</button></div>
            </form>
            </section>
          </div>
        </section>
        <section v-else-if="activeTab === 'import'" class="knowledge-config-split">
          <section class="config-detail-pane">
            <div class="config-detail-head"><strong>JSON 导入</strong><span>粘贴或上传图谱 JSON，先预览差异再合并</span></div>
            <textarea v-model="jsonText" class="input json-input" rows="14" placeholder='{"entities":[],"relations":[]}'></textarea>
            <div class="config-actions"><button class="ghost-button" type="button" @click="jsonFileInput?.click()"><Upload :size="15" />上传 JSON</button><button class="primary-button" type="button" :disabled="importingGraph" @click="previewJson">预览导入</button><button class="primary-button" type="button" :disabled="!jsonPreview?.can_import || importingGraph" @click="$emit('import-graph-json', parsedJson)">{{ importingGraph ? '导入中' : '确认合并' }}</button></div>
            <input ref="jsonFileInput" class="visually-hidden" type="file" accept=".json,application/json" @change="readJsonFile" />
          </section>
          <aside class="config-preview-pane">
            <strong>预览结果</strong>
            <div v-if="jsonPreview" class="import-preview-list">
              <span>新增节点 {{ jsonPreview.new_entity_count }}</span>
              <span>更新节点 {{ jsonPreview.updated_entity_count }}</span>
              <span>新增关系 {{ jsonPreview.new_relation_count }}</span>
              <span>更新关系 {{ jsonPreview.updated_relation_count }}</span>
              <span>影响已有关系 {{ jsonPreview.affected_relation_ids.length }}</span>
              <p v-if="jsonPreview.missing_sources.length">缺失知识库：{{ jsonPreview.missing_sources.join('、') }}</p>
              <p v-if="jsonPreview.errors.length">{{ jsonPreview.errors.join('；') }}</p>
            </div>
            <p v-else class="curriculum-empty">预览结果会显示在这里</p>
          </aside>
        </section>

        <section v-else class="knowledge-config-panel">
          <div class="curriculum-section-head"><strong><History :size="17" />最近召回</strong><button type="button" :disabled="loadingAdmin" @click="$emit('refresh-admin')"><RefreshCw :size="15" /></button></div>
          <details v-for="record in retrievals" :key="record.id" class="curriculum-retrieval-row"><summary>{{ record.query || '空查询' }}<small>{{ modeLabel(record.mode) }} · {{ formatDate(record.created_at) }}</small></summary><p v-if="record.vector_error" class="curriculum-error">{{ record.vector_error }}</p><div v-for="hit in record.records" :key="`${record.id}-${hit.chunk_id}`" class="retrieval-hit"><strong>{{ hit.source }} · 片段 {{ hit.source_index }}</strong><span>综合 {{ score(hit.score) }} · 向量 {{ score(hit.vector_score) }} · BM25 {{ score(hit.bm25_score) }}</span><p>{{ hit.content }}</p></div><p v-if="!record.records.length" class="retrieval-empty">本次没有命中课标片段。</p></details>
          <p v-if="!retrievals.length" class="retrieval-empty">当前还没有课标召回记录</p>
        </section>

        <Teleport to="body">
          <div v-if="graphExpanded" class="graph-stage-overlay" role="dialog" aria-modal="true" aria-label="图谱配置大幕布" @keydown.esc.prevent="closeGraphStage">
            <section class="graph-stage-panel">
              <header class="graph-stage-head">
                <div>
                  <strong>图谱配置预览</strong>
                  <span>{{ graph.entities.length }} 个节点 · {{ graph.relations.length }} 条关系</span>
                </div>
                <button ref="graphStageCloseRef" type="button" @click="closeGraphStage"><X :size="16" />关闭</button>
              </header>
              <div class="graph-stage-body">
                <FocusKnowledgeGraphCanvas
                  :graph="graph"
                  :selected-entity-ids="editingKind === 'entity' && entityForm.id ? [entityForm.id] : []"
                  :selected-relation-id="editingKind === 'relation' ? relationForm.id : ''"
                  :max-nodes="graph.entities.length || 18"
                  variant="map"
                  :fullscreen="true"
                  aria-label="图谱配置大幕布"
                  @select-node="selectGraphNode"
                  @focus-node="selectGraphNode"
                  @select-relation="selectGraphRelation"
                />
              </div>
            </section>
          </div>
        </Teleport>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from "vue";
import { BookOpen, Database, Download, GitBranch, History, Maximize2, Plus, RefreshCw, ShieldCheck, Trash2, Upload, X } from "lucide-vue-next";
import FocusKnowledgeGraphCanvas from "@/components/FocusKnowledgeGraphCanvas.vue";
import type { Component } from "vue";
import type { CurriculumFileItem, CurriculumRetrievalRecord, CurriculumVectorStatus, ExpertAgentItem, KnowledgeEntity, KnowledgeGraphImportPreview, KnowledgeGraphPayload, KnowledgeRelation } from "@/types";

const props = defineProps<{
  visible: boolean;
  files: CurriculumFileItem[];
  totalChunks: number;
  status: CurriculumVectorStatus | null;
  statusLabel: string;
  operation: string;
  loading: boolean;
  loadingAdmin: boolean;
  uploading: boolean;
  error: string;
  uploadResults: { name: string; status: "pending" | "success" | "failed"; message: string }[];
  experts: ExpertAgentItem[];
  editingSource: string;
  permissionDraft: string[];
  savingSource: string;
  deletingSources: string[];
  retrievals: CurriculumRetrievalRecord[];
  graph: KnowledgeGraphPayload;
  savingGraph: boolean;
  importingGraph: boolean;
  jsonPreview: KnowledgeGraphImportPreview | null;
  formatDate: (value: string) => string;
  vectorLabel: (item: CurriculumFileItem) => string;
  modeLabel: (mode: string) => string;
  score: (value: number) => string;
}>();

const emit = defineEmits<{
  close: [];
  rebuild: [];
  export: [];
  import: [];
  "bundle-selected": [event: Event];
  "pick-files": [];
  "drop-files": [event: DragEvent];
  "files-selected": [event: Event];
  "toggle-permission": [expertId: string];
  "save-permissions": [item: CurriculumFileItem];
  "cancel-permissions": [];
  "edit-permissions": [item: CurriculumFileItem];
  "delete-file": [item: CurriculumFileItem];
  "refresh-admin": [];
  "save-entity": [payload: Record<string, unknown>];
  "delete-entity": [entityId: string, relationCount: number];
  "delete-graph": [];
  "save-relation": [payload: Record<string, unknown>];
  "delete-relation": [relationId: string];
  "preview-graph-json": [payload: unknown];
  "import-graph-json": [payload: unknown];
}>();

type TabId = "files" | "permissions" | "graph" | "import" | "retrievals";
const tabs: { id: TabId; label: string; icon: Component }[] = [
  { id: "files", label: "知识库文件", icon: BookOpen },
  { id: "permissions", label: "专家权限", icon: ShieldCheck },
  { id: "graph", label: "图谱配置", icon: GitBranch },
  { id: "import", label: "JSON导入", icon: Upload },
  { id: "retrievals", label: "召回记录", icon: History },
];
const activeTab = ref<TabId>("files");
const graphSearch = ref("");
const graphListMode = ref<"entities" | "relations">("entities");
const graphExpanded = ref(false);
const graphStageCloseRef = ref<HTMLButtonElement | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const bundleInput = ref<HTMLInputElement | null>(null);
const jsonFileInput = ref<HTMLInputElement | null>(null);
const jsonText = ref("");
const parsedJson = ref<unknown>(null);
const editingKind = ref<"entity" | "relation">("entity");
const entityOriginalId = ref("");
const relationOriginalId = ref("");

const entityForm = reactive({
  id: "",
  name: "",
  entity_type: "concept",
  aliasesText: "",
  description: "",
  source: "",
  rag_sources: [] as string[],
});
const relationForm = reactive({
  id: "",
  subject_entity_id: "",
  predicate: "",
  object_entity_id: "",
  description: "",
  evidence_source: "",
  confidence: "medium",
});

const permissionCoverage = computed(() => {
  if (!props.files.length) return 0;
  const configured = props.files.filter((file) => file.allowed_expert_ids.length > 0).length;
  return Math.round((configured / props.files.length) * 100);
});
const unboundNodeCount = computed(() => props.graph.entities.filter((entity) => !entity.rag_sources.length).length);
const selectedPermissionSource = computed(() => props.editingSource || props.files[0]?.source || "");
const selectedPermissionFile = computed(() => props.files.find((file) => file.source === selectedPermissionSource.value));
const filteredEntities = computed(() => {
  const keyword = graphSearch.value.toLowerCase();
  if (!keyword) return props.graph.entities;
  return props.graph.entities.filter((entity) => `${entity.name} ${entity.id} ${entity.entity_type}`.toLowerCase().includes(keyword));
});
const filteredRelations = computed(() => {
  const keyword = graphSearch.value.toLowerCase();
  if (!keyword) return props.graph.relations;
  return props.graph.relations.filter((relation) => `${relation.id} ${relation.predicate} ${entityName(relation.subject_entity_id)} ${entityName(relation.object_entity_id)}`.toLowerCase().includes(keyword));
});
watch(() => props.visible, (visible) => {
  if (visible) {
    if (!props.editingSource && props.files[0]) emit("edit-permissions", props.files[0]);
  }
});

let graphStageReturnFocus: HTMLElement | null = null;
let graphStagePreviousOverflow = "";

watch(graphExpanded, async (expanded) => {
  if (expanded) {
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
  graphExpanded.value = true;
}

function closeGraphStage() {
  graphExpanded.value = false;
}

function selectPermissionFile(file: CurriculumFileItem) {
  emit("edit-permissions", file);
}

function entityName(entityId: string): string {
  return props.graph.entities.find((entity) => entity.id === entityId)?.name || entityId;
}

function aliasesFromText(value: string): string[] {
  return value.split(/[，,]/).map((item) => item.trim()).filter(Boolean);
}

function editEntity(entity: KnowledgeEntity & { x?: number; y?: number }) {
  editingKind.value = "entity";
  entityOriginalId.value = entity.id;
  Object.assign(entityForm, {
    id: entity.id,
    name: entity.name,
    entity_type: entity.entity_type,
    aliasesText: entity.aliases.join("，"),
    description: entity.description,
    source: entity.source,
    rag_sources: [...entity.rag_sources],
  });
}

function selectGraphNode(entityId: string) {
  const entity = props.graph.entities.find((item) => item.id === entityId);
  if (entity) editEntity(entity);
}

function selectGraphRelation(relationId: string) {
  const relation = props.graph.relations.find((item) => item.id === relationId);
  if (relation) editRelation(relation);
}

function startNewEntity() {
  editingKind.value = "entity";
  entityOriginalId.value = "";
  Object.assign(entityForm, {
    id: "",
    name: "",
    entity_type: "concept",
    aliasesText: "",
    description: "",
    source: "人工配置",
    rag_sources: [],
  });
}

function editRelation(relation: KnowledgeRelation) {
  editingKind.value = "relation";
  relationOriginalId.value = relation.id;
  Object.assign(relationForm, {
    id: relation.id,
    subject_entity_id: relation.subject_entity_id,
    predicate: relation.predicate,
    object_entity_id: relation.object_entity_id,
    description: relation.description,
    evidence_source: relation.evidence_source,
    confidence: relation.confidence || "medium",
  });
}

function startNewRelation() {
  editingKind.value = "relation";
  relationOriginalId.value = "";
  Object.assign(relationForm, {
    id: "",
    subject_entity_id: props.graph.entities[0]?.id || "",
    predicate: "",
    object_entity_id: props.graph.entities[1]?.id || props.graph.entities[0]?.id || "",
    description: "",
    evidence_source: "",
    confidence: "medium",
  });
}

function relatedRelationCount(entityId: string): number {
  return props.graph.relations.filter((relation) => relation.subject_entity_id === entityId || relation.object_entity_id === entityId).length;
}

function previewJson() {
  try {
    const payload = JSON.parse(jsonText.value || "{}");
    parsedJson.value = payload;
    emit("preview-graph-json", payload);
  } catch {
    parsedJson.value = null;
  }
}

async function readJsonFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  jsonText.value = await file.text();
}

defineExpose({
  openFilePicker: () => fileInput.value?.click(),
  openBundlePicker: () => bundleInput.value?.click(),
});
</script>
