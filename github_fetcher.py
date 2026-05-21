import os
import re
import requests
from typing import Optional

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

def extract_repo_info(url: str) -> Optional[tuple[str, str]]:
    """Extract owner and repo name from a GitHub URL."""
    pattern = r"github\.com/([^/]+)/([^/\s]+)"
    match = re.search(pattern, url)
    if not match:
        return None
    owner = match.group(1)
    repo = match.group(2).rstrip("/").replace(".git", "")
    return owner, repo

def fetch_repo_contents(owner: str, repo: str, path: str = "") -> list[dict]:
    """Recursively fetch file contents from a GitHub repo."""
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        return []

    items = resp.json()
    files = []

    # Skip noisy files/folders that don't help with learning analysis
    SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
    SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".lock", ".sum"}
    MAX_FILE_SIZE = 50_000  # 50KB per file
    MAX_FILES = 20          # Don't overwhelm the LLM

    if isinstance(items, dict):
        # Single file
        items = [items]

    for item in items:
        if len(files) >= MAX_FILES:
            break

        name = item.get("name", "")
        item_type = item.get("type", "")

        if any(skip in name for skip in SKIP_DIRS):
            continue
        if any(name.endswith(ext) for ext in SKIP_EXTS):
            continue

        if item_type == "dir":
            sub_files = fetch_repo_contents(owner, repo, item["path"])
            files.extend(sub_files)
        elif item_type == "file":
            size = item.get("size", 0)
            if size > MAX_FILE_SIZE:
                files.append({"path": item["path"], "content": f"[File too large to display: {size} bytes]"})
                continue

            file_resp = requests.get(item["download_url"], headers=headers, timeout=10)
            if file_resp.status_code == 200:
                files.append({"path": item["path"], "content": file_resp.text})

    return files

def format_repo_for_analysis(owner: str, repo: str) -> str:
    """Fetch a repo and format it as a single text block for the pipeline."""
    files = fetch_repo_contents(owner, repo)

    if not files:
        return f"[Could not fetch repo: {owner}/{repo}]"

    lines = [f"# GitHub Repository: {owner}/{repo}\n"]
    for f in files:
        lines.append(f"## File: {f['path']}")
        lines.append(f['content'])
        lines.append("")

    return "\n".join(lines)

def get_project_context(input_text: str) -> tuple[str, str]:
    """
    Given user input (GitHub URL or pasted code), return:
    - (context_text, source_label)
    """
    # Check if it looks like a GitHub URL
    if "github.com" in input_text:
        result = extract_repo_info(input_text)
        if result:
            owner, repo = result
            print(f"[GitHub] Fetching {owner}/{repo}...")
            context = format_repo_for_analysis(owner, repo)
            return context, f"github:{owner}/{repo}"

    # Otherwise treat as pasted code/description
    return input_text, "pasted"
