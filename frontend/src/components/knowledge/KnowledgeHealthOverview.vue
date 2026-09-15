<template>
  <div class="knowledge-admin-health">
    <section class="knowledge-admin-metrics" aria-label="知识库健康指标">
      <article>
        <FileText :size="18" />
        <span>知识来源<strong>{{ files.length }}</strong></span>
      </article>
      <article>
        <Layers3 :size="18" />
        <span>结构片段<strong>{{ totalChunks }}</strong></span>
      </article>
      <article :class="{ warning: vectorCoverage < 100 }">
        <Database :size="18" />
        <span>向量覆盖<strong>{{ vectorCoverage }}%</strong></span>
      </article>
      <article :class="{ warning: pendingReview > 0 }">
        <Clock3 :size="18" />
        <span>待办审核<strong>{{ pendingReview }}</strong></span>
      </article>
      <article :class="{ danger: validationIssues > 0 }">
        <ShieldAlert :size="18" />
        <span>发布异常<strong>{{ validationIssues }}</strong></span>
      </article>
    </section>

    <section class="knowledge-admin-health-grid">
      <article class="knowledge-admin-panel knowledge-admin-vector-card">
        <header>
          <div>
            <p>检索基础设施</p>
            <h3>{{ statusLabel }}</h3>
          </div>
          <span class="knowledge-admin-health-dot" :class="statusTone"></span>
        </header>
        <dl v-if="status">
          <div><dt>Embedding 模型</dt><dd>{{ status.model }}</dd></div>
          <div><dt>向量覆盖</dt><dd>{{ status.vector_count }} / {{ status.database_chunk_count }}</dd></div>
          <div><dt>检索模式</dt><dd>{{ status.available ? '向量 + BM25 混合检索' : 'BM25 降级检索' }}</dd></div>
          <div><dt>设备</dt><dd>{{ status.device || 'CPU' }}</dd></div>
        </dl>
        <p v-else class="knowledge-admin-muted">正在读取向量服务状态…</p>
        <p v-if="status?.error" class="knowledge-admin-inline-error">{{ status.error }}</p>
        <footer>
          <button type="button" :disabled="Boolean(operation) || loading" @click="$emit('refresh')">
            <RefreshCw :size="15" :class="{ 'spin-icon': loading }" />刷新状态
          </button>
          <button
            type="button"
            :class="{ primary: Boolean(status && (!status.available || status.rebuild_required)) }"
            :disabled="Boolean(operation)"
            @click="$emit('rebuild')"
          >
            <Wrench :size="15" />重建索引
          </button>
        </footer>
      </article>

      <article class="knowledge-admin-panel">
        <header><div><p>资料构成</p><h3>分类分布</h3></div></header>
        <div class="knowledge-admin-distribution">
          <button v-for="item in categoryCounts" :key="item.value" type="button" @click="$emit('filter', 'category', item.value)">
            <span><i :class="`category-${item.value}`"></i>{{ item.label }}</span><strong>{{ item.count }}</strong>
          </button>
        </div>
      </article>
    </section>

    <section class="knowledge-admin-panel knowledge-admin-layer-panel">
      <header><div><p>乡村振兴</p><h3>四层知识结构</h3></div><span>{{ ruralFiles.length }} 份资料</span></header>
      <div class="knowledge-admin-layer-grid">
        <button v-for="layer in layerCounts" :key="layer.value" type="button" @click="$emit('filter', 'layer', layer.value)">
          <span>{{ layer.label }}</span><strong>{{ layer.count }}</strong><ChevronRight :size="16" />
        </button>
      </div>
    </section>

    <section class="knowledge-admin-panel knowledge-admin-issue-panel">
      <header>
        <div><p>需要关注</p><h3>问题与待办队列</h3></div>
        <span>{{ issues.length ? `${issues.length} 项` : '全部正常' }}</span>
      </header>
      <div v-if="issues.length" class="knowledge-admin-issue-list">
        <button v-for="issue in issues" :key="issue.item.id" type="button" @click="$emit('open-source', issue.item)">
          <AlertTriangle :size="17" :class="issue.tone" />
          <span><strong>{{ issue.item.title || issue.item.source }}</strong><small>{{ issue.reasons.join(' · ') }}</small></span>
          <ChevronRight :size="16" />
        </button>
      </div>
      <div v-else class="knowledge-admin-healthy-empty"><ShieldCheck :size="24" /><span>没有发现索引、审核或政策效力问题</span></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { AlertTriangle, ChevronRight, Clock3, Database, FileText, Layers3, RefreshCw, ShieldAlert, ShieldCheck, Wrench } from "lucide-vue-next";
