<template>
  <aside v-if="item" class="knowledge-admin-detail" aria-label="资料详情">
    <header class="knowledge-admin-detail-head">
      <div>
        <p>{{ categoryLabel(item.category) }}</p>
        <h2 :title="item.title || item.source">{{ item.title || item.source }}</h2>
        <span :title="item.source">{{ item.source }}</span>
      </div>
      <button type="button" aria-label="关闭资料详情" title="关闭详情" @click="$emit('close')"><X :size="18" /></button>
    </header>

    <nav class="knowledge-admin-detail-tabs" aria-label="资料详情栏目">
      <button v-for="tab in tabs" :key="tab.value" type="button" :class="{ active: activeTab === tab.value }" @click="selectTab(tab.value)">
        {{ tab.label }}<small v-if="tab.count !== undefined">{{ tab.count }}</small>
      </button>
    </nav>

    <div v-if="detailError" class="knowledge-admin-detail-error">
      <AlertCircle :size="16" /><span>{{ detailError }}</span><button type="button" @click="loadDetail">重试</button>
    </div>

    <div class="knowledge-admin-detail-body">
      <div v-if="detailLoading" class="knowledge-admin-detail-empty"><LoaderCircle class="spin-icon" :size="20" />正在读取资料详情</div>

      <section v-else-if="activeTab === 'overview'" class="knowledge-admin-detail-section">
        <div class="knowledge-admin-status-line">
          <span :class="`status-${item.review_status}`">{{ reviewLabel(item.review_status) }}</span>
          <span :class="`status-${item.vector_status === 'ready' ? 'published' : 'draft'}`">{{ vectorLabel(item) }}</span>
        </div>
        <div v-if="item.publish_errors.length" class="knowledge-admin-validation">
          <AlertTriangle :size="17" /><span><strong>发布前还需补齐</strong>{{ item.publish_errors.join('、') }}</span>
        </div>
        <dl class="knowledge-admin-detail-list">
          <div><dt>四层归属</dt><dd>{{ item.category === 'rural_revitalization' ? layerLabel(item.policy_layer) : '不适用' }}</dd></div>
          <div><dt>资料性质</dt><dd>{{ documentTypeLabel(item.document_type) }}</dd></div>
          <div><dt>地域范围</dt><dd>{{ scopeLabel(item.authority_scope) }}<template v-if="item.region_code"> · {{ item.region_code }}</template></dd></div>
          <div><dt>发文机关</dt><dd>{{ item.issuing_authority || '待补充' }}</dd></div>
          <div><dt>文号</dt><dd>{{ item.document_number || '无公开文号' }}</dd></div>
          <div><dt>发布日期</dt><dd>{{ item.publish_date || '待补充' }}</dd></div>
          <div><dt>效力状态</dt><dd>{{ validityLabel(item.validity_status) }}</dd></div>
          <div><dt>最近核验</dt><dd>{{ item.last_verified_at || '待核验' }}</dd></div>
          <div><dt>片段与向量</dt><dd>{{ item.chunk_count }} / {{ item.vector_chunk_count }}</dd></div>
          <div><dt>更新时间</dt><dd>{{ formatDate(item.updated_at) }}</dd></div>
        </dl>
        <div class="knowledge-admin-topic-list"><span v-for="topic in item.topics" :key="topic">{{ topicLabel(topic) }}</span><small v-if="!item.topics.length">尚未设置主题标签</small></div>
        <a v-if="item.source_url" class="knowledge-admin-official-link" :href="item.source_url" target="_blank" rel="noreferrer"><ExternalLink :size="15" />查看官网原文</a>
        <section v-if="detail?.replaces_source || detail?.replaced_by.length" class="knowledge-admin-version-box">
          <strong>版本关系</strong>
          <p v-if="detail?.replaces_source">替代：{{ detail.replaces_source.title }}</p>
          <p v-for="next in detail?.replaced_by || []" :key="next.id">后续版本：{{ next.title }}</p>
        </section>
        <details class="knowledge-admin-technical"><summary>技术信息</summary><p>Checksum：{{ item.checksum || '—' }}</p><p>Embedding：{{ item.embedding_model || '未启用' }}</p><p v-if="item.last_error" class="danger">{{ item.last_error }}</p></details>
      </section>

      <form v-else-if="activeTab === 'metadata'" class="knowledge-admin-metadata" @submit.prevent="$emit('save-metadata', item, metadataDraft)">
        <fieldset><legend>基础信息</legend>
          <label class="wide"><span>标题 *</span><input v-model.trim="metadataDraft.title" required /></label>
          <label><span>四层归属 *</span><select v-model="metadataDraft.policy_layer" required><option value="" disabled>请选择</option><option v-for="option in layerOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
          <label><span>资料性质 *</span><select v-model="metadataDraft.document_type" required><option v-for="option in documentTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
          <label><span>地域层级 *</span><select v-model="metadataDraft.authority_scope" required><option value="national">国家</option><option value="beijing">北京市</option><option value="district">区级</option></select></label>
          <label><span>行政区划代码 *</span><input v-model.trim="metadataDraft.region_code" placeholder="110000" required /></label>
          <label class="wide"><span>发文机关 *</span><input v-model.trim="metadataDraft.issuing_authority" required /></label>
          <label class="wide"><span>文号</span><input v-model.trim="metadataDraft.document_number" /></label>
        </fieldset>
        <fieldset><legend>发布与来源</legend>
          <label><span>发布日期 *</span><input v-model="metadataDraft.publish_date" type="date" required /></label>
          <label><span>核验日期 *</span><input v-model="metadataDraft.last_verified_at" type="date" required /></label>
          <label class="wide"><span>官网URL *</span><input v-model.trim="metadataDraft.source_url" type="url" required /></label>
        </fieldset>
        <fieldset><legend>效力与版本</legend>
          <label><span>生效日期</span><input v-model="metadataDraft.effective_date" type="date" /></label>
          <label><span>失效日期</span><input v-model="metadataDraft.expiry_date" type="date" /></label>
          <label><span>效力状态 *</span><select v-model="metadataDraft.validity_status" required><option value="current">现行</option><option value="expired">已过期</option><option value="repealed">已废止</option><option value="unknown">待核验</option><option value="not_applicable">非规范性材料</option></select></label>
          <label><span>替代来源ID</span><input v-model.trim="metadataDraft.replaces_source_id" /></label>
        </fieldset>
        <fieldset><legend>主题标签</legend><div class="knowledge-admin-topic-options"><label v-for="option in topicOptions" :key="option.value"><input v-model="metadataDraft.topics" type="checkbox" :value="option.value" />{{ option.label }}</label></div></fieldset>
        <div v-if="item.publish_errors.length" class="knowledge-admin-validation"><AlertTriangle :size="17" /><span><strong>保存后仍需核验</strong>{{ item.publish_errors.join('、') }}</span></div>
        <button class="knowledge-admin-save" type="submit" :disabled="Boolean(operation)"><Save :size="15" />保存元数据</button>
      </form>

      <section v-else-if="activeTab === 'chunks'" class="knowledge-admin-detail-section knowledge-admin-chunks">
        <label class="knowledge-admin-chunk-search"><Search :size="15" /><input v-model.trim="chunkSearch" aria-label="搜索当前资料片段" placeholder="在当前资料片段中搜索" /></label>
        <div v-if="chunksLoading" class="knowledge-admin-detail-empty"><LoaderCircle class="spin-icon" :size="18" />正在读取结构化片段</div>
        <article v-for="chunk in visibleChunks" :key="chunk.id">
          <header><strong>{{ chunk.heading_path || '正文' }}</strong><span v-if="chunk.article_number">{{ chunk.article_number }}</span></header>
          <p>{{ chunk.content }}</p><small>片段 {{ chunk.source_index + 1 }} · {{ chunk.chunk_type }}</small>
        </article>
        <div v-if="!chunksLoading && !visibleChunks.length" class="knowledge-admin-detail-empty">没有匹配的结构化片段</div>
      </section>

      <section v-else-if="activeTab === 'review'" class="knowledge-admin-detail-section">
        <div v-if="detail?.review_events.length" class="knowledge-admin-timeline">
          <article v-for="event in detail.review_events" :key="event.id">
            <i></i><div><strong>{{ reviewActionLabel(event.action) }}</strong><span>{{ event.from_status }} → {{ event.to_status }}</span><p v-if="event.note">{{ event.note }}</p><small>{{ formatDate(event.created_at) }}<template v-if="event.actor_user_id"> · {{ event.actor_user_id }}</template></small></div>
          </article>
        </div>
        <div v-else class="knowledge-admin-detail-empty">暂无审核记录</div>
      </section>

      <section v-else class="knowledge-admin-detail-section">
        <div class="knowledge-admin-permission-summary">
          <Users :size="18" /><span><strong>专家检索权限</strong><small>控制哪些专家能够召回这份资料</small></span>
        </div>
        <div v-if="editingSource === item.source" class="knowledge-admin-permission-editor">
          <label v-for="expert in experts" :key="expert.id"><input :checked="permissionDraft.includes(expert.id)" type="checkbox" @change="$emit('toggle-permission', expert.id)" /><span><strong>{{ expert.name }}</strong><small>{{ expert.role }}</small></span></label>
          <div><button type="button" class="primary" :disabled="savingSource === item.source" @click="$emit('save-permissions', item)">保存权限</button><button type="button" @click="$emit('cancel-permissions')">取消</button></div>
        </div>
        <template v-else>
          <div class="knowledge-admin-topic-list"><span v-for="id in item.allowed_expert_ids" :key="id">{{ expertName(id) }}</span><small v-if="!item.allowed_expert_ids.length">当前没有专家可以检索该资料</small></div>
          <button class="knowledge-admin-secondary-action" type="button" @click="$emit('edit-permissions', item)"><Pencil :size="15" />编辑权限</button>
        </template>
      </section>
    </div>

    <footer class="knowledge-admin-detail-actions">
      <div v-if="item.category === 'rural_revitalization'" class="knowledge-admin-review-actions">
        <button v-if="item.review_status === 'draft'" type="button" class="primary" :disabled="Boolean(operation)" @click="requestReview('submit')">提交审核</button>
        <button v-if="item.review_status === 'in_review'" type="button" :disabled="Boolean(operation)" @click="requestReview('return')">退回</button>
        <button v-if="item.review_status === 'in_review'" type="button" class="primary" :disabled="Boolean(operation) || item.publish_errors.length > 0" :title="item.publish_errors.join('、')" @click="requestReview('publish')">发布</button>
        <button v-if="item.review_status === 'published'" type="button" :disabled="Boolean(operation)" @click="requestReview('archive')">归档</button>
      </div>
      <details class="knowledge-admin-more-actions"><summary aria-label="更多资料操作" title="更多操作"><MoreHorizontal :size="18" /></summary><button type="button" class="danger" :disabled="deletingSources.includes(item.source) || uploading" @click="$emit('delete-file', item)"><Trash2 :size="15" />删除资料</button></details>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from "vue";
