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

const profileConfig: Record<GraphLayoutProfile, {
  capacities: number[];
  radii: number[];
  verticalRatio: number;
  rootDistance: number;
  childDistance: number;
  expansionRadius: number;
  minimumSpacing: number;
}> = {
  compact: { capacities: [7, 12, 20], radii: [0.24, 0.36, 0.46], verticalRatio: 0.76, rootDistance: 0.22, childDistance: 0.14, expansionRadius: 0.11, minimumSpacing: 0.12 },
  normal: { capacities: [9, 16, 28], radii: [0.27, 0.4, 0.48], verticalRatio: 0.74, rootDistance: 0.26, childDistance: 0.17, expansionRadius: 0.12, minimumSpacing: 0.135 },
  fullscreen: { capacities: [11, 20, 34], radii: [0.29, 0.42, 0.49], verticalRatio: 0.72, rootDistance: 0.28, childDistance: 0.18, expansionRadius: 0.13, minimumSpacing: 0.145 },
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
  const parentById = new Map<string, string>();
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
      parentById.set(neighbor, current);
      queue.push(neighbor);
    }
  }

  const childrenByParent = new Map<string, string[]>();
  for (const [childId, parentId] of parentById) {
    const children = childrenByParent.get(parentId) || [];
    children.push(childId);
    childrenByParent.set(parentId, children);
  }
  childrenByParent.forEach((children) => sortIds(children));

  // 第一层均匀环绕焦点；后续层只在父节点朝外的扇区内选点。
  const rootChildren = childrenByParent.get(focus.id) || [];
  placeRootChildren(positions, rootChildren, config, 1);

  const parentsByLevel = [...levels.entries()]
    .filter(([id, level]) => id !== focus.id && level > 0)
    .sort((left, right) => left[1] - right[1] || left[0].localeCompare(right[0]));
  for (const [parentId, level] of parentsByLevel) {
    const childIds = childrenByParent.get(parentId) || [];
    if (!childIds.length || !positions.has(parentId)) continue;
    const parentOfParent = parentById.get(parentId);
    const grandparentPosition = parentOfParent ? positions.get(parentOfParent) : undefined;
    placeLocalChildren(
      positions,
      childIds.map((id) => entityById.get(id)!),
      parentId,
      grandparentPosition,
      level + 1,
      adjacency,
      config,
    );
  }

  placeDetachedEntities(
    positions,
    ordered.filter((entity) => !levels.has(entity.id)),
    config,
    Math.max(1, ...levels.values()) + 1,
  );
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
  const outwardAngle = Math.atan2(source.yRatio - 0.5, source.xRatio - 0.5) || (hashId(sourceId) / 0xffffffff) * Math.PI * 2;
  placeLocalChildren(next, additions, sourceId, { xRatio: 0.5, yRatio: 0.5, ring: Math.max(0, source.ring - 1) }, source.ring + 1, new Map(), config, outwardAngle, config.expansionRadius);
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

function placeRootChildren(
  positions: Map<string, GraphLayoutPosition>,
  childIds: string[],
  config: (typeof profileConfig)[GraphLayoutProfile],
  ring: number,
) {
  childIds.forEach((childId, index) => {
    const angle = childIds.length === 1 ? 0 : (Math.PI * 2 * index) / childIds.length;
    positions.set(childId, pointAt({ xRatio: 0.5, yRatio: 0.5, ring: 0 }, angle, config.rootDistance, config, ring));
  });
}

function placeLocalChildren(
  positions: Map<string, GraphLayoutPosition>,
  children: GraphLayoutEntity[],
  parentId: string,
  grandparentPosition: GraphLayoutPosition | undefined,
  ring: number,
  adjacency: Map<string, Set<string>>,
  config: (typeof profileConfig)[GraphLayoutProfile],
  initialAngle?: number,
  distance = config.childDistance,
) {
  const parent = positions.get(parentId);
  if (!parent || !children.length) return;

  const outwardAngle = initialAngle ?? Math.atan2(
    parent.yRatio - (grandparentPosition?.yRatio ?? 0.5),
    parent.xRatio - (grandparentPosition?.xRatio ?? 0.5),
  );
  const spread = Math.min(Math.PI * 0.78, Math.PI * 0.22 + Math.max(0, children.length - 1) * 0.34);
  children.forEach((child, index) => {
    const preferredAngle = children.length === 1
      ? outwardAngle
      : outwardAngle - spread / 2 + (spread * index) / (children.length - 1);
    positions.set(child.id, chooseLocalPosition(positions, parent, parentId, child.id, preferredAngle, distance, ring, adjacency, config));
  });
}

