<template>
  <nav class="stage-timeline" aria-label="教学阶段">
    <button
      v-for="(stage, index) in stages"
      :key="stage.id"
      class="timeline-stage"
      :class="{ active: stage.id === selectedStageId, current: stage.id === currentStageId, confirmed: output(stage.id)?.confirmed }"
      type="button"
      :title="`阶段 ${index + 1} · ${stage.name}`"
      @click="$emit('select-stage', stage.id)"
    >
      <span class="timeline-dot" aria-hidden="true">
        <Check v-if="output(stage.id)?.confirmed" :size="13" />
        <span v-else-if="stage.id === currentStageId">{{ index + 1 }}</span>
        <Circle v-else :size="12" />
      </span>
      <span class="timeline-copy">
        <strong>{{ index + 1 }} {{ stage.name }}</strong>
        <small>{{ stage.display_direction || stage.direction }}</small>
      </span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { Check, Circle } from "lucide-vue-next";
import type { FlowStage, StageOutput } from "@/types";

defineProps<{
  stages: FlowStage[];
  selectedStageId: string;
  currentStageId: string;
  output: (stageId: string) => StageOutput | undefined;
}>();

defineEmits<{ 'select-stage': [stageId: string] }>();
</script>
