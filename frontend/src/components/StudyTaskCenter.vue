<template>
  <div class="task-center-backdrop" @click.self="$emit('close')">
    <section class="task-center" role="dialog" aria-modal="true" :aria-label="isManager ? '研学项目管理' : '工作台任务大厅'">
      <header class="task-center-head">
        <div>
          <p>FIELDWORK COORDINATION</p>
          <h2>{{ isManager ? '研学项目与任务' : '工作台任务大厅' }}</h2>
          <span>{{ isManager ? '以基地场景为起点，向三类工作台派发任务并汇集报告。' : `${roleLabel}工作流完成后会自动提交分类报告。` }}</span>
        </div>
        <div class="head-actions">
          <button class="secondary-button" type="button" :disabled="loading" @click="reload">{{ loading ? '刷新中…' : '刷新' }}</button>
          <button class="close-button" type="button" aria-label="关闭" @click="$emit('close')"><X :size="18" /></button>
        </div>
      </header>

      <p v-if="error" class="task-error" role="alert">{{ error }}</p>
      <div v-if="loading && !projects.length && !availableTasks.length" class="task-empty">正在读取项目和任务…</div>

      <section v-else-if="isManager" class="manager-layout">
        <aside class="project-list-pane">
          <button class="create-project-card" type="button" @click="startNewProject"><Plus :size="17" />新建研学项目</button>
          <button v-for="project in projects" :key="project.id" class="project-list-item" :class="{ selected: selectedProject?.id === project.id }" type="button" @click="selectProject(project.id)">
            <strong>{{ project.name }}</strong>
            <span>{{ project.location || '未填写地点' }}</span>
            <small>{{ projectStatus(project.status) }} · {{ project.tasks.length }} 个任务</small>
          </button>
          <p v-if="!projects.length" class="task-empty compact">还没有研学项目</p>
        </aside>

        <main class="project-editor">
          <template v-if="creatingProject || selectedProject">
            <form v-if="creatingProject" class="project-form" @submit.prevent="submitNewProject">
              <div class="section-title"><div><small>NEW PROJECT</small><h3>创建研学项目</h3></div></div>
              <label>项目名称<input v-model="projectDraft.name" required maxlength="200" placeholder="例如：古道自然观察研学" /></label>
              <label>场景地点<input v-model="projectDraft.location" maxlength="500" placeholder="基地、场地或区域" /></label>
              <label>场景说明<textarea v-model="projectDraft.scene_description" rows="3" maxlength="10000" placeholder="描述场景特点、观察对象与活动背景" /></label>
              <label>物料清单<textarea v-model="projectDraft.materialsText" rows="3" placeholder="每行一项，例如：放大镜、记录板" /></label>
              <footer><button class="secondary-button" type="button" @click="creatingProject = false">取消</button><button class="primary-button" type="submit" :disabled="saving">创建项目</button></footer>
            </form>

            <template v-else-if="selectedProject">
              <div class="project-title-row">
                <div><small>PROJECT · {{ projectStatus(selectedProject.status) }}</small><h3>{{ selectedProject.name }}</h3></div>
                <div class="project-actions">
                  <button v-if="selectedProject.status === 'draft'" class="primary-button" type="button" :disabled="saving" @click="publishProject">发布任务</button>
                  <button v-if="selectedProject.status === 'active'" class="secondary-button" type="button" :disabled="saving" @click="closeProject">结束项目</button>
                </div>
              </div>

              <form class="project-form compact-form" @submit.prevent="saveProject">
                <div class="form-grid">
                  <label>项目名称<input v-model="projectDraft.name" required maxlength="200" :disabled="selectedProject.status === 'closed'" /></label>
                  <label>场景地点<input v-model="projectDraft.location" maxlength="500" :disabled="selectedProject.status === 'closed'" /></label>
                </div>
                <label>统一场景说明<textarea v-model="projectDraft.scene_description" rows="3" maxlength="10000" :disabled="selectedProject.status === 'closed'" /></label>
                <label>物料清单<textarea v-model="projectDraft.materialsText" rows="3" placeholder="每行一项" :disabled="selectedProject.status === 'closed'" /></label>
                <div class="form-footer"><button v-if="selectedProject.status !== 'closed'" class="secondary-button" type="submit" :disabled="saving">保存场景</button></div>
              </form>

              <section class="attachment-section">
                <div class="section-title"><div><small>SCENE MATERIALS</small><h4>场景附件</h4></div><label v-if="selectedProject.status !== 'closed'" class="upload-button"><Upload :size="15" />上传<input type="file" accept=".pdf,.docx,.txt,.md" @change="uploadFile" /></label></div>
                <div v-if="selectedProject.files.length" class="attachment-list">
                  <div v-for="file in selectedProject.files" :key="file.id"><button type="button" @click="downloadFile(file)"><FileText :size="15" /><span>{{ file.name }}<small>{{ file.status === 'ready' ? '可查看' : file.status === 'failed' ? file.error_message || '处理失败' : '处理中' }}</small></span></button><button v-if="selectedProject.status !== 'closed'" class="remove-file" type="button" title="删除附件" @click="removeFile(file.id)"><X :size="15" /></button></div>
                </div>
                <p v-else class="muted-empty">上传 PDF、DOCX、TXT 或 MD，任务领取者可以查看场景资料。</p>
              </section>

              <section v-if="selectedProject.status !== 'closed'" class="task-builder">
                <div class="section-title"><div><small>TASK DISPATCH</small><h4>{{ editingTaskId ? '编辑任务' : '制定工作台任务' }}</h4></div></div>
                <form class="project-form" @submit.prevent="saveTask">
                  <label>目标工作台<select v-model="taskDraft.target_role" :disabled="Boolean(editingTaskId && editingTaskHasSubmissions)" @change="loadTaskFlows"><option value="teacher">教师工作台</option><option value="parent">家长工作台</option><option value="study_travel">研学基地工作台</option></select></label>
                  <label>任务标题<input v-model="taskDraft.title" required maxlength="200" placeholder="说明这类工作台要完成什么" /></label>
                  <label>任务要求<textarea v-model="taskDraft.description" rows="2" maxlength="10000" placeholder="具体要求、产出重点和注意事项" /></label>
                  <label>对应工作流<select v-model="taskDraft.flow_name" required><option v-for="flow in taskFlows" :key="flow.name" :value="flow.name">{{ flow.display_name }} · {{ flow.stage_count }}阶段</option></select></label>
                  <p v-if="editingTaskHasSubmissions" class="inline-note">任务已有人领取，目标工作台和工作流已锁定。</p>
                  <footer><button v-if="editingTaskId" class="secondary-button" type="button" @click="cancelTaskEdit">取消编辑</button><button class="primary-button" type="submit" :disabled="saving || !taskFlows.length">{{ editingTaskId ? '保存任务' : '添加任务' }}</button></footer>
                </form>
              </section>

              <section class="task-list-section">
                <div class="section-title"><div><small>WORKSTREAMS</small><h4>三类工作台任务</h4></div></div>
                <article v-for="task in selectedProject.tasks" :key="task.id" class="manager-task-card">
                  <div class="manager-task-head"><div><span class="role-chip" :class="task.target_role">{{ roleName(task.target_role) }}</span><strong>{{ task.title }}</strong><small>{{ task.flow_display_name }} · {{ taskStatus(task.status) }} · {{ task.submitted_count || 0 }}/{{ task.submission_count || 0 }} 份报告</small></div><div v-if="selectedProject.status !== 'closed' && task.status !== 'closed'" class="task-actions"><button class="text-button" type="button" @click="editTask(task)">编辑</button><button class="text-button danger-text" type="button" @click="closeTask(task)">关闭</button></div></div>
                  <p v-if="task.description" class="task-description">{{ task.description }}</p>
                  <details v-if="task.submissions?.length" class="submission-list"><summary>执行记录与提交报告（{{ task.submissions.length }}）</summary><article v-for="submission in task.submissions" :key="submission.id" class="submission-item"><div><strong>{{ submission.username }}</strong><span>{{ submission.status === 'submitted' ? `已提交 · ${formatDate(submission.submitted_at)}` : `进行中 · ${formatDate(submission.claimed_at)}` }}</span></div><pre v-if="submission.report_markdown">{{ submission.report_markdown }}</pre><p v-else class="muted-empty">工作流完成后会自动生成报告。</p></article></details>
                </article>
                <p v-if="!selectedProject.tasks.length" class="muted-empty">先添加教师、家长或基地任务，再发布项目。</p>
              </section>

              <section class="summary-section">
                <div class="section-title"><div><small>PROJECT REPORT</small><h4>基地人工汇总</h4></div><button class="secondary-button" type="button" :disabled="saving" @click="saveSummary">保存汇总</button></div>
                <textarea v-model="summaryDraft" rows="7" placeholder="查看各类任务提交报告后，在此整理项目成果。支持 Markdown。" />
              </section>
            </template>
          </template>
          <div v-else class="project-placeholder"><Layers3 :size="30" /><strong>选择一个研学项目</strong><span>或创建新项目，配置场景后向三类工作台派发任务。</span></div>
        </main>
      </section>

      <section v-else class="worker-task-layout">
        <div class="task-column">
          <div class="section-title"><div><small>AVAILABLE TASKS</small><h3>可领取任务</h3></div></div>
          <article v-for="task in availableTasks" :key="task.id" class="worker-task-card">
            <div class="manager-task-head"><div><span class="project-tag">{{ task.project.name }}</span><h4>{{ task.title }}</h4><small>{{ task.flow_display_name }} · {{ task.project.location || '未指定地点' }}</small></div><button v-if="task.my_submission" class="primary-button" type="button" @click="openSubmission(task.my_submission.session_id)">{{ task.my_submission.status === 'submitted' ? '查看已完成会话' : '继续执行' }}</button><button v-else class="primary-button" type="button" :disabled="saving" @click="claim(task)">领取并开始</button></div>
            <p v-if="task.description" class="task-description">{{ task.description }}</p>
            <details class="scene-details"><summary>查看场景与物料</summary><p v-if="task.project.scene_description">{{ task.project.scene_description }}</p><p v-if="task.project.materials.length"><strong>物料：</strong>{{ task.project.materials.join('、') }}</p><div v-for="file in task.project.files" :key="file.id" class="scene-file"><button type="button" @click="downloadFile(file, task.project.id)"><FileText :size="14" />{{ file.name }}</button></div></details>
          </article>
          <p v-if="!availableTasks.length" class="task-empty">当前没有可领取的{{ roleLabel }}任务。</p>
        </div>
        <div class="task-column">
          <div class="section-title"><div><small>MY EXECUTIONS</small><h3>我的任务</h3></div></div>
          <article v-for="item in myTasks" :key="item.id" class="my-task-row"><div><strong>{{ item.task_title }}</strong><span>{{ item.project_name }} · {{ item.status === 'submitted' ? '报告已提交' : '执行中' }}</span></div><button class="secondary-button" type="button" @click="openSubmission(item.session_id)">{{ item.status === 'submitted' ? '打开会话' : '继续执行' }}</button></article>
          <p v-if="!myTasks.length" class="task-empty">领取任务后会显示在这里。</p>
          <p class="auto-submit-note"><CheckCircle2 :size="16" />完成工作流最后阶段后，系统会自动形成{{ roleLabel }}报告并提交给研学基地。</p>
        </div>
      </section>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { CheckCircle2, FileText, Layers3, Plus, Upload, X } from "lucide-vue-next";