import { AlertCircle, AlertTriangle, ExternalLink, LoaderCircle, MoreHorizontal, Pencil, Save, Search, Trash2, Users, X } from "lucide-vue-next";
import { getKnowledgeSource, getKnowledgeSourceChunks } from "@/api";
import type { CurriculumFileItem, ExpertAgentItem, KnowledgeSourceChunk, KnowledgeSourceDetail, PolicyLayer } from "@/types";

type DetailTab = "overview" | "metadata" | "chunks" | "review" | "permissions";
const props = defineProps<{
  item: CurriculumFileItem | null;
  operation: string;
  experts: ExpertAgentItem[];
  editingSource: string;
  permissionDraft: string[];
  savingSource: string;
  deletingSources: string[];
  uploading: boolean;
  formatDate: (value: string) => string;
  vectorLabel: (item: CurriculumFileItem) => string;
  expertName: (id: string) => string;
  categoryLabel: (value: CurriculumFileItem["category"]) => string;
  layerLabel: (value: CurriculumFileItem["policy_layer"]) => string;
  scopeLabel: (value: string) => string;
  validityLabel: (value: string) => string;
  reviewLabel: (value: string) => string;
}>();
const emit = defineEmits<{
  close: [];
  "save-metadata": [item: CurriculumFileItem, metadata: Record<string, unknown>];
  "review-source": [item: CurriculumFileItem, action: "submit" | "return" | "publish" | "archive", note: string];
  "edit-permissions": [item: CurriculumFileItem];
  "toggle-permission": [expertId: string];
  "save-permissions": [item: CurriculumFileItem];
  "cancel-permissions": [];
  "delete-file": [item: CurriculumFileItem];
}>();

