import assert from "node:assert/strict";
import test from "node:test";

import { restoreAuthentication } from "../src/authBootstrap.ts";

test("workspace initialization failure keeps the authenticated user", async () => {
  const user = { id: "user-1" };
  const result = await restoreAuthentication(
    async () => user,
    async () => {
      throw new Error("parent session request failed");
    },
    (error) => (error as { status?: number }).status === 401,
  );

  assert.equal(result.status, "authenticated");
  if (result.status === "authenticated") {
    assert.equal(result.user, user);
    assert.match(String(result.workspaceError), /parent session request failed/);
  }
});

test("a rejected session check is the only failure that returns to login", async () => {
  const result = await restoreAuthentication(
    async () => {
      throw Object.assign(new Error("expired"), { status: 401 });
    },
    async () => undefined,
    (error) => (error as { status?: number }).status === 401,
  );

  assert.deepEqual(result, { status: "unauthenticated" });
});

test("a failed auth check that is not unauthorized is reported as unavailable", async () => {
  const result = await restoreAuthentication(
    async () => {
      throw Object.assign(new Error("server unavailable"), { status: 503 });
    },
    async () => undefined,
    (error) => (error as { status?: number }).status === 401,
  );

  assert.equal(result.status, "unavailable");
  if (result.status === "unavailable") {
    assert.match(String(result.error), /server unavailable/);
  }
});
