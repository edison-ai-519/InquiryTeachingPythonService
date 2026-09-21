export type GraphLayoutProfile = "compact" | "normal" | "fullscreen";

export type GraphLayoutEntity = {
  id: string;
  name: string;
};

export type GraphLayoutRelation = {
  subject_entity_id: string;
  object_entity_id: string;
};

export type GraphLayoutPosition = {
  xRatio: number;
  yRatio: number;
  ring: number;
};

const profileConfig: Record<GraphLayoutProfile, { capacities: number[]; radii: number[]; verticalRatio: number; expansionRadius: number }> = {
  compact: { capacities: [7, 12, 20], radii: [0.22, 0.35, 0.45], verticalRatio: 0.72, expansionRadius: 0.11 },
  normal: { capacities: [9, 16, 28], radii: [0.24, 0.37, 0.46], verticalRatio: 0.7, expansionRadius: 0.1 },
  fullscreen: { capacities: [11, 20, 34], radii: [0.25, 0.39, 0.47], verticalRatio: 0.68, expansionRadius: 0.085 },
};

export function buildInitialGraphPositions(
  entities: GraphLayoutEntity[],
  profile: GraphLayoutProfile,
  relations: GraphLayoutRelation[] = [],
  focusNodeId = "",
): Map<string, GraphLayoutPosition> {
  const ordered = [...entities].sort((a, b) => a.name.localeCompare(b.name, "zh-Hans-CN") || a.id.localeCompare(b.id, "zh-Hans-CN"));
  if (!ordered.length) return new Map();
  const focus = ordered.find((entity) => entity.id === focusNodeId) || ordered[0];
  const entityById = new Map(ordered.map((entity) => [entity.id, entity]));
  const positions = new Map<string, GraphLayoutPosition>();
  positions.set(focus.id, { xRatio: 0.5, yRatio: 0.5, ring: 0 });
  if (ordered.length === 1) return positions;

  const config = profileConfig[profile];
  const adjacency = buildAdjacency(ordered, relations);
  const degree = new Map(ordered.map((entity) => [entity.id, adjacency.get(entity.id)?.size || 0]));
  const levels = new Map<string, number>([[focus.id, 0]]);
  const queue = [focus.id];
  const sortIds = (ids: string[]) => ids.sort((left, right) => {
    const leftEntity = entityById.get(left)!;
    const rightEntity = entityById.get(right)!;
    return (degree.get(right) || 0) - (degree.get(left) || 0)
      || leftEntity.name.localeCompare(rightEntity.name, "zh-Hans-CN")
      || left.localeCompare(right);
  });
  while (queue.length) {
    const current = queue.shift()!;
    const level = levels.get(current)!;
    for (const neighbor of sortIds([...(adjacency.get(current) || [])])) {
      if (levels.has(neighbor)) continue;
      levels.set(neighbor, level + 1);
      queue.push(neighbor);
    }
  }

  const maxConnectedLevel = Math.max(...levels.values());
  const detached = ordered.filter((entity) => !levels.has(entity.id));
  detached.forEach((entity) => levels.set(entity.id, Math.max(1, maxConnectedLevel + 1)));
  const entitiesByLevel = new Map<number, GraphLayoutEntity[]>();
  for (const entity of ordered) {
    if (entity.id === focus.id) continue;
    const level = levels.get(entity.id) || 1;
    const group = entitiesByLevel.get(level) || [];
    group.push(entity);
    entitiesByLevel.set(level, group);
  }

  let physicalRing = 1;
  for (const level of [...entitiesByLevel.keys()].sort((a, b) => a - b)) {
    const group = entitiesByLevel.get(level)!;
    group.sort((left, right) => (degree.get(right.id) || 0) - (degree.get(left.id) || 0)
      || left.name.localeCompare(right.name, "zh-Hans-CN")
      || left.id.localeCompare(right.id));
    let offset = 0;
    while (offset < group.length) {
      const capacity = ringCapacity(config, physicalRing);
      const ringEntities = group.slice(offset, offset + capacity);
      const radius = ringRadius(config, physicalRing);
      ringEntities.forEach((entity, index) => {
      const angle = (Math.PI * 2 * index) / ringEntities.length - Math.PI / 2;
      positions.set(entity.id, {
        xRatio: 0.5 + Math.cos(angle) * radius,
        yRatio: 0.5 + Math.sin(angle) * radius * config.verticalRatio,
          ring: physicalRing,
      });
      });
      offset += ringEntities.length;
      physicalRing += 1;
    }
  }
  return positions;
}

export function placeExpandedGraphPositions(
  existing: Map<string, GraphLayoutPosition>,
  sourceId: string,
  addedEntities: GraphLayoutEntity[],
  profile: GraphLayoutProfile,
): Map<string, GraphLayoutPosition> {
  const next = new Map(existing);
  const source = existing.get(sourceId);
  if (!source) return next;

  const additions = addedEntities
    .filter((entity) => !next.has(entity.id))
    .sort((a, b) => a.name.localeCompare(b.name, "zh-Hans-CN") || a.id.localeCompare(b.id, "zh-Hans-CN"));
  const config = profileConfig[profile];
  const seed = hashId(sourceId) / 0xffffffff;
  const startAngle = seed * Math.PI * 2 - Math.PI / 2;
  const spread = Math.min(Math.PI * 0.95, Math.max(Math.PI * 0.35, additions.length * 0.3));

  additions.forEach((entity, index) => {
    const angle = additions.length === 1
      ? startAngle
      : startAngle - spread / 2 + (spread * index) / (additions.length - 1);
    const radius = config.expansionRadius + Math.floor(index / 6) * 0.055;
    next.set(entity.id, {
      xRatio: clamp(source.xRatio + Math.cos(angle) * radius, 0.06, 0.94),
      yRatio: clamp(source.yRatio + Math.sin(angle) * radius * config.verticalRatio, 0.08, 0.92),
      ring: source.ring + 1,
    });
  });
  return next;
}

export function toViewportPoint(
  position: GraphLayoutPosition,
  width: number,
  height: number,
): { x: number; y: number } {
  return { x: position.xRatio * width, y: position.yRatio * height };
}

export function graphLayoutProfile(
  width: number,
  height: number,
  variant: "full" | "map",
  fullscreen: boolean,
): GraphLayoutProfile {
  if (fullscreen || (width >= 960 && height >= 620)) return "fullscreen";
  if (variant === "map" || width < 520 || height < 420) return "compact";
  return "normal";
}

function hashId(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function buildAdjacency(entities: GraphLayoutEntity[], relations: GraphLayoutRelation[]): Map<string, Set<string>> {
  const entityIds = new Set(entities.map((entity) => entity.id));
  const adjacency = new Map<string, Set<string>>(entities.map((entity) => [entity.id, new Set()]));
  for (const relation of relations) {
    const { subject_entity_id: subjectId, object_entity_id: objectId } = relation;
    if (!entityIds.has(subjectId) || !entityIds.has(objectId) || subjectId === objectId) continue;
    adjacency.get(subjectId)!.add(objectId);
    adjacency.get(objectId)!.add(subjectId);
  }
  return adjacency;
}

function ringCapacity(config: (typeof profileConfig)[GraphLayoutProfile], ring: number): number {
  const index = ring - 1;
  return config.capacities[Math.min(index, config.capacities.length - 1)] + Math.max(0, index - config.capacities.length + 1) * 12;
}

function ringRadius(config: (typeof profileConfig)[GraphLayoutProfile], ring: number): number {
  const index = ring - 1;
  return config.radii[Math.min(index, config.radii.length - 1)] + Math.max(0, index - config.radii.length + 1) * 0.065;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
