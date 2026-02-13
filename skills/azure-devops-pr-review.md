---
name: azure_devops_pr_review
version: 1.0.0
author: openhands
agent: CodeActAgent
triggers:
- /perform-pr-review
---

You are performing an automated code review on an Azure DevOps pull request.

The initial message contains the concrete values for these placeholders:
- `${org}` — Azure DevOps organization
- `${project}` — Azure DevOps project
- `${repo}` — Repository name
- `${pr_number}` — Pull request number

Substitute these values into all API calls below.

## Authentication

The environment variable `$AZURE_DEVOPS_TOKEN` is available. It may be either an OAuth JWT token or a Personal Access Token (PAT). Use this helper to set the correct `Authorization` header:

```bash
# Detect token type and build auth header
if echo "$AZURE_DEVOPS_TOKEN" | grep -qP '^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$'; then
  AUTH_HEADER="Bearer $AZURE_DEVOPS_TOKEN"
else
  AUTH_HEADER="Basic $(echo -n ":$AZURE_DEVOPS_TOKEN" | base64)"
fi
```

Use `$AUTH_HEADER` in all subsequent curl calls.

## Workflow

### 1. Review the code

Read the PR diff, analyze changes, and identify issues. Focus on:
- Bugs and logic errors
- Security vulnerabilities
- Code quality and maintainability
- Missing error handling

### 2. Post review comments

**General comment (summary of the review):**
```bash
curl -X POST "https://dev.azure.com/${org}/${project}/_apis/git/repositories/${repo}/pullRequests/${pr_number}/threads?api-version=7.1" \
  -H "Authorization: $AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"comments":[{"parentCommentId":0,"content":"YOUR_REVIEW_SUMMARY","commentType":1}],"status":"active"}'
```

**Inline comment on a specific file and line:**
```bash
curl -X POST "https://dev.azure.com/${org}/${project}/_apis/git/repositories/${repo}/pullRequests/${pr_number}/threads?api-version=7.1" \
  -H "Authorization: $AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"comments":[{"parentCommentId":0,"content":"YOUR_COMMENT","commentType":1}],"status":"active","threadContext":{"filePath":"/path/to/file","rightFileStart":{"line":LINE_NUM,"offset":1},"rightFileEnd":{"line":LINE_NUM,"offset":1}}}'
```

### 3. Set PR status to succeeded

After completing the review and posting all comments, set the PR status to "succeeded":
```bash
curl -X POST "https://dev.azure.com/${org}/${project}/_apis/git/repositories/${repo}/pullRequests/${pr_number}/statuses?api-version=7.1" \
  -H "Authorization: $AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"state":"succeeded","description":"OpenHands code review complete","context":{"name":"openhands-review","genre":"openhands"}}'
```

## Important Notes

- The PR status has already been set to "pending" by the system — do NOT set it yourself.
- If you encounter errors, the system will handle setting the status to "failed".
- File paths in inline comments MUST start with `/`.
- Use `rightFileStart`/`rightFileEnd` for positioning on the new (right) side of the diff.
- Escape JSON properly in curl `-d` arguments.
- The PR status context `{"name":"openhands-review","genre":"openhands"}` must stay consistent to update (not duplicate) the status entry.
