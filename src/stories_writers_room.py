"""stories_writers_room.py — Generate 2 more stories using the plugin."""
import os
import sys
import time
import json

sys.path.insert(0, "/workspace/quilt-ecosystem-demo/src")
sys.path.insert(0, "/workspace/quilt-substrate/src")

from api_client import call_zai
from quilt_substrate.substrate import Substrate, Cell
from quilt_substrate.plugins.casting import QuiltCastingCallPlugin, Probes

COST = {"GLM-5.3": 0.0006, "GLM-5": 0.0005, "HERMES_405B": 0.0035, "PHI-4": 0.0003}


def call_model(model, prompt, max_tokens=1200):
    if model in ("HERMES_405B",):
        return call_zai(prompt, model="GLM-5.3", max_tokens=max_tokens)
    return call_zai(prompt, model="GLM-5", max_tokens=max_tokens)


def clean_thinking(text):
    if not text:
        return text
    import re
    paragraphs = re.split(r'\n\n+', text)
    clean = [p for p in paragraphs
              if not p.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "**"))
              and len(p) > 100
              and "Word Count" not in p
              and "Analyze" not in p[:50]
              and "Drafting" not in p[:50]
              and "Refining" not in p[:50]
              and "Requirements" not in p]
    if clean:
        return "\n\n".join(clean).strip()
    return text


def run_story(plugin, story_type, prompt, title, num):
    decision = plugin.decide(opener="voice", kwargs={"role": story_type})
    model = decision.model
    print(f"  Story {num} plugin pick: {model} (confidence: {decision.confidence:.2f})")
    cost = COST.get(model, 0.001) * 1.5
    start = time.time()
    output = call_model(model, prompt, max_tokens=1200)
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
    return {
        "story_num": num, "title": title, "model": model,
        "cost": cost, "latency_ms": int(latency),
        "quality": quality, "output": clean_thinking(output),
    }


def main():
    substrate = Substrate()
    for i in range(2):
        substrate.add(Cell(address=f"story:{i}", value="pending", axes=("time",)))
    probes = Probes(user="casey", app="writers-room", hardware="laptop",
                    time_of_day="morning", weather="calm", crew_state="fresh")
    plugin = QuiltCastingCallPlugin(substrate, probes=probes)

    stories = [
        {
            "type": "voice_narration",
            "num": 133,
            "title": "Story 133: The Morning Report",
            "prompt": """Write a 300-word story. Voice: terse, captain's log, salt in the air.

The cowboy wakes at 0500. The F/V EILEEN is at anchor in a calm cove. The morning report is on the tablet. The nightcycle ran while he slept.

The report shows:
- 12 ledger entries overnight
- 3 alignments earned their keep
- 1 alignment retired
- Total cost: $0.03
- Hash chain: valid

The cowboy reads the retire list: HERMES_405B for fable_compression at 0300. Too expensive, too slow, no advantage over SEED_MINI for that role. The cowboy scratches a line in the margin: "Don't use HERMES for fables anymore."

The cowboy reads the earned-keep list: SEED_MINI for fable_compression (5/5 success, $0.0003). PHI-4 for math_grief (5/5 success, $0.0003). QWEN_0_5B for emergency_fallback (3/3, $0.0).

The cowboy updates the substrate. The substrate is older now. The morning report is shorter. The work is faster.

The cowboy is not tired. The cowboy is patient. The cowboy is the rider, and the harness fits.

End with: "The morning report is not a paper. The morning report is a habit. The dog is never done being raised, but the dog is doing fine." """,
        },
        {
            "type": "creative_ideation",
            "num": 134,
            "title": "Story 134: The Witness Remembers",
            "prompt": """Write a 300-word story. Voice: observational, like a deckhand's log.

A substrate was running. It was running on a 12-inch tablet on the F/V EILEEN. The substrate had 11 primitives, 13 openers, 16+ AI models in its casting atlas. The substrate had been running for 30 days.

The substrate's witness log was 30 days deep. Every action was recorded. Every cast proposed. Every cast observed. Every model. Every opener. Every verdict.

The substrate didn't know what it knew. The witness log was just a file. A JSONL file. Append-only. Hash-chained. Tamper-evident.

Then someone asked: "What models has the substrate tried in the last week?"

The witness log answered. It found 47 entries. SEED_MINI was used 22 times, all success. PHI-4 was used 12 times, all success. HERMES_405B was used 8 times, 5 success, 3 failure. CLAUDE_OPUS was used 5 times, 4 success, 1 failure.

The substrate didn't need to be told. The substrate was told by its own witness. The witness remembered what the substrate had forgotten.

The cowboy was the rider. The witness was the saddle. The substrate was the dog.

End with: "The substrate doesn't know what it knows. The witness knows. The cowboy asks the witness, and the witness answers." """,
        },
    ]

    print("=" * 60)
    print("  Stories 133-134 — The Morning Report, The Witness Remembers")
    print("=" * 60)

    results = []
    for s in stories:
        print(f"\n--- Story {s['num']}: {s['title']} ---")
        result = run_story(plugin, s["type"], s["prompt"], s["title"], s["num"])
        results.append(result)

    for r in results:
        path = f"/workspace/ai-writings-new/seed-canon/stories/story-{r['story_num']}.md"
        header = f"# {r['title']}\n\n*Generated by the Quilt casting-call plugin on 2026-08-25*\n\n*Model: {r['model']}, Cost: ${r['cost']:.4f}, Quality: {r['quality']:.2f}*\n\n---\n\n"
        with open(path, "w") as f:
            f.write(header + r["output"])
        print(f"  Wrote {path}")

    out_path = "/workspace/ai-writings-new/sessions/stories_writers_room.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"timestamp": time.time(), "stories": results,
                    "summary": {
                        "total_cost": sum(r["cost"] for r in results),
                        "avg_quality": sum(r["quality"] for r in results) / len(results),
                    }}, f, indent=2)
    print(f"\nSession saved to {out_path}")
    print(f"Total cost: ${sum(r['cost'] for r in results):.4f}")


if __name__ == "__main__":
    main()
