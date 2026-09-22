# Repository Freeze Report v0

## Outcome

The repository passed content, large-file, secret, staging, and provenance audits and was prepared as the first authoritative local Git snapshot. No PostgreSQL process, database, `ANALYZE`, optimizer, or experiment was run.

## 1. Pre-existing Git state

An empty `.git/` directory existed before this task, but Git reported that the directory was not a repository. It contained no recognized history, branch, tag, or remote. The directory was initialized as a new repository without replacing legitimate history.

## 2. Branch

The authoritative branch is `main`.

## 3. Commit

The authoritative commit is the commit containing this report and tagged `research-freeze-v0`. Resolve its immutable hash with:

```text
git rev-parse research-freeze-v0^{}
```

The exact hash is also reported in the task completion response and by the final integrity check. Embedding a commit's own hash in a file contained by that same commit is self-referential and would change the hash.

Commit message:

```text
research: freeze experiments and paper technical baseline
```

## 4. Tag

Annotated tag: `research-freeze-v0`.

Tag message:

```text
Experimental phase complete; technical core and evaluation frozen for paper drafting.
```

## 5. Tracked content

The pre-report stage audit contained 189 files. Adding this report produces the final authoritative tracked set reported by the post-commit integrity check.

Pre-report tracked size: 71,968,155 bytes, approximately 68.634 MiB.

The repository content is classified as:

- **SOURCE:** `tools/`, `tests/`, and source files under `pgext/ce_replay_native/`.
- **PAPER:** paper architecture, Figure 1 specification, and Sections 3–8 under `docs/`.
- **EVIDENCE:** frozen JSON, Markdown, CSV, and compressed CSV artifacts under `results/`.
- **BENCHMARK / CONFIGURATION:** workload references and experiment configuration embedded in scripts/artifacts; the large raw benchmark datasets are external and are not vendored.
- **GENERATED / REPRODUCIBLE:** Python caches, test caches, and compiled native-extension objects; ignored.
- **LOCAL / LARGE / UNSAFE:** local PostgreSQL build/data trees, dumps, logs, credentials, and machine-specific agent state; absent or ignored.

## 6. Largest tracked files

| Bytes | File | Decision |
|---:|---|---|
| 12,642,122 | `results/census_ce_replay_optimize_v4.json` | TRACK — primary compositional optimization evidence |
| 12,038,834 | `results/census_ce_replay_optimize_v1_full_pairs.json` | TRACK — full candidate-pair optimization evidence |
| 10,073,655 | `results/census_generalization_mechanism_analysis_v0.json` | TRACK — frozen research archive/evidence, although outside the core paper |
| 7,839,743 | `results/census_structural_distance_generalization_v0.json` | TRACK — frozen archive evidence |
| 7,323,667 | `results/census_semantic_move_pruning_v0_moves.csv.gz` | TRACK — compressed move-level reproducibility evidence |
| 5,661,963 | `results/census_ce_replay_optimize_v1_scale1000.json` | TRACK — scale experiment evidence |

No file exceeds 50 MB or GitHub's normal 100 MB hard limit. Git LFS was not enabled.

## 7. Ignored categories

The `.gitignore` excludes:

- Python bytecode and tool/test caches;
- virtual environments;
- editor and OS metadata;
- local `.agents/` and `.codex/` state;
- compiled PostgreSQL extension objects such as `.o`, `.so`, and `.bc`;
- PostgreSQL build/data trees and process state;
- logs, dumps, backups, scratch, build, and distribution output;
- `.env`, private-key, and certificate-style credential files;
- reproducible rendered paper/build artifacts.

It does not broadly ignore `docs/`, `results/`, `tools/`, required CSV evidence, or experiment JSON/Markdown.

## 8. Large-file decisions

All files over 10 MB are important JSON evidence and are tracked. The compressed move-level CSV remains tracked because it is reasonably sized and supports reproducibility. No file was classified as a Git LFS candidate, manual-review blocker, or database binary. PostgreSQL source/build trees and raw database state are not present inside the repository.

## 9. Secret audit

High-confidence scans found no private keys, GitHub tokens, cloud keys, OpenAI-style keys, Slack tokens, credential-bearing connection URIs, `.env` files, or local key/certificate files.

Five early scripts contained the standard local PostgreSQL password literal as a CLI default. The defaults were changed to `None`; explicit `--password` remains supported. This was source hygiene only and did not modify results or claims. A post-change scan found no embedded non-empty password defaults.

## 10. Absolute-path audit

Absolute local path occurrences were classified as follows:

- **Historical provenance:** four result/report artifacts record original execution locations and were not rewritten.
- **Active source/config dependency:** eight scripts contain original-machine default paths for external Census/DMV inputs, PostgreSQL source, or audit roots. These paths are CLI-overridable and are documented in the README/reproducibility index. They remain a portability limitation rather than a secret.
- **Paper-facing accidental path:** none found in the frozen paper drafts.

Scientific result artifacts were not cosmetically rewritten.

## 11. README

Created `README.md` with the problem statement, CE-Replay definition, PostgreSQL semantic boundary, repository layout, workloads, reproduction entry points, research/paper status, optimization guarantee, and provenance limitation.

## 12. Reproducibility index

Created `docs/reproducibility-index-v0.md`, mapping the core Census/DMV semantic, non-monotonicity, maintenance, optimization, deployment, robustness, provenance, convergence, Technical Core, and Evaluation stages to their primary scripts and artifacts.

## 13. Scientific-artifact modifications

No experiment result, evidence JSON/CSV/Markdown, numerical measurement, or paper claim was modified for the repository freeze.

Repository-hygiene changes were limited to:

- adding `.gitignore`;
- adding `README.md`;
- adding the reproducibility index and this report; and
- removing a standard local password default from five source scripts.

## 14. Remote and push status

No Git remote is configured. No GitHub URL was invented, and nothing was pushed. To synchronize, the user must create or select a GitHub repository, add its verified URL as a remote, and explicitly push `main` plus the annotated tag.

## 15. Blockers

No local freeze blocker remains. GitHub synchronization is pending only on user selection/configuration of a legitimate remote.

REPOSITORY FROZEN — READY FOR GITHUB SYNC