const activeTab = ref<DetailTab>("overview");
const detail = ref<KnowledgeSourceDetail | null>(null);
const chunks = ref<KnowledgeSourceChunk[]>([]);
const detailLoading = ref(false);
const chunksLoading = ref(false);
const detailError = ref("");
const chunkSearch = ref("");
const metadataDraft = reactive<Record<string, any>>({ topics: [] });
const layerOptions: { value: PolicyLayer; label: string }[] = [
  { value: "foundation", label: "基础法规" }, { value: "annual_action", label: "年度任务" },
  { value: "ceo_talent", label: "CEO与人才" }, { value: "grassroots_compliance", label: "基层合规" },
];
const documentTypeOptions = [
  ["law", "法律"], ["local_regulation", "地方性法规"], ["policy_plan", "政策方案"],
  ["administrative_measure", "管理办法"], ["notice", "通知"], ["training_program", "培训活动"],
  ["case_material", "案例材料"], ["official_information", "官方信息"], ["guide", "办事指南"], ["reference", "参考资料"],
].map(([value, label]) => ({ value, label }));
const topicOptions = [
  ["organization_governance", "组织治理"], ["land_homestead", "土地宅基地"], ["collective_assets", "集体三资"],
  ["industry_development", "产业发展"], ["agritourism", "农文旅"], ["project_finance", "项目资金"],
  ["talent_development", "人才培养"], ["public_services", "公共服务"], ["ecology_environment", "生态环境"],
  ["safety_emergency", "安全应急"], ["digital_rural", "数字乡村"],
].map(([value, label]) => ({ value, label }));