import {
  claimStudyTask,
  closeStudyProject,
  closeStudyTask,
  createStudyProject,
  createStudyTask,
  deleteStudyProjectFile,
  downloadStudyProjectFile,
  getAvailableStudyTasks,
  getFlows,
  getMyStudyTasks,
  getStudyProject,
  getStudyProjects,
  publishStudyProject,
  updateStudyProject,
  updateStudyTask,
  uploadStudyProjectFile,
} from "@/api";
import type { AvailableStudyTask, FlowInfo, MyStudyTask, StudyProject, StudyProjectFile, StudyTask, UserRole } from "@/types";

const props = defineProps<{ role: UserRole }>();
const emit = defineEmits<{ close: []; "open-session": [sessionId: string] }>();
const isManager = computed(() => props.role === "study_travel");
const roleLabel = computed(() => props.role === "parent" ? "家长" : props.role === "study_travel" ? "基地" : "教师");
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const projects = ref<StudyProject[]>([]);
const selectedProject = ref<StudyProject | null>(null);
const selectedProjectId = ref("");
const creatingProject = ref(false);
const availableTasks = ref<AvailableStudyTask[]>([]);
const myTasks = ref<MyStudyTask[]>([]);
const taskFlows = ref<FlowInfo[]>([]);
const summaryDraft = ref("");
const editingTaskId = ref("");
const editingTaskHasSubmissions = ref(false);
const projectDraft = reactive({ name: "", location: "", scene_description: "", materialsText: "" });
const taskDraft = reactive<{ title: string; description: string; target_role: UserRole; flow_name: string }>({ title: "", description: "", target_role: "teacher", flow_name: "" });

