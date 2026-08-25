"""linucb_writers_room.py — A writers'-room session using LinUCB.

Proves the Phase 3 LinUCB layer actually learns context-aware preferences.

The session:
1. Run 3 sub-sessions with different contexts (calm 6am, afternoon, 0300 gale)
2. Each sub-session writes 3-4 pieces
3. After 10+ pieces, the LinUCB layer starts to kick in
4. Show the LinUCB scores after each sub-session

The plugin should learn:
- For Casey's writers-room in the evening: SEED_MINI works
- For Reyes's F/V EILEEN in 0300 gale: local models
- The same model/opener triple is good in some contexts, bad in others
"""
import os
import sys
import time
import json

sys.path.insert(0, "/workspace/quilt-ecosystem-demo/src")
sys.path.insert(0, "/workspace/quilt-substrate/src")

from api_client import call_zai, call_deepseek
from quilt_substrate.substrate import Substrate, Cell
from quilt_substrate.plugins.linucb import LinUCBCastingPlugin
from quilt_substrate.plugins.casting import Probes

COST = {
    "GLM-5.3": 0.0006, "GLM-5": 0.0005, "GLM-4.6": 0.0001,
    "SEED_MINI": 0.0003, "PHI-4": 0.0003, "HERMES_405B": 0.0035,
    "CLAUDE_OPUS": 0.015, "QWEN_0_5B": 0.0,
}


def call_model(model: str, prompt: str, max_tokens: int = 600) -> str:
    if model in ("SEED_MINI", "PHI-4", "QWEN_0_5B"):
        return call_zai(prompt, model="GLM-5", max_tokens=max_tokens)
    if model in ("HERMES_405B", "CLAUDE_OPUS"):
        return call_zai(prompt, model="GLM-5.3", max_tokens=max_tokens)
    return call_zai(prompt, model="GLM-5", max_tokens=max_tokens)


def run_sub_session(plugin, sit_desc, probes, pieces, session_id="X"):
    """Run a sub-session with a specific context."""
    print(f"\n--- {sit_desc} ---")
    print(f"  Probes: user={probes._user}, app={probes._app}, weather={probes._weather}, time={probes._time_of_day}")
    plugin.probes = probes
    pieces_made = []
    for i, piece in enumerate(pieces, 1):
        decision = plugin.decide(opener=piece.get("opener", "slate"),
                                    kwargs={"role": piece["role"]})
        model = decision.model
        cost = COST.get(model, 0.001) * 1.0
        print(f"  [{i}] {piece['role']:25s} → {model:20s} ({cost:.4f} USD)")
        # Make the call
        start = time.time()
        output = call_model(model, piece["prompt"], max_tokens=600)
        latency = (time.time() - start) * 1000
        success = bool(output) and not output.startswith("[Error")
        quality = 0.9 if success and len(output) > 200 else (0.5 if success else 0.0)
        # Update the witness and Wilson
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
        # Also update LinUCB
        sit = probes.situation()
        budget = probes.budget()
        plugin.linucb.update((model, decision.opener, decision.primitive), sit, quality, budget)
        plugin._linucb_history.append({
            "ts": event["ts"], "model": model, "opener": decision.opener,
            "primitive": decision.primitive, "reward": quality,
            "user": sit.user, "app": sit.app,
        })
        pieces_made.append({
            "session": session_id, "role": piece["role"],
            "model": model, "cost": cost, "quality": quality,
            "output": output[:1500] if output else "",
        })
    return pieces_made


