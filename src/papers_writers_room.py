"""papers_writers_room.py — Generate more papers using the plugin.

Papers 128, 129, 130 — three formal pieces on the new architecture.
"""
import os
import sys
import time
import json

sys.path.insert(0, "/workspace/quilt-ecosystem-demo/src")
sys.path.insert(0, "/workspace/quilt-substrate/src")

from api_client import call_zai
from quilt_substrate.substrate import Substrate, Cell
from quilt_substrate.plugins.casting import QuiltCastingCallPlugin, Probes

COST = {"GLM-5.3": 0.0006, "GLM-5": 0.0005, "PHI-4": 0.0003, "HERMES_405B": 0.0035}


def call_model(model, prompt, max_tokens=1500):
    if model in ("PHI-4", "GLM-5", "SEED_MINI"):
        return call_zai(prompt, model="GLM-5", max_tokens=max_tokens)
    if model in ("HERMES_405B",):
        return call_zai(prompt, model="GLM-5.3", max_tokens=max_tokens)
    return call_zai(prompt, model="GLM-5", max_tokens=max_tokens)


def clean_thinking(text):
    if not text:
        return text
    import re
    paragraphs = re.split(r'\n\n+', text)
    clean = [p for p in paragraphs
              if not p.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.",
                                            "**", "*"))
              and len(p) > 100
              and "Word Count" not in p
              and "Analyze" not in p[:50]
              and "Drafting" not in p[:50]
              and "Refining" not in p[:50]]
    if clean:
        return "\n\n".join(clean).strip()
    return text


def run_paper(plugin, paper_type, prompt, title, num):
    decision = plugin.decide(opener="reef", kwargs={"role": paper_type})
    model = decision.model
    print(f"  Paper {num} plugin pick: {model} (confidence: {decision.confidence:.2f})")
    cost = COST.get(model, 0.001) * 1.5
    start = time.time()
    output = call_model(model, prompt, max_tokens=1500)
    latency = (time.time() - start) * 1000
    success = bool(output) and not output.startswith("[Error")
    quality = 0.9 if success and len(output) > 800 else 0.7
    event = {
        "ts": time.time(),
        "kind": "cast.observed",
        "decision": {
            "model": model, "opener": decision.opener,
            "primitive": decision.primitive, "rationale": decision.rationale,
        },
        "latency_ms": int(latency),
        "success": success, "quality": quality, "cost": cost,
    }
    plugin.witness.append(event)
    plugin.wilson.observe(decision.primitive, decision.opener, model,
                            int(latency), success, quality)
    print(f"  Cost: ${cost:.4f}, Latency: {latency/1000:.1f}s, Quality: {quality:.2f}")
    cleaned = clean_thinking(output)
    return {
        "paper_num": num, "title": title, "model": model,
        "cost": cost, "latency_ms": int(latency),
        "quality": quality, "output": cleaned,
    }


def main():
    substrate = Substrate()
    for i in range(3):
        substrate.add(Cell(address=f"paper:{i}", value="pending", axes=("time",)))
    probes = Probes(user="casey", app="papers", hardware="laptop",
                    time_of_day="morning", weather="calm", crew_state="fresh")
    plugin = QuiltCastingCallPlugin(substrate, probes=probes)

    papers = [
        {
            "type": "math_grief",
            "num": 128,
            "title": "Paper 128: LinUCB and the Cowboy's Refinement",
            "prompt": """Write a 500-word paper on LinUCB (Linear Upper Confidence Bound) as applied to
the Quilt's casting-call plugin.

Topics:
1. The cold-start problem: with n<10, Wilson lower bound is the only signal
2. The warm-up: at n>=20, LinUCB takes over
3. The blend: 0.0 to 1.0 weight on LinUCB as data accumulates
4. The features: candidate identity (one-hot) + user + context (time, weather, battery, network, crew_state)
5. The alpha: exploration budget. Higher alpha in calm + full battery. Lower in gale + low battery
6. The per-(user, app) model: one A, one b per (user, app) pair
7. The cowboy's role: read the bandit output in the morning, refine the priors

End with: "The bandit is not the cowboy. The bandit is what the cowboy reads."

Voice: formal math paper but readable, like the F/V EILEEN's research log.""",
        },
        {
            "type": "math_grief",
            "num": 129,
            "title": "Paper 129: The Nightcycle's Refinement",
            "prompt": """Write a 500-word paper on the nightcycle — the scheduled pass that reads
saddle's ledger and produces a markdown report.

Topics:
1. The ledger: append-only JSONL, hash-chained (FNV-1a64), tamper-evident
2. The aggregation: per-(alignmentId) success/failure/escalation counts
3. The Wilson lower bound: per-alignment conservative estimate of success rate
4. The earned-keep rule: wilson_lower >= 0.5 AND n >= 5
5. The recommendations: retire failing alignments, pin earned-keep ones
6. The CLI: `python3 -m quilt_saddle_bridge.nightcycle ledger.jsonl --out report.md`
7. The composability: nightcycle can be run anytime, on any saddle-format ledger

End with: "The nightcycle is not a job. The nightcycle is a habit. The dog is never done being raised."

Voice: formal, like a research log entry on a sailboat.""",
        },
        {
            "type": "math_grief",
            "num": 130,
            "title": "Paper 130: The Witness as Index",
            "prompt": """Write a 500-word paper on the deckhand-backed witness — a persistent witness
for the Quilt substrate, backed by deckhand's BM25 search.

Topics:
1. The in-memory witness: lost on restart
2. The disk-backed witness: JSONL of events, queryable
3. The BM25 search: pure Python, no database, no model
4. The metadata filters: by kind, by model, by user
5. The use case: "what models has the plugin tried in the last 24 hours?"
6. The cowboy's question: not "what happened?" but "what's similar to what happened?"
7. The substrate becomes queryable: from ephemeral to indexed

End with: "The witness is not a log. The witness is a teacher. The substrate asks the witness, and the witness answers in tokens and ranks."

Voice: formal, observational, like a research log.""",
        },
    ]

    print("=" * 60)
    print("  Papers 128-130 — LinUCB, Nightcycle, Witness as Index")
    print("=" * 60)

    results = []
    for p in papers:
        print(f"\n--- Paper {p['num']}: {p['title']} ---")
        result = run_paper(plugin, p["type"], p["prompt"], p["title"], p["num"])
        results.append(result)

    # Save the papers
    for r in results:
        path = f"/workspace/ai-writings-new/seed-canon/papers/paper-{r['paper_num']}.md"
        header = f"# {r['title']}\n\n*Generated by the Quilt casting-call plugin on 2026-08-25*\n\n*Model: {r['model']}, Cost: ${r['cost']:.4f}, Quality: {r['quality']:.2f}*\n\n---\n\n"
        with open(path, "w") as f:
            f.write(header + r["output"])
        print(f"  Wrote {path}")

    # Save the session
    out_path = "/workspace/ai-writings-new/sessions/papers_writers_room.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"timestamp": time.time(), "papers": results,
                    "summary": {
                        "total_cost": sum(r["cost"] for r in results),
                        "avg_quality": sum(r["quality"] for r in results) / len(results),
                    }}, f, indent=2)
    print(f"\nSession saved to {out_path}")
    print(f"Total cost: ${sum(r['cost'] for r in results):.4f}")


if __name__ == "__main__":
    main()
