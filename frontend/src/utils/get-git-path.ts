/**
 * Get the git repository path for a conversation.
 * Returns path relative to workspace root (/workspace) to avoid double-prefixing
 * (agent server joins workspace root + path; passing "/workspace/project/x" causes
 * /workspace/workspace/project/x). For GitHub "owner/repo" use repo; for Azure DevOps
 * "org/project/repo" use repo (the last part).
 *
 * @param selectedRepository The selected repository (e.g., "OpenHands/OpenHands", "msci-otw/index-apps/cnpg-postgresql")
 * @returns The git path relative to /workspace (e.g., "project/index-apps")
 */
export function getGitPath(
  selectedRepository: string | null | undefined,
): string {
  if (!selectedRepository) {
    return "project";
  }

  const parts = selectedRepository.split("/");
  // GitHub: owner/repo -> repo; Azure DevOps: org/project/repo -> repo
  const repoName = parts.length > 1 ? parts[parts.length - 1] : parts[0];

  return `project/${repoName}`;
}
