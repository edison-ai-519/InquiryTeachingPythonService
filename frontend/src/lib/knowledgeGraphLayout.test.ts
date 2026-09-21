import { describe, expect, it } from "vitest";
import {
  buildInitialGraphPositions,
  graphLayoutProfile,
  placeExpandedGraphPositions,
  type GraphLayoutEntity,
} from "./knowledgeGraphLayout";

const entities: GraphLayoutEntity[] = Array.from({ length: 30 }, (_, index) => ({
  id: `entity_${String(index).padStart(2, "0")}`,
  name: `节点${String(30 - index).padStart(2, "0")}`,
}));

const structuredEntities: GraphLayoutEntity[] = [
  { id: "leaf", name: "叶片" },
  { id: "root", name: "核心节点" },
  { id: "first", name: "一级节点" },
  { id: "second", name: "二级节点" },
];

describe("knowledge graph layout", () => {
  it("creates the same positions regardless of input order", () => {
    const forward = buildInitialGraphPositions(entities, "normal");
    const reversed = buildInitialGraphPositions([...entities].reverse(), "normal");

    expect([...forward.entries()]).toEqual([...reversed.entries()]);
  });

  it("uses more than one ring for a dense graph", () => {
    const positions = buildInitialGraphPositions(entities, "normal");
    const rings = new Set([...positions.values()].map((position) => position.ring));

    expect(rings.size).toBeGreaterThan(1);
  });

  it("places the focus and its graph neighbors on successive rings", () => {
    const positions = buildInitialGraphPositions(structuredEntities, "normal", [
      { subject_entity_id: "root", object_entity_id: "first" },
      { subject_entity_id: "first", object_entity_id: "second" },
    ], "root");

    expect(positions.get("root")).toMatchObject({ xRatio: 0.5, yRatio: 0.5, ring: 0 });
    expect(positions.get("first")?.ring).toBe(1);
    expect(positions.get("second")?.ring).toBe(2);
    expect(positions.get("leaf")?.ring).toBeGreaterThanOrEqual(2);
  });

  it("keeps existing positions while placing expanded nodes near their source", () => {
    const initial = buildInitialGraphPositions(entities.slice(0, 8), "normal");
    const sourceId = entities[0].id;
    const sourcePosition = initial.get(sourceId)!;
    const expanded = placeExpandedGraphPositions(initial, sourceId, entities.slice(8, 11), "normal");

    expect(expanded.get(sourceId)).toEqual(sourcePosition);
    for (const entity of entities.slice(8, 11)) {
      const position = expanded.get(entity.id)!;
      expect(Math.hypot(position.xRatio - sourcePosition.xRatio, position.yRatio - sourcePosition.yRatio)).toBeLessThan(0.3);
    }
  });

  it("keeps a tall narrow user panel in the compact profile", () => {
    expect(graphLayoutProfile(420, 820, "full", false)).toBe("compact");
    expect(graphLayoutProfile(1200, 720, "map", true)).toBe("fullscreen");
  });
});