const tabs = computed(() => {
  const values: { value: DetailTab; label: string; count?: number }[] = [{ value: "overview", label: "概览" }];
  if (props.item?.category === "rural_revitalization") values.push({ value: "metadata", label: "元数据" });
  values.push({ value: "chunks", label: "结构片段", count: props.item?.chunk_count || 0 });
  if (props.item?.category === "rural_revitalization") values.push({ value: "review", label: "审核记录", count: detail.value?.review_events.length || 0 });
  values.push({ value: "permissions", label: "专家权限", count: props.item?.allowed_expert_ids.length || 0 });
  return values;
});
const visibleChunks = computed(() => {
  const query = chunkSearch.value.toLowerCase();
  return query ? chunks.value.filter((chunk) => `${chunk.heading_path} ${chunk.article_number} ${chunk.content}`.toLowerCase().includes(query)) : chunks.value;
});

function syncDraft(item: CurriculumFileItem) {
  Object.keys(metadataDraft).forEach((key) => delete metadataDraft[key]);
  Object.assign(metadataDraft, {
    title: item.title, policy_layer: item.policy_layer || "", document_type: item.document_type,
    authority_scope: item.authority_scope || "beijing", region_code: item.region_code,
    issuing_authority: item.issuing_authority, document_number: item.document_number,
    source_url: item.source_url, publish_date: item.publish_date, effective_date: item.effective_date,
    expiry_date: item.expiry_date, validity_status: item.validity_status,
    last_verified_at: item.last_verified_at, replaces_source_id: item.replaces_source_id,
    topics: [...item.topics],
  });
}

