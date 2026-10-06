<a name="stage-11-v0128-one-authorized-preparation180-second-cap"></a>

# Stage 11 v0128: one authorized preparation, 180-second cap

User approval 2026-10-01 11:08:19 UTC permits this cap revision and exactly one
fresh preparation after exact-source readiness and focused guard checks pass.
Run ID: rule-tying-v0128-20261001-01. Never retry/resume a failed directory.
Read PREPARATION_INTEGRATION.md and accepted INDEPENDENT_REVIEW.json first.
CAP_STATIC_REVIEW alone is not preparation readiness.

Active preparation limit is 180 seconds from before Python heavy imports,
checked with both UTC and monotonic clocks. The direct-terminal command also
uses a 180-second Linux timeout with interrupt then bounded owned cleanup.
Native WSL startup precedes that preparation clock; record it separately.
Inherited config.PREP_SECONDS300 is not an active launcher allowance.
The new cap is a user-selected engineering budget, not a completion guarantee.

Sources are exactly the top-level .py/.md catalog. Commands/JSON evidence are
separate bindings. Diagnostic cap fixtures are not research inputs; no model
execution in those tests. Historic documents and check runners are provenance,
not permission to reset budgets or rerun old experiments.

Training remains conditional on complete successful preparation, independent
freeze acceptance and the existing explicit authorization for one 90-minute,
4 GiB run. Do not launch training automatically from preparation commands.
Scientific design, start-free 6 GiB/free-reserve 2 GiB and all integrity checks remain.
