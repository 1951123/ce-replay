# PVLDB Volume 20 Final Submission Audit

Verified on 2026-09-22 against the [VLDB 2027 Formatting Guidelines](https://www.vldb.org/2027/formatting-guidelines.html), [PVLDB Volume 20 Submission Guidelines](https://www.vldb.org/2027/submission-guidelines.html), [Research Track call](https://www.vldb.org/2027/call-for-research-track.html), and official [VLDB template repository](https://github.com/vldbproceedings/VLDB-Template).

## Outcome

The technical package passes manuscript, template, page-limit, PDF, figure, table, citation-integrity, public-repository, frozen-artifact, and clean-build checks. It is not ready for upload because the single-blind manuscript still contains explicit author placeholders. No identity was inferred or invented.

Required author fields are: full names in final order; institution; city; state/region where applicable; country; email; corresponding-author choice if applicable; and any intentionally supplied ORCID. CMT-only declarations and timing actions are listed in `docs/pvldb20-cmt-human-action-checklist-v0.md`.

## Venue and template

Regular Research Papers allow 12 body pages excluding references; appendices and acknowledgements count toward the body limit. This paper has approximately 11.2 body pages, references start on page 12, and it has no appendix or acknowledgements. It is therefore within the page limit.

The official template HEAD is `39c95f5c6fcbe652a83be24e4eff8f2134cd3fbc` dated 2026-07-13. Local `acmart.cls`, `pvldb.sty`, and `ACM-Reference-Format.bst` are byte-identical to that revision. The document class, `pvldb` package, `\vldbtopmatter`, copyright/reference-format block, and artifact-availability block are present. DOI/page placeholders are submission-stage placeholders from the official sample. The current official sample contains no CCS or keywords block.

## PDF and visual inspection

The clean build produces 12 US-Letter pages. Every page was inspected, including dense pages 7--9. There is no clipping, overlap, blank page, malformed equation, unreadable figure/table, or ownership ambiguity. All reported fonts are embedded and the Type 3 count is zero. Figures remain vector. Copy/paste extraction succeeds. There are no overfull hboxes, undefined references, undefined citations, duplicate labels, or missing figures. The established 1.252pt page-output overfull vbox is visually harmless.

## Figures, tables, and bibliography

F1--F4 and T1--T5 retain their numbering, captions, values, units, and scientific roles. DMV raw zero-truth qualification remains visible. All 15 bibliography entries are cited, every citation resolves internally, there are no duplicate or unused keys, and the citation set is unchanged. Authoritative metadata corrections add pages 516--525 to the JITS ICDE 2007 entry and correct the DOI for *Constrained Physical Design Tuning* to `10.14778/1453856.1453863`. The current Amazon Science record for the 2026 Redshift paper does not yet provide final PVLDB issue/pages/DOI metadata; this is documented rather than guessed.

## Artifact and repository

The GitHub repository is public, its default branch is `main`, and `research-freeze-v0` still peels to `22cf494f954cffff86080236473ca847064dca74`. Frozen results are unchanged. The repository provides code, native-extension source, experiment scripts, frozen outputs, vector-figure generation, paper build instructions, and a claim-to-evidence reproduction index. Census/DMV data and PostgreSQL itself are external inputs and are not redistributed. Full re-execution is conditional on obtaining those inputs and on experiment-specific resources; frozen evidence inspection is immediately available.

Public-facing instructions are repository-relative. Absolute paths remain only in historical scripts/results as provenance or overridable defaults. A heuristic secret scan found no committed credentials or private keys. The worktree is approximately 93 MiB including ignored build products; the Git database is 18.28 MiB, the largest tracked file is about 12.6 MiB, no tracked file exceeds 100 MiB, and Git LFS is unused.

## Originality and human declarations

No repository document explicitly identifies a prior version, workshop paper, concurrent submission, technical report, or preprint. This cannot establish originality from private author history. Human authors must declare any such work, all conflicts, the qualified reviewer nominee, submission-cap status, and related concurrent submissions in CMT.

## Gate

`PACKAGE READY EXCEPT AUTHOR/CMT METADATA`
