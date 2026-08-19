# HeatViz Agent Rulebook (agents.md)

You are the implementation agent for HeatViz. SPEC.md is the contract. This file is the rulebook.

## Startup Protocol (every session)

1. Read SPEC.md fully.
2. Read memory.md. If missing, create it from the template below.
3. Verify the Input Data Contract (SPEC Section 3). If any file is missing or misaligned, STOP and report. Do not improvise.

## Memory Protocol

- memory.md is append-only state. Never delete entries.
- Read it before any action; write to it after every stage.
- Template:

```text
# HeatViz Memory
## Status: <current stage>
## Completed Stages
- [ ] 01 blocks  [ ] 02 m1-train  [ ] 03 m1-infer  [ ] 04 graph
- [ ] 05 m2-train  [ ] 06 m2-infer  [ ] 07 score-export  [ ] 08 api  [ ] 09 web
## Metrics Log
(stage, gate, value, pass/fail, timestamp)
## Artifacts
(file paths produced)
## Blockers
(none / description)
```

## Execution Rules

1. Run stages 01-07 in order, then api, then web. One stage per step.
2. Constants, weights, seeds, architectures in SPEC are immutable.
3. Every gate (G1-G7) must pass before continuing. On failure: log to memory.md, exit, report the failing metric. No fallbacks, no retries with changed parameters.
4. No scope creep: implement only what SPEC defines. No extra features, no extra models, no extra data.
5. All randomness uses SEED=42.
6. Log every metric (R2, MAE, correlation, std, block counts) to memory.md immediately after computation.

## Reporting Style

After each stage report exactly:
`STAGE <n> <name>: PASS/FAIL | <key metrics> | artifact: <path>`

## Definition of Done

All 9 stages complete, all gates logged as PASS in memory.md,
`data/output/vulnerability_blocks.geojson` exists in EPSG:4326,
and `uvicorn api.main:app` serves the working map at `/`.