function syncProjectDraft(project: StudyProject) {
  projectDraft.name = project.name;
  projectDraft.location = project.location;
  projectDraft.scene_description = project.scene_description;
  projectDraft.materialsText = project.materials.join("\n");
  summaryDraft.value = project.summary_markdown;
}

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    if (isManager.value) {
      projects.value = await getStudyProjects();
      if (selectedProjectId.value && projects.value.some((item) => item.id === selectedProjectId.value)) await selectProject(selectedProjectId.value);
      else if (projects.value.length && !creatingProject.value) await selectProject(projects.value[0].id);
    } else {
      [availableTasks.value, myTasks.value] = await Promise.all([getAvailableStudyTasks(props.role), getMyStudyTasks(props.role)]);
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "加载失败，请稍后重试";
  } finally {
    loading.value = false;
  }
}

async function selectProject(id: string) {
  selectedProjectId.value = id;
  creatingProject.value = false;
  try {
    selectedProject.value = await getStudyProject(id);
    syncProjectDraft(selectedProject.value);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "读取项目失败";
  }
}

function startNewProject() {
  selectedProject.value = null;
  selectedProjectId.value = "";
  creatingProject.value = true;
  Object.assign(projectDraft, { name: "", location: "", scene_description: "", materialsText: "" });
  editingTaskId.value = "";
}