import type { CurriculumFileItem, CurriculumVectorStatus } from "@/types";

const props = defineProps<{
  files: CurriculumFileItem[];
  totalChunks: number;
  status: CurriculumVectorStatus | null;
  statusLabel: string;
  loading: boolean;
  operation: string;
}>();

defineEmits<{
  rebuild: [];
  refresh: [];
  filter: [kind: "category" | "layer", value: string];
  "open-source": [item: CurriculumFileItem];
}>();

const ruralFiles = computed(() => props.files.filter((item) => item.category === "rural_revitalization"));
const vectorCoverage = computed(() => {
  const chunks = props.files.reduce((sum, item) => sum + item.chunk_count, 0);
  const vectors = props.files.reduce((sum, item) => sum + item.vector_chunk_count, 0);
  return chunks ? Math.min(100, Math.round((vectors / chunks) * 100)) : 100;
});
const pendingReview = computed(() => props.files.filter((item) => ["draft", "in_review"].includes(item.review_status)).length);
const validationIssues = computed(() => props.files.filter((item) => item.publish_errors.length > 0).length);
const statusTone = computed(() => props.status?.available && !props.status.rebuild_required ? "ready" : props.status?.error ? "danger" : "warning");

const categoryCounts = computed(() => [
  { value: "curriculum", label: "课程与课标", count: props.files.filter((item) => item.category === "curriculum").length },
  { value: "ecology", label: "昆虫与植物生态", count: props.files.filter((item) => item.category === "ecology").length },
  { value: "rural_revitalization", label: "乡村振兴", count: ruralFiles.value.length },
]);

const layerCounts = computed(() => [
  ["foundation", "基础法规"], ["annual_action", "年度任务"],
  ["ceo_talent", "CEO与人才"], ["grassroots_compliance", "基层合规"],
].map(([value, label]) => ({ value, label, count: ruralFiles.value.filter((item) => item.policy_layer === value).length })));

const issues = computed(() => props.files.flatMap((item) => {
  const reasons: string[] = [];
  let tone = "warning";
  if (item.vector_status === "error" || item.vector_chunk_count !== item.chunk_count) {
    reasons.push(item.last_error || `向量 ${item.vector_chunk_count}/${item.chunk_count}`);
    tone = "danger";
  }
  if (item.review_status === "draft") reasons.push("草稿待提交");
  if (item.review_status === "in_review") reasons.push("等待审核");
  if (item.publish_errors.length) reasons.push(`发布前待补 ${item.publish_errors.length} 项`);
  if (item.category === "rural_revitalization" && ["unknown", "expired", "repealed"].includes(item.validity_status)) {
    reasons.push(item.validity_status === "unknown" ? "效力待核验" : item.validity_status === "expired" ? "已过期" : "已废止");
  }
  return reasons.length ? [{ item, reasons, tone }] : [];
}).sort((a, b) => (a.tone === "danger" ? -1 : 1) - (b.tone === "danger" ? -1 : 1)));
</script>

