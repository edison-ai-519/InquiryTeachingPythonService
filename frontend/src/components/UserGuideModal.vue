<template>
  <div class="user-guide-backdrop" @click.self="$emit('close')">
    <section class="user-guide-modal" role="dialog" aria-modal="true" aria-labelledby="user-guide-title">
      <header class="user-guide-header">
        <div>
          <p>使用指引</p>
          <h2 id="user-guide-title">快速了解工作台</h2>
          <span>按步骤开始使用，也可以查看其他角色的指引。</span>
        </div>
        <button class="user-guide-close" type="button" aria-label="关闭使用手册" @click="$emit('close')"><X :size="18" /></button>
      </header>

      <nav class="user-guide-tabs" aria-label="使用手册章节">
        <button type="button" :class="{ active: activeTab === 'start' }" @click="activeTab = 'start'">快速开始</button>
        <button v-for="item in roleGuideTabs" :key="item.role" type="button" :class="{ active: activeTab === item.role }" @click="activeTab = item.role">{{ item.label }}工作台</button>
        <button type="button" :class="{ active: activeTab === 'help' }" @click="activeTab = 'help'">常见操作</button>
      </nav>

      <div class="user-guide-body">
        <template v-if="activeTab === 'start'">
          <p class="user-guide-intro">从创建草案到导出成果，通常按以下顺序完成：</p>
          <ol class="user-guide-step-list">
            <li v-for="(step, index) in commonGuideSteps" :key="step.title">
              <span class="user-guide-step-number">{{ index + 1 }}</span>
              <div><strong>{{ step.title }}</strong><p>{{ step.description }}</p></div>
            </li>
          </ol>
          <aside class="user-guide-note"><BookOpen :size="17" /><span><strong>页面怎么读</strong>宽屏左侧是草案和阶段，中间是对话，右侧是方案编辑、保存与导出；窄屏可在顶部切换“对话”和“方案编辑”。</span></aside>
        </template>
        <template v-else-if="activeTab === 'help'">
          <p class="user-guide-intro">遇到具体操作问题时，可以先查看这里：</p>
          <ol class="user-guide-step-list">
            <li v-for="(item, index) in commonHelpItems" :key="item.title">
              <span class="user-guide-step-number">{{ index + 1 }}</span>
              <div><strong>{{ item.title }}</strong><p>{{ item.description }}</p></div>
            </li>
          </ol>
        </template>
        <template v-else>
          <template v-for="role in roleGuideTabs" :key="role.role">
            <article v-if="activeTab === role.role" class="user-guide-role-content">
              <p class="user-guide-intro">{{ userGuideByRole[role.role].intro }}</p>
              <ol class="user-guide-step-list">
                <li v-for="(step, index) in userGuideByRole[role.role].steps" :key="step.title">
                  <span class="user-guide-step-number">{{ index + 1 }}</span>
                  <div><strong>{{ step.title }}</strong><p>{{ step.description }}</p></div>
                </li>
              </ol>
              <aside class="user-guide-example"><strong>提问示例</strong><p>“{{ userGuideByRole[role.role].example }}”</p></aside>
            </article>
          </template>
        </template>
      </div>
      <footer class="user-guide-footer"><span>可以随时关闭手册，返回当前工作内容。</span><button type="button" @click="$emit('close')">开始使用</button></footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { BookOpen, X } from "lucide-vue-next";
import type { UserRole } from "@/types";
import { commonGuideSteps, commonHelpItems, roleGuideTabs, userGuideByRole } from "@/userGuide";

const props = defineProps<{ role: UserRole }>();
const activeTab = ref<UserRole | "start" | "help">(props.role);
const emit = defineEmits<{ close: [] }>();

function handleEscape(event: KeyboardEvent) {
  if (event.key === "Escape") emit("close");
}

onMounted(() => window.addEventListener("keydown", handleEscape));
onBeforeUnmount(() => window.removeEventListener("keydown", handleEscape));
</script>

<style scoped>
.user-guide-backdrop{position:fixed;inset:0;z-index:1400;display:grid;place-items:center;padding:20px;background:var(--overlay-backdrop)}
.user-guide-modal{display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;width:min(760px,100%);max-height:min(760px,calc(100vh - 40px));overflow:hidden;border:1px solid var(--border-default);border-radius:16px;background:var(--surface);box-shadow:var(--shadow-raised)}
.user-guide-header{display:flex;justify-content:space-between;gap:18px;padding:24px 26px 18px;border-bottom:1px solid var(--border-default)}
.user-guide-header p{margin:0 0 5px;color:var(--brand);font-size:11px;font-weight:700;letter-spacing:.08em}
.user-guide-header h2{margin:0;color:var(--text-primary);font-size:21px}
.user-guide-header span,.user-guide-footer span{color:var(--text-secondary);font-size:12px}
.user-guide-close{display:grid;place-items:center;flex:none;width:36px;height:36px;border:1px solid var(--border-default);border-radius:9px;color:var(--text-secondary);background:var(--surface);cursor:pointer}
.user-guide-tabs{display:flex;gap:7px;padding:12px 26px;border-bottom:1px solid var(--border-default);overflow:auto}
.user-guide-tabs button{flex:none;padding:8px 12px;border:1px solid transparent;border-radius:8px;color:var(--text-secondary);background:var(--surface-subtle);font-size:12px;cursor:pointer}
.user-guide-tabs button.active{border-color:var(--brand);color:var(--brand);background:var(--brand-soft);font-weight:700}
.user-guide-body{min-height:0;padding:20px 26px;overflow:auto}
.user-guide-intro{margin:0 0 17px;color:var(--text-secondary);font-size:13px;line-height:1.7}
.user-guide-step-list{display:grid;gap:12px;margin:0;padding:0;list-style:none}
.user-guide-step-list li{display:grid;grid-template-columns:30px minmax(0,1fr);gap:11px;align-items:start}
.user-guide-step-number{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;color:var(--brand);background:var(--brand-soft);font-size:12px;font-weight:700}
.user-guide-step-list strong,.user-guide-note strong,.user-guide-example strong{color:var(--text-primary);font-size:13px}
.user-guide-step-list p,.user-guide-example p{margin:4px 0 0;color:var(--text-secondary);font-size:12px;line-height:1.65}
.user-guide-note{display:flex;gap:9px;margin-top:19px;padding:12px;border:1px solid var(--border-default);border-radius:10px;color:var(--brand);background:var(--surface-subtle)}
.user-guide-note span{display:grid;gap:3px;color:var(--text-secondary);font-size:12px;line-height:1.5}
.user-guide-example{margin-top:19px;padding:14px 16px;border-left:3px solid var(--brand);border-radius:0 9px 9px 0;background:var(--brand-soft)}
.user-guide-example p{color:var(--text-primary)}
.user-guide-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 26px;border-top:1px solid var(--border-default)}
.user-guide-footer button{padding:9px 15px;border:0;border-radius:8px;color:#fff;background:var(--brand);font-size:12px;font-weight:700;cursor:pointer}
@media(max-width:600px){.user-guide-backdrop{padding:10px}.user-guide-modal{max-height:calc(100vh - 20px)}.user-guide-header{padding:18px 16px 14px}.user-guide-tabs{padding:10px 16px}.user-guide-body{padding:17px 16px}.user-guide-footer{align-items:flex-start;padding:12px 16px}.user-guide-footer span{max-width:210px}}
</style>