async function loadDetail() {
  if (!props.item) return;
  const sourceId = props.item.id;
  detailLoading.value = true;
  detailError.value = "";
  try { detail.value = await getKnowledgeSource(sourceId); }
  catch (error: any) { detailError.value = error.message || String(error); }
  finally { detailLoading.value = false; }
}
async function loadChunks() {
  if (!props.item || chunks.value.length) return;
  chunksLoading.value = true;
  detailError.value = "";
  try { chunks.value = await getKnowledgeSourceChunks(props.item.id); }
  catch (error: any) { detailError.value = error.message || String(error); }
  finally { chunksLoading.value = false; }
}
async function selectTab(value: DetailTab) { activeTab.value = value; if (value === "chunks") await loadChunks(); }
function requestReview(action: "submit" | "return" | "publish" | "archive") {
  if (!props.item) return;
  const note = action === "return" ? window.prompt("请输入退回原因") : "";
  if (action === "return" && note === null) return;
  if ((action === "publish" || action === "archive") && !window.confirm(`确认${action === "publish" ? "发布" : "归档"}《${props.item.title}》吗？`)) return;
  emit("review-source", props.item, action, note || "");
}
function documentTypeLabel(value: string) { return documentTypeOptions.find((item) => item.value === value)?.label || value || "待补充"; }
function topicLabel(value: string) { return topicOptions.find((item) => item.value === value)?.label || value; }
function reviewActionLabel(value: string) { return ({ submit: "提交审核", return: "退回修改", publish: "正式发布", archive: "归档", content_update: "正文更新", metadata_update: "元数据更新" } as Record<string, string>)[value] || value; }

watch(() => props.item, async (item, previous) => {
  if (!item) return;
  if (!previous || item.id !== previous.id) { activeTab.value = "overview"; chunks.value = []; chunkSearch.value = ""; }
  syncDraft(item);
  await loadDetail();
}, { immediate: true });

defineExpose({
  openTab: async (value: DetailTab) => { await nextTick(); await selectTab(value); },
});
</script>

