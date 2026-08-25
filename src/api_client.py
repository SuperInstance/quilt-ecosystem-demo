"""api_client.py — Use ZAI's GLM-4.5 to think deeply about the SuperInstance CRA project.

This script sends questions to the API in batches, with the full context
of the project. The goal is *thinking deep* — not just summarizing, but
exploring the implications, finding the unstated assumptions, mapping
the consequences, suggesting improvements.
"""
import urllib.request
import json
import os
import sys
import time

ZAI_TOKEN = os.environ["ZAI_TOKEN"]
DEEPSEEK_TOKEN = os.environ["DEEPSEEK_TOKEN"]
KIMI_TOKEN = os.environ["KIMI_TOKEN"]


def call_zai(prompt, model="glm-5.3", max_tokens=4096, system=None):
    """Call ZAI's chat completions API."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    req = urllib.request.Request(
        "https://api.z.ai/api/paas/v4/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {ZAI_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            msg = data["choices"][0]["message"]
            # GLM-5.3 returns reasoning_content separately; prefer content, fall back to reasoning
            content = msg.get("content") or ""
            if not content and msg.get("reasoning_content"):
                content = msg["reasoning_content"]
            return content
    except Exception as e:
        return f"[Error: {e}]"


def call_deepseek(prompt, max_tokens=4096, system=None):
    """Call DeepSeek's API."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {DEEPSEEK_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Error: {e}]"


def call_kimi(prompt, max_tokens=4096, system=None):
    """Call Kimi's API."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": "moonshot-v1-32k",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    req = urllib.request.Request(
        "https://api.moonshot.cn/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {KIMI_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Error: {e}]"


def think_deep(prompt, system=None, models=("zai", "deepseek", "kimi")):
    """Send a prompt to multiple LLMs and get their deep-thinking responses."""
    results = {}
    for m in models:
        if m == "zai":
            print(f"  -> ZAI (GLM-5.3)...  ", end=" ", flush=True)
            r = call_zai(prompt, system=system)
        elif m == "deepseek":
            print(f"  -> DeepSeek...        ", end=" ", flush=True)
            r = call_deepseek(prompt, system=system)
        elif m == "kimi":
            print(f"  -> Kimi...            ", end=" ", flush=True)
            r = call_kimi(prompt, system=system)
        if r.startswith("[Error"):
            print(f"FAILED")
        else:
            print(f"({len(r)} chars)")
        results[m] = r
        time.sleep(2)
    return results


def synthesize(question, results, model="glm-5.3"):
    """Take multiple LLM responses and synthesize them into a unified analysis."""
    synthesis_prompt = f"""You are a senior systems architect. Three different AI systems have
each analyzed a question about a complex production codebase. Your job is to
synthesize their findings into a single, unified, authoritative analysis.

THE QUESTION:
{question}

THE THREE RESPONSES:

=== RESPONSE A (ZAI GLM-5.3) ===
{results.get('zai', '[missing]')}

=== RESPONSE B (DeepSeek V3) ===
{results.get('deepseek', '[missing]')}

=== RESPONSE C (Kimi) ===
{results.get('kimi', '[missing]')}

YOUR TASK:
1. Identify findings that ALL THREE agree on (high confidence)
2. Identify findings only ONE found (might be unique insight)
3. Identify findings where they DISAGREE
4. Resolve disagreements with reasoning
5. Produce a final synthesis with:
   - Critical issues (must fix)
   - Important issues (should fix)
   - Minor issues (nice to fix)
   - Strengths to preserve
   - Open questions

Be specific. Cite the underlying code where applicable. Be concise.
"""
    return call_zai(synthesis_prompt, system="You are a senior systems architect.", max_tokens=4096)