async function submitNewProject() {
  saving.value = true;
  error.value = "";
  try {
    const project = await createStudyProject({ ...projectDraft, materials: projectDraft.materialsText.split(/\r?\n/).map((item) => item.trim()).filter(Boolean) });
    creatingProject.value = false;
    await reload();
    await selectProject(project.id);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "创建项目失败";
  } finally {
    saving.value = false;
  }
}

async function saveProject() {
  if (!selectedProject.value) return;
  saving.value = true;
  error.value = "";
  try {
    await updateStudyProject(selectedProject.value.id, {
      name: projectDraft.name,
      location: projectDraft.location,
      scene_description: projectDraft.scene_description,
      materials: projectDraft.materialsText.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
    });
    await reload();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "保存场景失败";
  } finally {
    saving.value = false;
  }
}

async function saveSummary() {
  if (!selectedProject.value) return;
  saving.value = true;
  try {
    await updateStudyProject(selectedProject.value.id, { summary_markdown: summaryDraft.value });
    await reload();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "保存汇总失败";
  } finally {
    saving.value = false;
  }
}

async function publishProject() {
  if (!selectedProject.value) return;
  saving.value = true;
  try {
    await publishStudyProject(selectedProject.value.id);
    await reload();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "发布项目失败";
  } finally {
    saving.value = false;
  }
}