<style scoped>
.knowledge-admin-detail{display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;min-width:0;height:100%;border-left:1px solid var(--border-default);background:var(--surface);box-shadow:-8px 0 22px rgba(28,45,35,.06)}.knowledge-admin-detail-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:16px 18px 12px}.knowledge-admin-detail-head>div{min-width:0}.knowledge-admin-detail-head p{margin:0 0 3px;color:var(--brand);font-size:9px;font-weight:700;letter-spacing:.07em}.knowledge-admin-detail-head h2,.knowledge-admin-detail-head span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.knowledge-admin-detail-head h2{margin:0;color:var(--text-primary);font-size:15px}.knowledge-admin-detail-head span{display:block;margin-top:4px;color:var(--text-muted);font-size:9px}.knowledge-admin-detail-head>button{display:grid;flex:0 0 32px;place-items:center;width:32px;height:32px;padding:0;border:1px solid var(--border-default);border-radius:7px;color:var(--text-secondary);background:var(--surface)}.knowledge-admin-detail-tabs{display:flex;gap:2px;padding:0 14px;border-bottom:1px solid var(--border-default);overflow-x:auto}.knowledge-admin-detail-tabs button{display:flex;align-items:center;gap:4px;min-height:38px;padding:0 8px;border:0;border-bottom:2px solid transparent;color:var(--text-secondary);background:transparent;font-size:10px;white-space:nowrap}.knowledge-admin-detail-tabs button.active{color:var(--brand);border-bottom-color:var(--brand);font-weight:700}.knowledge-admin-detail-tabs small{padding:1px 4px;border-radius:999px;background:var(--surface-subtle);font-size:8px}.knowledge-admin-detail-body{min-height:0;overflow:auto}.knowledge-admin-detail-section,.knowledge-admin-metadata{display:grid;align-content:start;gap:13px;padding:17px}.knowledge-admin-detail-empty{display:grid;place-items:center;align-content:center;gap:7px;min-height:180px;color:var(--text-muted);font-size:11px}.knowledge-admin-status-line{display:flex;flex-wrap:wrap;gap:6px}.knowledge-admin-status-line span{padding:4px 7px;border-radius:999px;color:var(--text-secondary);background:var(--surface-subtle);font-size:10px}.knowledge-admin-status-line .status-published{color:var(--success);background:var(--success-soft)}.knowledge-admin-status-line .status-in_review{color:var(--info);background:var(--info-soft)}.knowledge-admin-status-line .status-draft{color:#9a651f;background:#f8eddf}.knowledge-admin-validation{display:grid;grid-template-columns:20px minmax(0,1fr);gap:8px;padding:10px;border-radius:8px;color:#9a651f;background:#f8eddf;font-size:10px}.knowledge-admin-validation span{display:grid;gap:2px}.knowledge-admin-validation strong{font-size:11px}.knowledge-admin-detail-list{display:grid;grid-template-columns:1fr 1fr;gap:1px;margin:0;border:1px solid var(--border-default);border-radius:8px;overflow:hidden;background:var(--border-default)}.knowledge-admin-detail-list div{min-width:0;padding:9px;background:var(--surface)}.knowledge-admin-detail-list dt{color:var(--text-muted);font-size:9px}.knowledge-admin-detail-list dd{overflow:hidden;margin:3px 0 0;color:var(--text-primary);font-size:10px;text-overflow:ellipsis;white-space:nowrap}.knowledge-admin-topic-list{display:flex;flex-wrap:wrap;gap:5px}.knowledge-admin-topic-list span{padding:3px 6px;border-radius:999px;color:var(--brand);background:var(--brand-soft);font-size:9px}.knowledge-admin-topic-list small{color:var(--text-muted);font-size:10px}.knowledge-admin-official-link,.knowledge-admin-secondary-action{display:inline-flex;width:fit-content;align-items:center;gap:6px;padding:7px 9px;border:1px solid var(--border-default);border-radius:7px;color:var(--brand);background:var(--surface);font-size:10px;text-decoration:none}.knowledge-admin-version-box{padding:10px;border:1px solid var(--border-default);border-radius:8px;background:var(--surface-subtle)}.knowledge-admin-version-box strong{font-size:10px}.knowledge-admin-version-box p,.knowledge-admin-technical p{margin:5px 0 0;color:var(--text-secondary);font-size:9px}.knowledge-admin-technical summary{color:var(--text-secondary);font-size:10px;cursor:pointer}.knowledge-admin-technical p{overflow-wrap:anywhere}.knowledge-admin-technical .danger{color:var(--danger)}.knowledge-admin-metadata fieldset{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin:0;padding:12px;border:1px solid var(--border-default);border-radius:9px}.knowledge-admin-metadata legend{padding:0 5px;color:var(--text-primary);font-size:11px;font-weight:700}.knowledge-admin-metadata label{display:grid;gap:4px;min-width:0;color:var(--text-secondary);font-size:9px}.knowledge-admin-metadata label.wide{grid-column:1/-1}.knowledge-admin-metadata input,.knowledge-admin-metadata select{width:100%;min-width:0;padding:7px;border:1px solid var(--border-default);border-radius:6px;color:var(--text-primary);background:var(--surface);font:inherit;font-size:10px}.knowledge-admin-topic-options{display:flex;grid-column:1/-1;flex-wrap:wrap;gap:7px}.knowledge-admin-topic-options label{display:flex;grid-template-columns:none;align-items:center;gap:4px}.knowledge-admin-topic-options input{width:auto}.knowledge-admin-save{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:34px;border:1px solid var(--brand);border-radius:7px;color:var(--brand-contrast);background:var(--brand);font-size:11px}.knowledge-admin-chunk-search{position:sticky;z-index:1;top:0;display:grid;grid-template-columns:17px minmax(0,1fr);align-items:center;gap:6px;padding:7px 9px;border:1px solid var(--border-default);border-radius:7px;color:var(--text-muted);background:var(--surface)}.knowledge-admin-chunk-search input{min-width:0;border:0;outline:0;color:var(--text-primary);background:transparent;font-size:10px}.knowledge-admin-chunks article{padding:10px;border:1px solid var(--border-default);border-radius:8px;background:var(--surface-subtle)}.knowledge-admin-chunks article header{display:flex;justify-content:space-between;gap:7px}.knowledge-admin-chunks article strong{color:var(--text-primary);font-size:10px}.knowledge-admin-chunks article header span{flex:0 0 auto;color:var(--brand);font-size:9px}.knowledge-admin-chunks article p{margin:7px 0;color:var(--text-secondary);font-size:10px;line-height:1.65;white-space:pre-wrap}.knowledge-admin-chunks article small{color:var(--text-muted);font-size:8px}.knowledge-admin-timeline{display:grid}.knowledge-admin-timeline article{display:grid;grid-template-columns:14px minmax(0,1fr);gap:8px}.knowledge-admin-timeline article>i{position:relative;width:8px;height:8px;margin-top:4px;border:2px solid var(--brand);border-radius:50%;background:var(--surface)}.knowledge-admin-timeline article>i::after{position:absolute;top:8px;bottom:-56px;left:2px;width:1px;background:var(--border-default);content:""}.knowledge-admin-timeline article:last-child>i::after{display:none}.knowledge-admin-timeline article>div{padding-bottom:17px}.knowledge-admin-timeline strong{color:var(--text-primary);font-size:10px}.knowledge-admin-timeline span{float:right;color:var(--text-muted);font-size:8px}.knowledge-admin-timeline p{margin:5px 0;color:var(--text-secondary);font-size:10px}.knowledge-admin-timeline small{color:var(--text-muted);font-size:8px}.knowledge-admin-permission-summary{display:flex;align-items:center;gap:9px;color:var(--brand)}.knowledge-admin-permission-summary span{display:grid;gap:2px}.knowledge-admin-permission-summary strong{color:var(--text-primary);font-size:11px}.knowledge-admin-permission-summary small{color:var(--text-secondary);font-size:9px}.knowledge-admin-permission-editor{display:grid;gap:6px}.knowledge-admin-permission-editor>label{display:grid;grid-template-columns:18px minmax(0,1fr);gap:7px;padding:8px;border:1px solid var(--border-default);border-radius:7px}.knowledge-admin-permission-editor label span{display:grid;gap:2px}.knowledge-admin-permission-editor label strong{font-size:10px}.knowledge-admin-permission-editor label small{color:var(--text-muted);font-size:8px}.knowledge-admin-permission-editor>div{display:flex;gap:7px;margin-top:4px}.knowledge-admin-permission-editor button,.knowledge-admin-detail-actions button{display:inline-flex;align-items:center;justify-content:center;gap:5px;padding:7px 9px;border:1px solid var(--border-default);border-radius:7px;color:var(--text-secondary);background:var(--surface);font-size:10px}.knowledge-admin-permission-editor button.primary,.knowledge-admin-detail-actions button.primary{color:var(--brand-contrast);border-color:var(--brand);background:var(--brand)}.knowledge-admin-detail-actions{position:relative;display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:57px;padding:10px 16px;border-top:1px solid var(--border-default);background:var(--surface)}.knowledge-admin-review-actions{display:flex;gap:7px}.knowledge-admin-more-actions{position:relative;margin-left:auto}.knowledge-admin-more-actions summary{display:grid;place-items:center;width:32px;height:32px;border:1px solid var(--border-default);border-radius:7px;color:var(--text-secondary);cursor:pointer;list-style:none}.knowledge-admin-more-actions summary::-webkit-details-marker{display:none}.knowledge-admin-more-actions button{position:absolute;z-index:4;right:0;bottom:39px;width:126px;box-shadow:var(--shadow-raised)}.knowledge-admin-more-actions button.danger{color:var(--danger);border-color:color-mix(in srgb,var(--danger) 35%,var(--border-default));background:var(--surface)}.knowledge-admin-detail-error{display:grid;grid-template-columns:18px minmax(0,1fr) auto;align-items:center;gap:7px;margin:8px 14px 0;padding:8px;border-radius:7px;color:var(--danger);background:var(--danger-soft);font-size:9px}.knowledge-admin-detail-error button{border:0;color:inherit;background:transparent;font-weight:700}
@media(max-width:620px){.knowledge-admin-detail{position:absolute;z-index:10;inset:0;border-left:0}.knowledge-admin-detail-list,.knowledge-admin-metadata fieldset{grid-template-columns:1fr}.knowledge-admin-metadata label.wide{grid-column:1}.knowledge-admin-detail-tabs{padding:0 8px}.knowledge-admin-detail-section,.knowledge-admin-metadata{padding:14px}}
.knowledge-admin-detail{min-height:0;max-height:100%;overflow:hidden}
.knowledge-admin-detail-body{min-height:0;overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch}
</style>