<style scoped>
.knowledge-admin-health{display:grid;gap:16px;max-width:1380px;margin:0 auto;padding:20px 24px 32px}.knowledge-admin-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.knowledge-admin-metrics article{display:flex;align-items:center;gap:11px;min-width:0;padding:16px;border:1px solid var(--border-default);border-radius:11px;background:var(--surface);color:var(--brand)}.knowledge-admin-metrics article.warning{color:#a4691c;background:#fffaf1}.knowledge-admin-metrics article.danger{color:var(--danger);background:var(--danger-soft)}.knowledge-admin-metrics span{display:grid;gap:4px;color:var(--text-secondary);font-size:11px}.knowledge-admin-metrics strong{color:var(--text-primary);font-size:22px;line-height:1}.knowledge-admin-health-grid{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,.75fr);gap:14px}.knowledge-admin-panel{min-width:0;padding:18px;border:1px solid var(--border-default);border-radius:12px;background:var(--surface);box-shadow:var(--shadow-soft)}.knowledge-admin-panel header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:15px}.knowledge-admin-panel header p{margin:0 0 3px;color:var(--text-muted);font-size:10px;font-weight:700;letter-spacing:.08em}.knowledge-admin-panel h3{margin:0;color:var(--text-primary);font-size:15px}.knowledge-admin-panel header>span{color:var(--text-secondary);font-size:11px}.knowledge-admin-health-dot{width:9px;height:9px;margin-top:5px;border-radius:50%;background:var(--text-muted);box-shadow:0 0 0 4px var(--surface-subtle)}.knowledge-admin-health-dot.ready{background:var(--success)}.knowledge-admin-health-dot.warning{background:#c9872b}.knowledge-admin-health-dot.danger{background:var(--danger)}.knowledge-admin-vector-card dl{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:0}.knowledge-admin-vector-card dl div{min-width:0;padding:10px;border-radius:8px;background:var(--surface-subtle)}.knowledge-admin-vector-card dt{color:var(--text-muted);font-size:10px}.knowledge-admin-vector-card dd{overflow:hidden;margin:4px 0 0;color:var(--text-primary);font-size:12px;text-overflow:ellipsis;white-space:nowrap}.knowledge-admin-vector-card footer{display:flex;gap:8px;margin-top:14px}.knowledge-admin-vector-card button,.knowledge-admin-distribution button,.knowledge-admin-layer-grid button,.knowledge-admin-issue-list button{border:1px solid var(--border-default);color:var(--text-secondary);background:var(--surface);cursor:pointer}.knowledge-admin-vector-card button{display:inline-flex;align-items:center;gap:6px;padding:7px 9px;border-radius:7px;font-size:11px}.knowledge-admin-vector-card button.primary{color:var(--brand-contrast);border-color:var(--brand);background:var(--brand)}.knowledge-admin-distribution{display:grid;gap:7px}.knowledge-admin-distribution button{display:flex;align-items:center;justify-content:space-between;padding:10px;border-radius:8px}.knowledge-admin-distribution button span{display:flex;align-items:center;gap:8px;font-size:11px}.knowledge-admin-distribution i{width:8px;height:8px;border-radius:50%;background:var(--info)}.knowledge-admin-distribution i.category-ecology{background:var(--success)}.knowledge-admin-distribution i.category-rural_revitalization{background:#b5792d}.knowledge-admin-distribution strong{color:var(--text-primary);font-size:15px}.knowledge-admin-layer-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.knowledge-admin-layer-grid button{display:grid;grid-template-columns:minmax(0,1fr) auto auto;align-items:center;gap:8px;padding:13px;border-radius:9px;text-align:left}.knowledge-admin-layer-grid button:hover,.knowledge-admin-distribution button:hover,.knowledge-admin-issue-list button:hover{color:var(--brand);border-color:var(--brand);background:var(--brand-soft)}.knowledge-admin-layer-grid span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}.knowledge-admin-layer-grid strong{color:var(--text-primary);font-size:18px}.knowledge-admin-issue-list{display:grid;border-top:1px solid var(--border-default)}.knowledge-admin-issue-list button{display:grid;grid-template-columns:20px minmax(0,1fr) 16px;align-items:center;gap:10px;padding:12px 4px;border:0;border-bottom:1px solid var(--border-default);text-align:left}.knowledge-admin-issue-list button>span{display:grid;gap:3px;min-width:0}.knowledge-admin-issue-list strong,.knowledge-admin-issue-list small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.knowledge-admin-issue-list strong{color:var(--text-primary);font-size:12px}.knowledge-admin-issue-list small{color:var(--text-secondary);font-size:10px}.knowledge-admin-issue-list .warning{color:#b5792d}.knowledge-admin-issue-list .danger{color:var(--danger)}.knowledge-admin-healthy-empty{display:grid;place-items:center;gap:8px;min-height:110px;color:var(--success);font-size:12px}.knowledge-admin-muted{color:var(--text-muted);font-size:11px}.knowledge-admin-inline-error{margin:10px 0 0;color:var(--danger);font-size:11px}
@media(max-width:1050px){.knowledge-admin-metrics{grid-template-columns:repeat(3,1fr)}.knowledge-admin-health-grid{grid-template-columns:1fr}.knowledge-admin-layer-grid{grid-template-columns:1fr 1fr}}
@media(max-width:620px){.knowledge-admin-health{padding:14px}.knowledge-admin-metrics{grid-template-columns:1fr 1fr}.knowledge-admin-metrics article:last-child{grid-column:1/-1}.knowledge-admin-layer-grid,.knowledge-admin-vector-card dl{grid-template-columns:1fr}}
</style>