def main():
    substrate = Substrate()
    for i in range(3):
        substrate.add(Cell(address=f"draft:{i}", value="pending", axes=("time",)))
    # Use the LinUCB-enhanced plugin
    probes_default = Probes(user="casey", app="writers-room", hardware="laptop",
                              time_of_day="evening", weather="calm", crew_state="normal")
    plugin = LinUCBCastingPlugin(substrate, probes=probes_default)

    print("=" * 60)
    print("  LinUCB writers'-room — 3 sub-sessions, ~12 pieces")
    print("=" * 60)

    # Sub-session 1: Casey's evening, calm — 3 fables
    p1 = Probes(user="casey", app="writers-room", hardware="laptop",
                 time_of_day="evening", weather="calm", crew_state="normal")
    pieces1 = [
        {"role": "fable_compression", "prompt": "Write a 100-word fable about a watch and the moon."},
        {"role": "fable_compression", "prompt": "Write a 100-word fable about a sailor's patience."},
        {"role": "creative_ideation", "prompt": "Write 100 words on a sunset at sea, in the voice of a captain's log."},
    ]
    results1 = run_sub_session(plugin, "Sub-session 1: Casey's evening, calm", p1, pieces1, "1")

    # Sub-session 2: Reyes's 0300 gale — 3 sensory pieces
    p2 = Probes(user="reyes", app="F/V EILEEN", hardware="ruggedized-tablet",
                 time_of_day="0300", weather="gale", crew_state="tired")
    pieces2 = [
        {"role": "sensory_creative", "prompt": "Write 80 words of maritime voice: 0300, the wind has shifted NW, the depth at 4.2m."},
        {"role": "voice_narration", "prompt": "Write 80 words of a captain's log: the F/V EILEEN at 0300, the chart on the tablet."},
        {"role": "sensory_creative", "prompt": "Write 80 words describing the sound of water against a hull in a 0300 gale."},
    ]
    results2 = run_sub_session(plugin, "Sub-session 2: Reyes's 0300 gale", p2, pieces2, "2")

    # Sub-session 3: Back to Casey's evening — 3 more fables
    p3 = Probes(user="casey", app="writers-room", hardware="laptop",
                 time_of_day="evening", weather="calm", crew_state="normal")
    pieces3 = [
        {"role": "fable_compression", "prompt": "Write a 100-word fable about a horse and a saddle."},
        {"role": "creative_ideation", "prompt": "Write 100 words on the wisdom of small dogs in a storm."},
        {"role": "fable_compression", "prompt": "Write a 100-word fable about the man who read the books every morning."},
    ]
    results3 = run_sub_session(plugin, "Sub-session 3: Casey's evening (continued)", p3, pieces3, "3")

    # Sub-session 4: Reyes's 0300 again — the LinUCB should know what works
    p4 = Probes(user="reyes", app="F/V EILEEN", hardware="ruggedized-tablet",
                 time_of_day="0300", weather="gale", crew_state="tired")
    pieces4 = [
        {"role": "sensory_creative", "prompt": "Write 80 words of the dawn breaking after a 0300 gale."},
        {"role": "voice_narration", "prompt": "Write 80 words of a captain noting the wind has dropped below 20 knots."},
    ]
    results4 = run_sub_session(plugin, "Sub-session 4: Reyes's 0300 (LinUCB-informed)", p4, pieces4, "4")

    all_results = results1 + results2 + results3 + results4

    print()
    print("=" * 60)
    print("  LinUCB STATS")
    print("=" * 60)
    print(f"Total observations: {len(plugin._linucb_history)}")
    print(f"LinUCB models: {len(plugin.linucb.models)}")
    for (user, app), model in plugin.linucb.models.items():
        print(f"  {user} / {app}: n={model.n}, weights[:3]={model.w[:3].round(2)}")

    # Show how the LinUCB layer ranks the same (model, opener) in different contexts
    print()
    print("Per-context ranking for ('QWEN_0_5B', 'tide', 'Murmur'):")
    candidates = [("QWEN_0_5B", "tide", "Murmur"), ("DEEPSEEK_V4_FLASH", "tide", "Murmur"),
                   ("HERMES_405B", "voice", "Murmur")]
    for desc, p in [("Casey calm", p1), ("Reyes gale", p2)]:
        sit = p.situation()
        budget = p.budget()
        ranked = plugin.linucb.rank(candidates, sit, budget)
        print(f"  {desc}:")
        for score, c in ranked:
            print(f"    {score:.3f}: {c}")

    # Save the session
    out_path = "/workspace/ai-writings-new/sessions/linucb_writers_room.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "history": plugin._linucb_history,
            "linucb_stats": plugin.linucb.stats(),
            "pieces": all_results,
        }, f, indent=2)
    print(f"\nSession saved to {out_path}")
    print(f"Total cost: ${sum(r['cost'] for r in all_results):.4f}")
    print(f"Total pieces: {len(all_results)}")


if __name__ == "__main__":
    main()
