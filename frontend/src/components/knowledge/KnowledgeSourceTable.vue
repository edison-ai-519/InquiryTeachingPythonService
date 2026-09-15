<template>
  <div class="knowledge-admin-table-wrap">
    <table class="knowledge-admin-table">
      <thead>
        <tr>
          <th>资料名称</th><th>分类与层次</th><th>地域与机关</th><th>效力</th><th>审核</th><th>片段 / 向量</th><th>更新时间</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in files"
          :key="item.id || item.source"
          :class="{ selected: item.id === selectedId }"
          tabindex="0"
          @click="$emit('select', item)"
          @keydown.enter="$emit('select', item)"
        >
          <td data-label="资料名称">
            <div class="knowledge-admin-source-title">
              <FileText :size="17" />
              <span><strong :title="item.title || item.source">{{ item.title || item.source }}</strong><small :title="item.source">{{ item.source }}</small></span>
            </div>
          </td>
          <td data-label="分类与层次">
            <span :class="`knowledge-admin-pill category-${item.category}`">{{ categoryLabel(item.category) }}</span>
            <small v-if="item.category === 'rural_revitalization'">{{ layerLabel(item.policy_layer) }}</small>
          </td>
          <td data-label="地域与机关">
            <strong class="knowledge-admin-cell-main">{{ scopeLabel(item.authority_scope) }}</strong>
            <small :title="item.issuing_authority">{{ item.issuing_authority || '发文机关待补' }}</small>
          </td>
          <td data-label="效力"><span :class="`knowledge-admin-pill validity-${item.validity_status}`">{{ validityLabel(item.validity_status) }}</span></td>
          <td data-label="审核"><span :class="`knowledge-admin-pill review-${item.review_status}`">{{ reviewLabel(item.review_status) }}</span></td>
          <td data-label="片段 / 向量">
            <strong class="knowledge-admin-cell-main">{{ item.chunk_count }} / {{ item.vector_chunk_count }}</strong>
            <small :class="`vector-${item.vector_status}`">{{ vectorLabel(item) }}</small>
          </td>
          <td data-label="更新时间"><span class="knowledge-admin-date">{{ formatDate(item.updated_at) }}</span></td>
        </tr>
      </tbody>
    </table>
    <div v-if="loading" class="knowledge-admin-table-empty"><LoaderCircle class="spin-icon" :size="20" />正在读取知识资料</div>
    <div v-else-if="!files.length" class="knowledge-admin-table-empty"><BookOpen :size="24" />当前筛选条件下没有资料</div>
  </div>
</template>

<script setup lang="ts">
import { BookOpen, FileText, LoaderCircle } from "lucide-vue-next";
import type { CurriculumFileItem } from "@/types";

defineProps<{
  files: CurriculumFileItem[];
  selectedId: string;
  loading: boolean;
  formatDate: (value: string) => string;
  vectorLabel: (item: CurriculumFileItem) => string;
  categoryLabel: (value: CurriculumFileItem["category"]) => string;
  layerLabel: (value: CurriculumFileItem["policy_layer"]) => string;
  scopeLabel: (value: string) => string;
  validityLabel: (value: string) => string;
  reviewLabel: (value: string) => string;
}>();

defineEmits<{ select: [item: CurriculumFileItem] }>();
</script>

<style scoped>
.knowledge-admin-table-wrap{min-width:0;height:100%;overflow:auto;background:var(--surface)}.knowledge-admin-table{width:100%;min-width:970px;border-collapse:separate;border-spacing:0;table-layout:fixed}.knowledge-admin-table th{position:sticky;z-index:2;top:0;padding:10px 12px;border-bottom:1px solid var(--border-default);color:var(--text-muted);background:var(--surface-subtle);font-size:10px;font-weight:700;text-align:left;letter-spacing:.03em}.knowledge-admin-table th:first-child{width:27%}.knowledge-admin-table th:nth-child(2){width:13%}.knowledge-admin-table th:nth-child(3){width:16%}.knowledge-admin-table th:nth-child(4),.knowledge-admin-table th:nth-child(5){width:9%}.knowledge-admin-table th:nth-child(6){width:14%}.knowledge-admin-table th:nth-child(7){width:12%}.knowledge-admin-table td{min-width:0;padding:11px 12px;border-bottom:1px solid var(--border-default);color:var(--text-secondary);font-size:11px;vertical-align:middle}.knowledge-admin-table tbody tr{cursor:pointer;outline:none}.knowledge-admin-table tbody tr:hover,.knowledge-admin-table tbody tr:focus-visible{background:var(--surface-subtle)}.knowledge-admin-table tbody tr.selected{background:var(--brand-soft);box-shadow:inset 3px 0 0 var(--brand)}.knowledge-admin-source-title{display:grid;grid-template-columns:20px minmax(0,1fr);align-items:center;gap:8px;min-width:0;color:var(--brand)}.knowledge-admin-source-title>span,.knowledge-admin-table td:nth-child(2),.knowledge-admin-table td:nth-child(3),.knowledge-admin-table td:nth-child(6){display:grid;gap:3px;min-width:0}.knowledge-admin-source-title strong,.knowledge-admin-source-title small,.knowledge-admin-table td small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.knowledge-admin-source-title strong,.knowledge-admin-cell-main{color:var(--text-primary);font-size:11px}.knowledge-admin-source-title small,.knowledge-admin-table td small{color:var(--text-muted);font-size:9px}.knowledge-admin-pill{display:inline-flex;width:fit-content;max-width:100%;align-items:center;padding:3px 6px;border-radius:999px;color:var(--text-secondary);background:var(--surface-subtle);font-size:10px;white-space:nowrap}.knowledge-admin-pill.category-curriculum{color:var(--info);background:var(--info-soft)}.knowledge-admin-pill.category-ecology,.knowledge-admin-pill.review-published,.knowledge-admin-pill.validity-current{color:var(--success);background:var(--success-soft)}.knowledge-admin-pill.category-rural_revitalization,.knowledge-admin-pill.review-draft,.knowledge-admin-pill.validity-unknown{color:#9a651f;background:#f8eddf}.knowledge-admin-pill.review-in_review{color:var(--info);background:var(--info-soft)}.knowledge-admin-pill.review-archived,.knowledge-admin-pill.validity-not_applicable{color:var(--text-muted);background:var(--surface-subtle)}.knowledge-admin-pill.validity-expired,.knowledge-admin-pill.validity-repealed{color:var(--danger);background:var(--danger-soft)}.knowledge-admin-table .vector-ready{color:var(--success)}.knowledge-admin-table .vector-error{color:var(--danger)}.knowledge-admin-date{display:block;color:var(--text-secondary);font-variant-numeric:tabular-nums;white-space:nowrap}.knowledge-admin-table-empty{display:grid;place-items:center;align-content:center;gap:8px;min-height:260px;color:var(--text-muted);font-size:11px}
@media(max-width:760px){.knowledge-admin-table{display:block;min-width:0}.knowledge-admin-table thead{display:none}.knowledge-admin-table tbody{display:grid}.knowledge-admin-table tr{display:grid;grid-template-columns:1fr 1fr;gap:9px;padding:14px;border-bottom:1px solid var(--border-default)}.knowledge-admin-table td{display:grid!important;gap:3px!important;padding:0;border:0}.knowledge-admin-table td:first-child{grid-column:1/-1}.knowledge-admin-table td::before{content:attr(data-label);color:var(--text-muted);font-size:9px}.knowledge-admin-table tr.selected{box-shadow:inset 3px 0 0 var(--brand)}}
</style>
