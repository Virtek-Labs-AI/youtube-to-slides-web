"""PR review script using Claude to analyze diffs and post verdicts."""

import json
import os
import sys
import urllib.request

import anthropic

MAX_DIFF_SIZE = 100_000  # 100KB

def read_diff(path: str) -> str:
    with open(path, "r") as f:
        content = f.read()
    if len(content) > MAX_DIFF_SIZE:
        content = content[:MAX_DIFF_SIZE] + "\n\n... [DIFF TRUNCATED — exceeded 100KB limit] ..."
    return content


def get_review(diff: str, pr_title: str, pr_body: str, base_ref: str, head_ref: str) -> str:
    client = anthropic.Anthropic()

    user_prompt = f"""Review this pull request.

**PR Title:** {pr_title}
**PR Description:** {pr_body or "No description provided."}
**Base branch:** {base_ref}
**Head branch:** {head_ref}

Check the following:
1. **Best practices**: Python (ruff-compliant, type hints, no bare except), TypeScript/Next.js (no implicit any, proper error handling)
2. **Security**: No secrets committed, no SQL injection, no unsafe CORS, no unvalidated inputs, no dangerouslySetInnerHTML
3. **Correctness**: Logic errors, null/undefined edge cases, regression risk
4. **Tests**: New functionality covered by tests?
5. **Standards**: PR title follows `<type>(<scope>): <description>` convention

Respond with EXACTLY this format:

VERDICT: PASS | FAIL

Findings:
- BLOCKER: <description>   ← must be fixed before merge
- WARNING: <description>   ← should be addressed
- NOTE:    <description>   ← informational

Summary: <2-3 sentences>

If there are no findings of a particular severity, omit that level. Always include at least a Summary.

**Diff:**
```
{diff}
```"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system="You are a senior code reviewer for a YouTube-to-slides SaaS application built with FastAPI (Python) and Next.js (TypeScript). Review PRs thoroughly and produce a structured verdict.",
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract text from response, skipping thinking blocks
    text_parts = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
    return "\n".join(text_parts)


def post_comment(repo: str, pr_number: str, body: str, token: str) -> None:
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    data = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        if resp.status not in (200, 201):
            print(f"Failed to post comment: {resp.status}")
            sys.exit(1)
    print("Review comment posted successfully.")


def main() -> None:
    diff_file = os.environ["DIFF_FILE"]
    pr_number = os.environ["PR_NUMBER"]
    pr_title = os.environ.get("PR_TITLE", "")
    pr_body = os.environ.get("PR_BODY", "")
    repo = os.environ["REPO"]
    base_ref = os.environ.get("BASE_REF", "")
    head_ref = os.environ.get("HEAD_REF", "")
    github_token = os.environ["GITHUB_TOKEN"]

    diff = read_diff(diff_file)
    if not diff.strip():
        print("Empty diff, skipping review.")
        return

    print("Requesting review from Claude...")
    review = get_review(diff, pr_title, pr_body, base_ref, head_ref)

    comment_body = f"## AI Code Review\n\n{review}"
    print("Posting review comment...")
    post_comment(repo, pr_number, comment_body, github_token)

    # Determine pass/fail
    is_fail = "VERDICT: FAIL" in review
    if is_fail:
        print("Review verdict: FAIL (blockers found)")
        sys.exit(1)
    else:
        print("Review verdict: PASS")


if __name__ == "__main__":
    main()
