"""Finalize this writing/planning milestone; never imports training code.

Run once from the local WSL environment after independent reviews are complete.
Historical evidence is read and hash-checked; only this package and six named
root navigation documents are written. Refuses an existing completion record.
"""
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent.parent
REL = PACKAGE.relative_to(ROOT).as_posix()


def read(path):
    return path.read_text(encoding="utf-8-sig")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, text):
    assert path.resolve().is_relative_to(ROOT)
    path.write_text(text, encoding="utf-8", newline="\n")


def save(path, obj):
    write(path, json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def record(path):
    return {"path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size, "sha256": digest(path)}


def main():
    assert not (PACKAGE / "COMPLETION.json").exists(), "Already completed"
    now = datetime.now(timezone.utc).isoformat()
    reviews = []
    for name in ("NOTE_REVIEW.json", "PROTOCOL_REVIEW.json"):
        data = json.loads(read(PACKAGE / name))
        reviews.append({"file": name, "sha256": digest(PACKAGE / name),
                        "review": data})
    # Root separately reads and approves the two records before calling this.
    # Do not infer acceptance merely because the files exist.
    approval = json.loads(read(PACKAGE / "ROOT_ACCEPTANCE.json"))
    assert approval["status"] == "PASS_WRITING_AND_DESIGN_MILESTONE"
    for item in approval["reviewed_files"]:
        assert digest(PACKAGE / item["file"]) == item["sha256"], item
    protocol_sources = reviews[1]["review"]["source_evidence"]
    for target, expected in protocol_sources.items():
        assert digest(ROOT / target) == expected, target

    inventory = []
    pattern = r"^\| (S\d+[A-Z]) \| \[[^\]]+\]\(([^)]+)\) \| `([a-f0-9]{64})` \|$"
    for source_id, target, expected in re.findall(pattern, read(PACKAGE / "CLAIMS.md"), re.M):
        path = (PACKAGE / target).resolve()
        assert path.is_relative_to(ROOT)
        assert digest(path) == expected, source_id
        inventory.append({"source_id": source_id, **record(path)})
    assert len(inventory) == 20, len(inventory)
    literature = json.loads(read(PACKAGE / "LITERATURE_SOURCES.json"))
    assert literature["source_count"] == len(literature["sources"]) == 10
    assert all(item["primary_source"] for item in literature["sources"])

    roots = ["HANDOFF.md", "NEXT_EXPERIMENT.md", "RUNBOOK.md", "CODEX_START.md",
             "RESEARCH_STATE.json", "RESEARCH_GOAL.md"]
    backup = PACKAGE / "context_before"
    assert not backup.exists(), "Partial finalization: inspect before retry"
    backup.mkdir()
    for name in roots:
        (backup / name).write_bytes((ROOT / name).read_bytes())

    handoff = read(ROOT / "HANDOFF.md")
    handoff = re.sub(r"\*\*Latest continuation status:\*\*[^\n]+",
        "**Latest continuation status:** The Stage 2–10 writing/literature/design milestone is complete "
        "(30 September 2026). Section 19 records the reviewed paper-track package and next proposed "
        "rule-tying experiment. Stage 10 remains the latest measured experiment. "
        "No new training was run; implementation readiness and a pre-outcome freeze remain pending.",
        handoff, count=1)
    handoff += f"""

## 19. Paper-track milestone complete — 30 September 2026

The user requested continued progress and a goal that keeps the project aligned
with Jane Street. The bounded writing/planning goal is now complete:
`{REL}/README.md` links the research note, 13-claim ledger,
ten-primary-source literature review, alignment rationale and proposed protocol.
`REVIEW.json`, `MANIFEST.json` and `COMPLETION.json` record review and provenance.
The broader empirical mechanism question remains open.

Independent reviews corrected two scientific details in the new documents:
Stage 4's 15 main random-arm policy gates fail, but six early secondary S/M cells
pass; and total-loss gains subtract in float32 before promotion, whereas the
historical component diagnostics promote component losses before subtraction.
Component p* uses the 1e-10 guard; 3e-10 belongs only to pooled allocation.
All frozen reports, code, measurements and earlier estimates remain preserved.
The 20 cited historical report/JSON source hashes were rechecked successfully.

Current evidence supports a bounded methodological case study, without a major
advance over Jane Street, exact large-LM replication, or established novelty.
Stage 6's primary U/R/random middle utility fails in all four panels, while its
M controls pass utility/scaling. Stage 10's numerical agreement leaves this
scientific distinction intact. Only scripts were historically executed.

### Next concrete preparation

Read `{REL}/NEXT_PROTOCOL_DRAFT.md` and
`DESIGN_RATIONALE.md`. The proposed experiment compares the original 16 group
rules (G16) against one tied rule (G1), using the same U checkpoint, paired data
skeleton, weights and batch orders. Changed answers also change later
teacher-forced inputs; full token equality is required within each condition.
Fixed-optimizer epoch-10 group learning and validation-selected total utility
are separate branches. No p*, peak or test score selects hyperparameters.

The design proposes two tuning pairs and five fresh confirmation corpora with
two nested model/weight seeds, at most 312 adaptation trajectories and 36 U
pretrained checkpoints. A 90-minute training ceiling and 4 GiB new-storage
ceiling are provisional until measured resource fixtures establish feasibility.
Middle-capacity continuation requires positive relative group response, positive
absolute G1 group learning, and selected G1 utility in all five corpus means.
All failures stay reported. No significance or peak result is required.

Next: implement new versioned source locally, audit fixtures and seed inventory,
benchmark the resource schedule, independently review, then freeze source,
protocol, seeds and analysis before any research outcomes. This package is a
reviewed proposal, not an implemented, frozen or executed experiment. Do not
duplicate Stages 2–10 or start another numerical audit absent a concrete failure.
No cloud job, upload, publication or spending was performed or authorized here.
"""
    write(ROOT / "HANDOFF.md", handoff)

    next_text = f"""# Current next step — implement the reviewed rule-tying proposal

The Stage 2–10 research-note, literature and next-design milestone is complete
(30 September 2026). Read `{REL}/README.md`,
`RESEARCH_NOTE.md`, `CLAIMS.md` and `NEXT_PROTOCOL_DRAFT.md` in that package.
Review and provenance: `REVIEW.json`, `MANIFEST.json`, `COMPLETION.json`.
The goal's scientific direction remains in `RESEARCH_GOAL.md`.

The next proposed experiment tests G1 versus G16 group-rule sharing under paired
U pretraining. It separates fixed F10 component learning from validation-only
selection including epoch zero. Two fresh tuning pairs, five fresh confirmation
corpora × two nested seeds, <=312 trajectories, 36 pretrained models. The
90-minute/4 GiB bounds still require a local resource benchmark.

Implement in new versioned source; verify data/label pairing, component arithmetic,
selection, aggregation, fresh seed inventory and resource feasibility. Obtain an
independent implementation review and freeze all source/protocol/analysis before
new outcomes. The draft's go/stop criteria require useful total adaptation and
positive absolute and relative group learning; p* never drives continuation.
Routine local preparation is authorized by the user's continuation instruction.
The proposal is not yet implemented, frozen or executed. No training is active.

Stage 10 remains the latest measured experiment. Preserve all original estimates,
guards, successful secondary controls and failed primary gates. See HANDOFF
section 19 for this milestone and section 18 for Stage 10.

## Historical completed recommendations

Everything below records earlier continuation points and is superseded by the
current next step above; do not relaunch a completed stage.

"""
    write(ROOT / "NEXT_EXPERIMENT.md", next_text + read(ROOT / "NEXT_EXPERIMENT.md"))

    runbook = read(ROOT / "RUNBOOK.md")
    runbook = runbook.replace("## Start new research\n", f"""## Start new research

### Current: paper-track milestone complete; experiment implementation pending

Read HANDOFF section 19 and `{REL}/NEXT_PROTOCOL_DRAFT.md`.
The research note, focused literature review and design passed independent review.
There is no new training result or active experiment. Prepare versioned source,
outcome-independent fixtures, seed inventory and a local resource benchmark;
source-bound implementation review and freeze must precede research outcomes.
Use the existing WSL Python and GPU. Current proposed ceilings are 90 minutes
and 4 GiB new storage with a 2 GiB reserve; readiness has not been measured.
The historical stage instructions below are completed records, not launch commands.

""", 1)
    runbook = runbook.replace("Stage 10 continuous-search agreement is now authorized; see current preparation status above.",
                              "Stage 10 continuous-search agreement is complete; see its completion record above.")
    write(ROOT / "RUNBOOK.md", runbook)

    start = read(ROOT / "CODEX_START.md").replace(
        "# Current continuation point — 30 September 2026",
        "# Historical continuation point after Stage 10", 1)
    write(ROOT / "CODEX_START.md", f"""# Current continuation point — reviewed scientific proposal

Read AGENTS.md, HANDOFF.md (latest section 19), NEXT_EXPERIMENT.md, RUNBOOK.md
and the Stage 1 report before extending research. Stages 2–10 are complete.
The writing/literature/design milestone in `{REL}/` is also
complete; start with README.md, RESEARCH_NOTE.md and NEXT_PROTOCOL_DRAFT.md.

The next task is implementation readiness for the proposed G1/G16 rule-tying
experiment: new versioned source, outcome-independent fixtures, seed inventory,
local resource benchmark, independent implementation review and pre-outcome
freeze. No new model outcome exists; no training process is active. Preserve
old stages and every failure/undefined result. Use validation-only selection,
paired controls and independent corpus units. Do not use p* to select or expand
an experiment. Keep all work local on D: through the existing Ubuntu WSL runtime.
The reviewed document is a plan, not an execution freeze or measured readiness.

""" + start)

    state = json.loads(read(ROOT / "RESEARCH_STATE.json"))
    state["completed"].append("paper-track-v1-writing-literature-design")
    state["next"] = "implement, fixture-check and benchmark reviewed G1/G16 rule-tying proposal before an independent pre-outcome freeze"
    state["next_status"] = "local preparation authorized; design reviewed; implementation/resource readiness and freeze pending"
    state["latest_completed_milestone"] = "paper-track-v1-writing-literature-design"
    state["latest_milestone_completion"] = f"{REL}/COMPLETION.json"
    state["latest_research_note"] = f"{REL}/RESEARCH_NOTE.md"
    state["next_protocol_draft"] = f"{REL}/NEXT_PROTOCOL_DRAFT.md"
    state["next_protocol_status"] = "proposed_not_implemented_not_frozen_not_executed"
    state["active_experiment"] = None
    state["updated_date"] = now[:10]
    state["updated_utc"] = now
    write(ROOT / "RESEARCH_STATE.json", json.dumps(state, indent=2, ensure_ascii=False) + "\n")

    goal = read(ROOT / "RESEARCH_GOAL.md")
    goal = goal.replace("## Active milestone", "## Completed writing and planning milestone", 1)
    goal = goal.replace("The active tool goal has no user-specified token budget.",
        f"Completion and independent review are recorded in `{REL}/COMPLETION.json`.\n"
        "The user specified no token budget. The broader mechanism question remains open;\n"
        "the next operational step is implementation readiness for the reviewed proposal.", 1)
    write(ROOT / "RESEARCH_GOAL.md", goal)

    local_links = []
    for path in PACKAGE.glob("*.md"):
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", read(path)):
            if re.match(r"https?://|#", target):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            assert resolved.exists(), (path.name, target)
            local_links.append({"file": path.name, "target": target})
    # Source hashes are checked again after navigation edits.
    for item in inventory:
        assert digest(ROOT / item["path"]) == item["sha256"]

    review = {"schema_version": 1, "status": "PASS_WRITING_AND_DESIGN_MILESTONE",
        "completed_utc": now, "independent_reviews": reviews,
        "root_acceptance": approval,
        "checks": {"historical_sources_hash_verified": len(inventory),
            "additional_protocol_source_hashes_verified": len(protocol_sources),
            "primary_literature_sources": 10, "local_markdown_links_checked": len(local_links),
            "root_navigation_files_updated": roots, "new_training_performed": False,
            "new_model_results_created": False, "implementation_readiness_established": False,
            "protocol_frozen": False},
        "limits": ["Review of saved source summaries does not repeat every historical raw audit.",
            "No resource benchmark, new research data generation or model training in this milestone.",
            "Five-corpus go/stop rules are descriptive, not preregistered significance tests.",
            "No novelty, major Jane Street advance or large-LM replication established."]}
    save(PACKAGE / "REVIEW.json", review)
    save(PACKAGE / "HISTORICAL_SOURCE_MANIFEST.json", {"files": inventory})
    files = [p for p in PACKAGE.rglob("*") if p.is_file()
             and p.name not in {"MANIFEST.json", "COMPLETION.json"}]
    files += [ROOT / name for name in roots]
    manifest = {"schema_version": 1, "created_utc": now,
        "scope": "Writing/planning artifacts and current root navigation; historical sources separately inventoried.",
        "self_and_completion_excluded": True,
        "files": [record(p) for p in sorted(files)]}
    save(PACKAGE / "MANIFEST.json", manifest)
    for item in manifest["files"]:
        assert digest(ROOT / item["path"]) == item["sha256"]
    save(PACKAGE / "COMPLETION.json", {"schema_version": 1,
        "status": "complete_writing_literature_and_reviewed_design",
        "completed_utc": now, "manifest": record(PACKAGE / "MANIFEST.json"),
        "review": record(PACKAGE / "REVIEW.json"),
        "package_file_count_excluding_manifest_and_completion": len(files) - len(roots),
        "historical_source_count": len(inventory), "claim_count": 13,
        "primary_literature_source_count": 10, "new_training_runs": 0,
        "new_numerical_experiments": 0, "new_model_results": 0,
        "next_protocol_status": "proposed_not_implemented_not_frozen_not_executed",
        "next": state["next"], "broader_empirical_mechanism_question_resolved": False})
    print(json.dumps({"status": "PASS", "manifest_files": len(files),
        "historical_sources": len(inventory), "local_links": len(local_links),
        "completion": f"{REL}/COMPLETION.json"}))


if __name__ == "__main__":
    main()
