<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <section class="curriculum-modal" role="dialog" aria-modal="true" aria-labelledby="curriculum-title">
      <header class="curriculum-modal-head"><div><p class="section-kicker">课程知识库</p><h2 id="curriculum-title">课标知识库</h2><span>{{ admin ? '管理员管理' : '只读查看' }} · {{ files.length }} 个文件 · {{ totalChunks }} 个片段</span></div><button class="close-button" type="button" @click="$emit('close')"><X :size="18" />关闭</button></header>
      <section v-if="admin" class="curriculum-control-panel">
        <div class="vector-summary"><Database :size="20" /><span><strong>{{ statusLabel }}</strong><small v-if="status">{{ status.model }} · {{ status.vector_count }}/{{ status.database_chunk_count }} 个向量</small><small v-else>正在读取向量服务状态</small></span></div>
        <div class="curriculum-admin-actions"><button type="button" :disabled="Boolean(operation) || loadingAdmin" @click="$emit('rebuild')"><RefreshCw :size="15" />重建索引</button><button type="button" :disabled="Boolean(operation)" @click="$emit('export')"><Download :size="15" />导出知识库</button><button type="button" :disabled="Boolean(operation)" @click="$emit('import')"><Upload :size="15" />导入知识库</button><input ref="bundleInput" class="visually-hidden" type="file" accept=".zip,application/zip" @change="$emit('bundle-selected', $event)" /></div>
      </section>
      <button v-if="admin" class="curriculum-dropzone" type="button" :disabled="uploading" @click="$emit('pick-files')" @dragover.prevent @drop.prevent="$emit('drop-files', $event)"><Upload :size="21" /><strong>{{ uploading ? '正在导入课标' : '上传课标文件' }}</strong><span>PDF / DOCX / TXT / MD，单文件最大 20 MB</span></button>
      <input v-if="admin" ref="fileInput" class="visually-hidden" type="file" multiple accept=".pdf,.docx,.txt,.md" @change="$emit('files-selected', $event)" />
      <div v-if="uploadResults.length" class="curriculum-upload-results"><span v-for="result in uploadResults" :key="result.name" :class="`status-${result.status}`">{{ result.name }} · {{ result.status === 'success' ? '完成' : result.status === 'failed' ? '失败' : '等待' }}</span></div>
      <p v-if="error" class="curriculum-error">{{ error }}</p>
      <div v-if="loading" class="curriculum-empty"><LoaderCircle class="spin-icon" :size="20" />正在读取课标列表</div>
      <div v-else-if="files.length" class="curriculum-file-list">
        <article v-for="item in files" :key="item.source" class="curriculum-file-row"><FileText :size="19" /><div class="curriculum-file-copy"><strong :title="item.source">{{ item.source }}</strong><span>{{ item.extension.replace('.', '').toUpperCase() }} · {{ item.chunk_count }} 个片段 · {{ formatDate(item.updated_at) }}</span><small :class="`vector-status-${item.vector_status}`">{{ vectorLabel(item) }}</small><div class="curriculum-permission-tags"><span v-if="!item.allowed_expert_ids.length" class="permission-unassigned">尚未授权专家</span><span v-for="id in item.allowed_expert_ids" :key="id" class="permission-tag">{{ expertName(id) }}</span></div><div v-if="editingSource === item.source" class="curriculum-permission-editor"><label v-for="expert in experts" :key="expert.id"><input :checked="permissionDraft.includes(expert.id)" type="checkbox" @change="$emit('toggle-permission', expert.id)" />{{ expert.name }} · {{ expert.role }}</label><div><button type="button" :disabled="savingSource === item.source" @click="$emit('save-permissions', item)">保存权限</button><button type="button" @click="$emit('cancel-permissions')">取消</button></div></div></div><button v-if="admin" type="button" @click="$emit('edit-permissions', item)">配置权限</button><button v-if="admin" class="delete-file-button" type="button" :disabled="deletingSources.includes(item.source) || uploading" @click="$emit('delete-file', item)"><LoaderCircle v-if="deletingSources.includes(item.source)" class="spin-icon" :size="14" /><Trash2 v-else :size="16" /></button></article>
      </div>
      <div v-else class="curriculum-empty"><BookOpen :size="24" />当前还没有导入课标</div>
      <section v-if="admin" class="curriculum-retrieval-section"><div class="curriculum-section-head"><strong><History :size="17" />最近召回</strong><button type="button" :disabled="loadingAdmin" @click="$emit('refresh-admin')"><RefreshCw :size="15" /></button></div><details v-for="record in retrievals" :key="record.id" class="curriculum-retrieval-row"><summary>{{ record.query || '空查询' }}<small>{{ modeLabel(record.mode) }} · {{ formatDate(record.created_at) }}</small></summary><p v-if="record.vector_error" class="curriculum-error">{{ record.vector_error }}</p><div v-for="hit in record.records" :key="`${record.id}-${hit.chunk_id}`" class="retrieval-hit"><strong>{{ hit.source }} · 片段 {{ hit.source_index }}</strong><span>综合 {{ score(hit.score) }} · 向量 {{ score(hit.vector_score) }} · BM25 {{ score(hit.bm25_score) }}</span><p>{{ hit.content }}</p></div><p v-if="!record.records.length" class="retrieval-empty">本次没有命中课标片段。</p></details><p v-if="!retrievals.length" class="retrieval-empty">当前还没有课标召回记录</p></section>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { BookOpen, Database, Download, FileText, History, LoaderCircle, RefreshCw, Trash2, Upload, X } from "lucide-vue-next";
import type { CurriculumFileItem, CurriculumRetrievalRecord, CurriculumVectorStatus, ExpertAgentItem } from "@/types";

defineProps<{
  visible: boolean; admin: boolean; files: CurriculumFileItem[]; totalChunks: number; status: CurriculumVectorStatus | null; statusLabel: string; operation: string; loading: boolean; loadingAdmin: boolean; uploading: boolean; error: string;
  uploadResults: { name: string; status: 'pending' | 'success' | 'failed'; message: string }[]; experts: ExpertAgentItem[]; editingSource: string; permissionDraft: string[]; savingSource: string; deletingSources: string[]; retrievals: CurriculumRetrievalRecord[];
  formatDate: (value: string) => string; vectorLabel: (item: CurriculumFileItem) => string; expertName: (id: string) => string; modeLabel: (mode: string) => string; score: (value: number) => string;
}>();
defineEmits(['close', 'rebuild', 'export', 'import', 'bundle-selected', 'pick-files', 'drop-files', 'files-selected', 'toggle-permission', 'save-permissions', 'cancel-permissions', 'edit-permissions', 'delete-file', 'refresh-admin']);
const fileInput = ref<HTMLInputElement | null>(null);
const bundleInput = ref<HTMLInputElement | null>(null);
defineExpose({ openFilePicker: () => fileInput.value?.click(), openBundlePicker: () => bundleInput.value?.click() });
</script>