async function closeProject() {
  if (!selectedProject.value || !window.confirm("结束项目后将停止领取任务，已有执行和报告仍可查看。继续吗？")) return;
  saving.value = true;
  try {
    await closeStudyProject(selectedProject.value.id);
    await reload();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "结束项目失败";
  } finally {
    saving.value = false;
  }
}

async function loadTaskFlows() {
  taskFlows.value = await getFlows(taskDraft.target_role);
  if (!taskFlows.value.some((flow) => flow.name === taskDraft.flow_name)) taskDraft.flow_name = taskFlows.value[0]?.name || "";
}

async function saveTask() {
  if (!selectedProject.value) return;
  saving.value = true;
  error.value = "";
  try {
    const input = { ...taskDraft };
    if (editingTaskId.value) await updateStudyTask(selectedProject.value.id, editingTaskId.value, input);
    else await createStudyTask(selectedProject.value.id, input);
    cancelTaskEdit();
    await reload();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "保存任务失败";
  } finally {
    saving.value = false;
  }
}

function editTask(task: StudyTask) {
  editingTaskId.value = task.id;
  editingTaskHasSubmissions.value = Boolean(task.submission_count);
  Object.assign(taskDraft, { title: task.title, description: task.description, target_role: task.target_role, flow_name: task.flow_name });
  void loadTaskFlows();
}

function cancelTaskEdit() {
  editingTaskId.value = "";
  editingTaskHasSubmissions.value = false;
  Object.assign(taskDraft, { title: "", description: "", target_role: "teacher" as UserRole, flow_name: "" });
  void loadTaskFlows();
}

async function closeTask(task: StudyTask) {
  if (!selectedProject.value) return;
  saving.value = true;
  try {
    await closeStudyTask(selectedProject.value.id, task.id);
    await reload();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "关闭任务失败";
  } finally {
    saving.value = false;
  }
}

async function uploadFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file || !selectedProject.value) return;
  saving.value = true;
  try {
    await uploadStudyProjectFile(selectedProject.value.id, file);
    await reload();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "上传附件失败";
  } finally {
    saving.value = false;
    input.value = "";
  }
}

async function removeFile(fileId: string) {
  if (!selectedProject.value) return;
  saving.value = true;
  try {
    await deleteStudyProjectFile(selectedProject.value.id, fileId);
    await reload();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "删除附件失败";
  } finally {
    saving.value = false;
  }
}

async function downloadFile(file: StudyProjectFile, projectId = selectedProject.value?.id) {
  if (!projectId) return;
  try {
    await downloadStudyProjectFile(projectId, file.id, props.role);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "下载附件失败";
  }
}

async function claim(task: AvailableStudyTask) {
  saving.value = true;
  try {
    const result = await claimStudyTask(task.id, props.role);
    emit("open-session", result.session.id);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "领取任务失败";
  } finally {
    saving.value = false;
  }
}

function openSubmission(sessionId: string) {
  emit("open-session", sessionId);
}

function projectStatus(status: string) {
  return ({ draft: "草稿", active: "进行中", closed: "已结束" } as Record<string, string>)[status] || status;
}
function taskStatus(status: string) {
  return ({ draft: "草稿", open: "开放领取", closed: "已关闭" } as Record<string, string>)[status] || status;
}
function roleName(role: UserRole) {
  return ({ teacher: "教师工作台", parent: "家长工作台", study_travel: "基地工作台" } as Record<UserRole, string>)[role];
}
function formatDate(value: string) {
  return value ? new Date(value).toLocaleString() : "";
}

watch(() => props.role, () => { void reload(); });
onMounted(() => { void reload(); void loadTaskFlows(); });
</script>

