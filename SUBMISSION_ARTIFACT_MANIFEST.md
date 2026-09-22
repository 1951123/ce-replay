# CE-Replay Submission Artifact Manifest

## Stable identity

- Public repository: <https://github.com/1951123/ce-replay>
- Immutable research tag: `research-freeze-v0`
- Frozen research commit: `22cf494f954cffff86080236473ca847064dca74`
- Submission-package paper baseline: `4d5a94d62c6004cc226934690280308ab03942b9`
- Reproduction entrypoint: [`docs/reproducibility-index-v0.md`](docs/reproducibility-index-v0.md)

The research tag identifies the frozen experimental evidence. Later `main` commits contain paper construction, typesetting, and submission-compliance artifacts; they do not rewrite the research tag.

## Repository map

- `tools/`: semantic probes, replay evaluators, optimizers, maintenance calibration, deployment, and audits.
- `pgext/ce_replay_native/`: PostgreSQL native-validation extension source.
- `tests/`: lightweight analysis tests.
- `results/`: frozen experiment outputs and paper/compliance audits.
- `docs/`: semantic documentation, evidence indexes, manuscript versions, and reviews.
- `paper/pvldb2027/`: official PVLDB Volume 20 template, generated LaTeX, bibliography, vector figures, and build instructions.
- `paper/pvldb2027/figures/src/build_figures.py`: deterministic figure generator.

## Claims, workloads, and evidence

The artifact supports the bounded CE-Replay claims for PostgreSQL 16.14 base-relation conjunctive restrictions described in the paper. Census supplies the large sparse candidate-incidence regime; DMV supplies the dense, high-reuse constant-`IN` regime. The reproducibility index maps semantic validation, non-monotonicity, maintenance calibration, optimization, incremental evaluation, deployment, and provenance audits to their scripts and frozen outputs.

Frozen outputs can be inspected without a running DBMS. Re-executing native and deployment experiments requires PostgreSQL 16.14, the extension toolchain, and separately obtained Census/DMV benchmark inputs. The repository does not redistribute those external datasets or a PostgreSQL source tree. Historical result artifacts may retain original absolute paths as provenance; public instructions use repository-relative paths.

## Figure and paper reproduction

Figure rebuilding is documented in [`paper/pvldb2027/README.md`](paper/pvldb2027/README.md). The four figures are generated from frozen repository artifacts and are stored as PDF and SVG. The same README provides the exact `pdflatex`/BibTeX paper build sequence and records the pinned official template hashes.

## Known limitations

- The validated semantics are bounded to the documented PostgreSQL 16.14 fragment; this is not full planner or join replay.
- Candidate-payload acquisition is an offline external boundary.
- Workload-scale optima are neighborhood-local except for documented small or restricted exhaustive audits.
- Maintenance coefficients are environment-specific first-order proxies.
- Frozen and fresh payloads are distinct realizations; DMV lacks sufficient frozen provenance for a paired per-query drift reconstruction.
- External benchmark inputs and PostgreSQL must be obtained separately; resource needs depend on the selected experiment and environment.

## Submission state

The technical package has been audited for PVLDB Volume 20. The candidate PDF is intentionally not labeled upload-ready until human authors supply names, order, affiliations, locations, and email addresses and complete the CMT declarations listed in `docs/pvldb20-cmt-human-action-checklist-v0.md`.
