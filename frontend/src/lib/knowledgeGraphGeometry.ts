export type GraphPoint = {
  x: number;
  y: number;
  radius: number;
};

export type CurvedEdge = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  controlX: number;
  controlY: number;
  labelX: number;
  labelY: number;
  normalX: number;
  normalY: number;
  path: string;
};

export type RelationLabelCandidate = {
  id: string;
  label: string;
  x: number;
  y: number;
  normalX: number;
  normalY: number;
};

export type RelationLabelPlacement = RelationLabelCandidate & {
  width: number;
  height: number;
};

export function buildCurvedEdge(input: {
  id: string;
  source: GraphPoint;
  target: GraphPoint;
  lane: number;
}): CurvedEdge {
  const dx = input.target.x - input.source.x;
  const dy = input.target.y - input.source.y;
  const distance = Math.hypot(dx, dy);
  if (!distance) {
    return {
      x1: input.source.x,
      y1: input.source.y,
      x2: input.target.x,
      y2: input.target.y,
      controlX: input.source.x,
      controlY: input.source.y,
      labelX: input.source.x,
      labelY: input.source.y,
      normalX: 0,
      normalY: -1,
      path: `M ${input.source.x} ${input.source.y}`,
    };
  }
  const unitX = dx / distance;
  const unitY = dy / distance;
  const normalX = -unitY;
  const normalY = unitX;
  const x1 = input.source.x + unitX * Math.min(input.source.radius + 2, distance / 3);
  const y1 = input.source.y + unitY * Math.min(input.source.radius + 2, distance / 3);
  const x2 = input.target.x - unitX * Math.min(input.target.radius + 4, distance / 3);
  const y2 = input.target.y - unitY * Math.min(input.target.radius + 4, distance / 3);
  const curveDirection = hashId(input.id) % 2 === 0 ? 1 : -1;
  const curvature = curveDirection * (Math.min(24, Math.max(8, distance * 0.09)) + input.lane * 8);
  const controlX = (x1 + x2) / 2 + normalX * curvature;
  const controlY = (y1 + y2) / 2 + normalY * curvature;
  const midpoint = quadraticPoint(x1, y1, controlX, controlY, x2, y2, 0.5);
  const labelOffset = curvature >= 0 ? 11 : -11;
  return {
    x1,
    y1,
    x2,
    y2,
    controlX,
    controlY,
    labelX: midpoint.x + normalX * labelOffset,
    labelY: midpoint.y + normalY * labelOffset,
    normalX,
    normalY,
    path: `M ${round(x1)} ${round(y1)} Q ${round(controlX)} ${round(controlY)} ${round(x2)} ${round(y2)}`,
  };
}

export function placeRelationLabels(candidates: RelationLabelCandidate[]): RelationLabelPlacement[] {
  const placed: RelationLabelPlacement[] = [];
  for (const candidate of candidates) {
    const width = Math.max(30, candidate.label.length * 12 + 14);
    const height = 20;
    const attempts = [0, 14, -14, 28, -28].map((offset) => ({
      x: candidate.x + candidate.normalX * offset,
      y: candidate.y + candidate.normalY * offset,
    }));
    const best = attempts.reduce((current, attempt) => {
      const attemptOverlap = overlapArea(attempt.x, attempt.y, width, height, placed);
      const currentOverlap = overlapArea(current.x, current.y, width, height, placed);
      return attemptOverlap < currentOverlap ? attempt : current;
    });
    placed.push({ ...candidate, ...best, width, height });
  }
  return placed;
}

function quadraticPoint(x1: number, y1: number, controlX: number, controlY: number, x2: number, y2: number, t: number) {
  const inverse = 1 - t;
  return {
    x: inverse * inverse * x1 + 2 * inverse * t * controlX + t * t * x2,
    y: inverse * inverse * y1 + 2 * inverse * t * controlY + t * t * y2,
  };
}

function overlapArea(x: number, y: number, width: number, height: number, placed: RelationLabelPlacement[]): number {
  const left = x - width / 2;
  const top = y - height / 2;
  return placed.reduce((area, item) => {
    const itemLeft = item.x - item.width / 2;
    const itemTop = item.y - item.height / 2;
    const overlapWidth = Math.max(0, Math.min(left + width, itemLeft + item.width) - Math.max(left, itemLeft));
    const overlapHeight = Math.max(0, Math.min(top + height, itemTop + item.height) - Math.max(top, itemTop));
    return area + overlapWidth * overlapHeight;
  }, 0);
}

function hashId(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}
