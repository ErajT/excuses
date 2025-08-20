from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import os
import glob
import requests
import tempfile
import shutil
import subprocess
import stat

# === Configuration ===
OPENROUTER_API_KEY = "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"
LLM_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "deepseek/deepseek-r1-0528:free"

app = FastAPI()

# === Request Body ===
class RepoRequest(BaseModel):
    url: str


# === Utility: File Selection ===
def select_entry_files(project_path):
    priority_files = [
        "README.md", "readme.md",
        "main.py", "server.py", "index.py",
        "app.js", "index.js", "server.js",
        "app.tsx", "index.tsx",
        "pom.xml", "build.gradle"
    ]
    files_found = []
    for f in priority_files:
        f_path = os.path.join(project_path, f)
        if os.path.exists(f_path):
            files_found.append(f_path)
    return files_found

# === Utility: Walk and Select Modules ===
def discover_module_files(project_path, max_files=10):
    code_files = glob.glob(os.path.join(project_path, '**/*.py'), recursive=True)
    code_files += glob.glob(os.path.join(project_path, '**/*.js'), recursive=True)
    code_files += glob.glob(os.path.join(project_path, '**/*.ts'), recursive=True)
    code_files += glob.glob(os.path.join(project_path, '**/*.java'), recursive=True)
    code_files += glob.glob(os.path.join(project_path, '**/*.cpp'), recursive=True)
    return code_files[:max_files]

# === Prompt Engineering ===
def prompt_for_summary(filename, content):
    return f"""
You are a senior developer onboarding a new engineer.
Explain the file `{filename}` in simple, clear terms for CLI viewing:
- Start with a brief overview.
- List key components or functions in bullet points.
- Mention how it connects to the system.
- Use markdown-style formatting (## headings, **bold**, `inline code`, code blocks if needed).
- Keep explanations clear and skimmable.

File content:
{content}
"""

# === Direct LLM Call ===
def call_llm_direct(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a senior developer helping onboard a new teammate."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(LLM_API_URL, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# === Explain Code File ===
def explain_code_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()[:150000]  # Keep within token limit
            prompt = prompt_for_summary(os.path.basename(file_path), content)
            return call_llm_direct(prompt)
    except Exception as e:
        return f"Error processing {file_path}: {e}"

# === Main Onboarding Flow ===
def onboard_codebase(project_path):
    entry_files = select_entry_files(project_path)
    module_files = discover_module_files(project_path)
    all_files = entry_files + [f for f in module_files if f not in entry_files]

    walkthrough = {}
    for f in all_files:
        print(f"\nExplaining {f}...")
        result = explain_code_file(f)
        walkthrough[f] = result

    return walkthrough

# === GitHub Clone Utility ===
def clone_github_repo(github_url):
    temp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "clone", github_url, temp_dir], check=True)
        return temp_dir
    except subprocess.CalledProcessError:
        print("❌ Failed to clone the repository.")
        shutil.rmtree(temp_dir)
        return None

def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# === API Endpoint ===
@app.post("/onboard", response_model=Dict[str, str])
def onboard_repo(req: RepoRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")

    if url.startswith("http://") or url.startswith("https://"):
        local_path = clone_github_repo(url)
        if not local_path:
            raise HTTPException(status_code=500, detail="Failed to clone repository")
        cloned = True
    else:
        if not os.path.exists(url):
            raise HTTPException(status_code=404, detail="Local path not found")
        local_path = url
        cloned = False

    try:
        result = onboard_codebase(local_path)
    finally:
        if cloned and os.path.exists(local_path):
            shutil.rmtree(local_path, onerror=on_rm_error)

    return result
