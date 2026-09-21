import { describe, expect, it } from "vitest";
import { buildCurvedEdge, placeRelationLabels } from "./knowledgeGraphGeometry";

describe("knowledge graph geometry", () => {
  it("routes an edge from node borders through a stable quadratic curve", () => {
    const edge = buildCurvedEdge({
      id: "relation_1",
      source: { x: 100, y: 100, radius: 20 },
      target: { x: 300, y: 100, radius: 20 },
      lane: 0,
    });

    expect(edge.x1).toBeGreaterThan(100);
    expect(edge.x2).toBeLessThan(300);
    expect(edge.controlY).not.toBe(100);
    expect(edge.path).toContain("Q");
  });

  it("moves colliding relation labels to separate stable positions", () => {
    const labels = placeRelationLabels([
      { id: "a", label: "取食", x: 160, y: 120, normalX: 0, normalY: -1 },
      { id: "b", label: "栖息于", x: 160, y: 120, normalX: 0, normalY: -1 },
    ]);

    expect(labels).toHaveLength(2);
    expect(labels[0].y).not.toBe(labels[1].y);
  });
});
