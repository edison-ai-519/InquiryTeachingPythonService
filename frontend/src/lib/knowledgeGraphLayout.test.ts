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

  it("places descendants in the outward local sector of their parent", () => {
    const branchEntities: GraphLayoutEntity[] = [
      { id: "root", name: "中心" },
      { id: "north", name: "分支甲" },
      { id: "east", name: "分支乙" },
      { id: "south", name: "分支丙" },
      { id: "west", name: "分支丁" },
      { id: "west-leaf", name: "叶节点甲" },
      { id: "south-leaf", name: "叶节点乙" },
      { id: "east-leaf", name: "叶节点丙" },
      { id: "north-leaf", name: "叶节点丁" },
    ];
    const relations = [
      { subject_entity_id: "root", object_entity_id: "north" },
      { subject_entity_id: "root", object_entity_id: "east" },
      { subject_entity_id: "root", object_entity_id: "south" },
      { subject_entity_id: "root", object_entity_id: "west" },
      { subject_entity_id: "north", object_entity_id: "north-leaf" },
      { subject_entity_id: "east", object_entity_id: "east-leaf" },
      { subject_entity_id: "south", object_entity_id: "south-leaf" },
      { subject_entity_id: "west", object_entity_id: "west-leaf" },
    ];
    const positions = buildInitialGraphPositions(branchEntities, "normal", relations, "root");
    const root = positions.get("root")!;

    for (const [parentId, childId] of [["north", "north-leaf"], ["east", "east-leaf"], ["south", "south-leaf"], ["west", "west-leaf"]]) {
      const parent = positions.get(parentId)!;
      const child = positions.get(childId)!;
      const parentOutwardX = parent.xRatio - root.xRatio;
      const parentOutwardY = parent.yRatio - root.yRatio;
      const childDirectionX = child.xRatio - parent.xRatio;
      const childDirectionY = child.yRatio - parent.yRatio;

      expect(parentOutwardX * childDirectionX + parentOutwardY * childDirectionY).toBeGreaterThan(0);
    }
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
