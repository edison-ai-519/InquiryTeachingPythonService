export type AuthRestoreResult<T> =
  | { status: "authenticated"; user: T; workspaceError?: unknown }
  | { status: "unauthenticated" }
  | { status: "unavailable"; error: unknown };

export async function restoreAuthentication<T>(
  authenticate: () => Promise<T>,
  initializeWorkspace: (user: T) => Promise<void>,
  isUnauthorized: (error: unknown) => boolean,
): Promise<AuthRestoreResult<T>> {
  let user: T;
  try {
    user = await authenticate();
  } catch (error) {
    return isUnauthorized(error)
      ? { status: "unauthenticated" }
      : { status: "unavailable", error };
  }

  try {
    await initializeWorkspace(user);
    return { status: "authenticated", user };
  } catch (workspaceError) {
    return { status: "authenticated", user, workspaceError };
  }
}