function chooseLocalPosition(
  positions: Map<string, GraphLayoutPosition>,
  parent: GraphLayoutPosition,
  parentId: string,
  childId: string,
  preferredAngle: number,
  distance: number,
  ring: number,
  adjacency: Map<string, Set<string>>,
  config: (typeof profileConfig)[GraphLayoutProfile],
): GraphLayoutPosition {
  const angleOffsets = [0, -0.13, 0.13, -0.26, 0.26, -0.39, 0.39];
  const distances = [distance, distance * 0.9, distance * 1.1];
  let best = pointAt(parent, preferredAngle, distance, config, ring);
  let bestScore = Number.POSITIVE_INFINITY;

  for (const angleOffset of angleOffsets) {
    for (const candidateDistance of distances) {
      const candidate = pointAt(parent, preferredAngle + angleOffset, candidateDistance, config, ring);
      let score = Math.abs(angleOffset) * 0.035 + Math.abs(candidateDistance - distance) * 0.08;
      for (const [id, positioned] of positions) {
        const nodeDistance = Math.hypot(candidate.xRatio - positioned.xRatio, candidate.yRatio - positioned.yRatio);
        score += Math.max(0, config.minimumSpacing - nodeDistance) ** 2 * 140;
        if (id !== parentId && adjacency.get(childId)?.has(id)) score += nodeDistance * 0.12;
      }
      score += countNewEdgeCrossings(parentId, parent, childId, candidate, positions, adjacency) * 0.45;
      if (score < bestScore) {
        best = candidate;
        bestScore = score;
      }
    }
  }
  return best;
}

function countNewEdgeCrossings(
  sourceId: string,
  source: GraphLayoutPosition,
  targetId: string,
  target: GraphLayoutPosition,
  positions: Map<string, GraphLayoutPosition>,
  adjacency: Map<string, Set<string>>,
): number {
  let crossings = 0;
  const checked = new Set<string>();
  for (const [leftId, neighbors] of adjacency) {
    const left = positions.get(leftId);
    if (!left) continue;
    for (const rightId of neighbors) {
      const edgeId = [leftId, rightId].sort().join("|");
      if (checked.has(edgeId)) continue;
      checked.add(edgeId);
      if (leftId === sourceId || leftId === targetId || rightId === sourceId || rightId === targetId) continue;
      const right = positions.get(rightId);
      if (right && segmentsIntersect(source, target, left, right)) crossings += 1;
    }
  }
  return crossings;
}

function segmentsIntersect(
  firstStart: GraphLayoutPosition,
  firstEnd: GraphLayoutPosition,
  secondStart: GraphLayoutPosition,
  secondEnd: GraphLayoutPosition,
): boolean {
  const direction = (origin: GraphLayoutPosition, point: GraphLayoutPosition, target: GraphLayoutPosition) => (
    (point.xRatio - origin.xRatio) * (target.yRatio - origin.yRatio)
    - (point.yRatio - origin.yRatio) * (target.xRatio - origin.xRatio)
  );
  const first = direction(firstStart, firstEnd, secondStart);
  const second = direction(firstStart, firstEnd, secondEnd);
  const third = direction(secondStart, secondEnd, firstStart);
  const fourth = direction(secondStart, secondEnd, firstEnd);
  return first * second < 0 && third * fourth < 0;
}

function placeDetachedEntities(
  positions: Map<string, GraphLayoutPosition>,
  detached: GraphLayoutEntity[],
  config: (typeof profileConfig)[GraphLayoutProfile],
  firstRing: number,
) {
  let ring = firstRing;
  let offset = 0;
  while (offset < detached.length) {
    const capacity = ringCapacity(config, ring);
    const entities = detached.slice(offset, offset + capacity);
    const radius = ringRadius(config, ring);
    entities.forEach((entity, index) => {
      const angle = entities.length === 1 ? 0 : (Math.PI * 2 * index) / entities.length;
      positions.set(entity.id, pointAt({ xRatio: 0.5, yRatio: 0.5, ring: 0 }, angle, radius, config, ring));
    });
    offset += entities.length;
    ring += 1;
  }
}

function pointAt(
  center: GraphLayoutPosition,
  angle: number,
  distance: number,
  config: (typeof profileConfig)[GraphLayoutProfile],
  ring: number,
): GraphLayoutPosition {
  return {
    xRatio: clamp(center.xRatio + Math.cos(angle) * distance, 0.06, 0.94),
    yRatio: clamp(center.yRatio + Math.sin(angle) * distance * config.verticalRatio, 0.08, 0.92),
    ring,
  };
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