<style scoped>
.task-center-backdrop{position:fixed;z-index:1300;inset:0;display:grid;place-items:center;padding:18px;background:rgba(17,27,22,.56);backdrop-filter:blur(5px)}
.task-center{display:grid;grid-template-rows:auto auto minmax(0,1fr);width:min(1160px,calc(100vw - 36px));height:min(900px,calc(100vh - 36px));overflow:hidden;border:1px solid var(--border-default);border-radius:16px;background:var(--surface);box-shadow:var(--shadow-raised)}
.task-center-head{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:18px 22px;border-bottom:1px solid var(--border-default)}
.task-center-head p,.section-title small,.project-title-row small{margin:0 0 4px;color:var(--brand);font-size:9px;font-weight:800;letter-spacing:.1em}
.task-center-head h2{margin:0;color:var(--text-primary);font-size:20px}.task-center-head span{display:block;margin-top:5px;color:var(--text-secondary);font-size:11px}
.head-actions,.project-actions,.task-actions{display:flex;align-items:center;gap:7px}.close-button{display:grid;place-items:center;width:34px;height:34px;border:1px solid var(--border-default);border-radius:8px;color:var(--text-secondary);background:var(--surface)}
.task-error{margin:10px 20px 0;padding:9px 12px;border-radius:8px;color:var(--danger);background:var(--danger-soft);font-size:11px}
.manager-layout{display:grid;grid-template-columns:245px minmax(0,1fr);min-height:0}.project-list-pane{display:flex;flex-direction:column;gap:7px;padding:14px;border-right:1px solid var(--border-default);overflow:auto;background:var(--surface-subtle)}
.create-project-card,.project-list-item{display:grid;gap:5px;width:100%;padding:11px;border:1px solid var(--border-default);border-radius:9px;color:var(--text-primary);background:var(--surface);text-align:left}.create-project-card{display:flex;align-items:center;gap:7px;color:var(--brand);border-style:dashed;font-weight:700}.project-list-item.selected{border-color:var(--brand);box-shadow:inset 3px 0 var(--brand)}.project-list-item strong{font-size:11px}.project-list-item span,.project-list-item small{color:var(--text-secondary);font-size:9px}.project-list-item small{color:var(--brand)}
.project-editor{min-width:0;overflow:auto;padding:20px 24px 28px}.project-title-row{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:15px}.project-title-row h3{margin:0;color:var(--text-primary);font-size:19px}.section-title{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:9px}.section-title h3,.section-title h4{margin:0;color:var(--text-primary);font-size:14px}.section-title small{display:block}
.project-form{display:grid;gap:9px}.project-form label{display:grid;gap:4px;color:var(--text-secondary);font-size:10px}.project-form input,.project-form textarea,.project-form select,.summary-section textarea{width:100%;min-width:0;padding:8px 9px;border:1px solid var(--border-default);border-radius:7px;color:var(--text-primary);background:var(--surface);font:inherit;font-size:11px}.project-form textarea,.summary-section textarea{resize:vertical;line-height:1.55}.project-form input:disabled,.project-form textarea:disabled{opacity:.72}.project-form footer,.project-form .form-footer{display:flex;justify-content:flex-end;gap:7px}.compact-form{padding:12px;border:1px solid var(--border-default);border-radius:10px;background:var(--surface-subtle)}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.primary-button,.secondary-button{display:inline-flex;align-items:center;justify-content:center;min-height:31px;padding:6px 10px;border:1px solid var(--brand);border-radius:7px;color:var(--brand-contrast);background:var(--brand);font-size:10px;font-weight:700}.secondary-button{border-color:var(--border-default);color:var(--text-secondary);background:var(--surface)}button:disabled{opacity:.55;cursor:not-allowed}
.attachment-section,.task-builder,.task-list-section,.summary-section{margin-top:20px}.upload-button{display:inline-flex;align-items:center;gap:5px;padding:6px 9px;border:1px solid var(--border-default);border-radius:7px;color:var(--text-secondary);background:var(--surface);font-size:10px;cursor:pointer}.upload-button input{display:none}.attachment-list{display:grid;gap:5px}.attachment-list>div{display:flex;align-items:center;justify-content:space-between;padding:7px 9px;border:1px solid var(--border-default);border-radius:7px}.attachment-list button{display:flex;align-items:center;gap:7px;border:0;color:var(--brand);background:transparent;text-align:left}.attachment-list button span{display:grid;gap:2px;color:var(--text-primary);font-size:10px}.attachment-list small{color:var(--text-muted);font-size:9px}.attachment-list .remove-file{color:var(--danger)}.muted-empty,.inline-note{margin:5px 0;color:var(--text-muted);font-size:10px;line-height:1.5}.inline-note{color:#9a651f}
.manager-task-card{margin:7px 0;padding:10px;border:1px solid var(--border-default);border-radius:9px;background:var(--surface)}.manager-task-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.manager-task-head>div:first-child{display:grid;justify-items:start;gap:4px;min-width:0}.manager-task-head strong{color:var(--text-primary);font-size:11px}.manager-task-head small,.task-description{margin:0;color:var(--text-secondary);font-size:10px}.role-chip,.project-tag{padding:3px 6px;border-radius:999px;color:var(--brand);background:var(--brand-soft);font-size:9px;font-weight:700}.role-chip.parent{color:#87572a;background:#f8eddf}.role-chip.study_travel{color:#527040;background:#edf3e8}.text-button{border:0;color:var(--brand);background:transparent;font-size:10px}.danger-text{color:var(--danger)}.task-description{margin-top:8px;line-height:1.55}.submission-list,.scene-details{margin-top:9px;padding-top:8px;border-top:1px solid var(--border-default);color:var(--text-secondary);font-size:10px}.submission-list summary,.scene-details summary{cursor:pointer}.submission-item{margin-top:8px;padding:9px;border-radius:7px;background:var(--surface-subtle)}.submission-item>div{display:flex;justify-content:space-between;gap:8px}.submission-item strong{color:var(--text-primary)}.submission-item span{color:var(--text-muted)}.submission-item pre{max-height:260px;overflow:auto;white-space:pre-wrap;color:var(--text-secondary);font:10px/1.6 inherit}.summary-section .section-title{margin-bottom:8px}.project-placeholder,.task-empty{display:grid;justify-items:center;align-content:center;gap:8px;min-height:180px;color:var(--text-muted);font-size:11px;text-align:center}.project-placeholder strong{color:var(--text-primary)}.project-placeholder span{max-width:340px;line-height:1.5}.task-empty.compact{min-height:70px}
.worker-task-layout{display:grid;grid-template-columns:1fr 1fr;gap:18px;min-height:0;padding:19px 22px;overflow:auto}.task-column{min-width:0}.worker-task-card{margin:9px 0;padding:12px;border:1px solid var(--border-default);border-radius:10px;background:var(--surface)}.worker-task-card h4{margin:1px 0;color:var(--text-primary);font-size:13px}.worker-task-card .manager-task-head>div:first-child{gap:5px}.scene-details p{line-height:1.55}.scene-file button{display:flex;align-items:center;gap:5px;margin:5px 0;padding:4px 0;border:0;color:var(--brand);background:transparent;font-size:10px}.my-task-row{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:7px 0;padding:10px;border:1px solid var(--border-default);border-radius:9px}.my-task-row>div{display:grid;gap:4px}.my-task-row strong{color:var(--text-primary);font-size:10px}.my-task-row span{color:var(--text-secondary);font-size:9px}.auto-submit-note{display:flex;align-items:flex-start;gap:7px;margin-top:17px;padding:10px;border-radius:8px;color:var(--brand);background:var(--brand-soft);font-size:10px;line-height:1.5}
@media(max-width:760px){.task-center-backdrop{padding:6px}.task-center{width:calc(100vw - 12px);height:calc(100vh - 12px)}.task-center-head{padding:13px}.manager-layout{grid-template-columns:150px minmax(0,1fr)}.project-list-pane{padding:8px}.project-editor{padding:14px}.worker-task-layout{grid-template-columns:1fr;padding:14px}.form-grid{grid-template-columns:1fr}.task-center-head span{max-width:55vw}}
</style>
