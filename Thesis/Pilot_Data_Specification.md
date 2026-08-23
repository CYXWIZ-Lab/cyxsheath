# Pilot Data Specification

## 1. Status and Scope

Version `1.0.0`, frozen 2026-08-20, governs Phase 6 seed-corpus admission and annotation. The seed validates replay, provenance, the manifest, and the supervision ontology. It is not a training corpus, benchmark result, or representative estimate of real-world defect prevalence.

The target is 100–300 **adjudicated cases**. A case is one immutable task, repository revision, generator proposal, observable evidence bundle, and outcome. Retries and variants from the same task remain separate records but share one lineage group.

## 2. Required Artifacts

Every admitted case must resolve to content-addressed:

1. task record and immutable source snapshot;
2. replay environment image;
3. proposal response and canonical patch;
4. visible and blinded verification evidence;
5. two independent annotations and one adjudication conforming to `schemas/annotation_record.schema.json`; and
6. one manifest entry conforming to `schemas/dataset_manifest.schema.json`.

The manifest stores references and digests, not duplicate source trees. Author names, email addresses, account identifiers, private chain-of-thought, credentials, and unrelated repository history are not dataset fields.

## 3. Source and Coverage Rules

Permitted sources are revision-pinned benchmark tasks, issue/patch pairs, CI or analyzer repairs, and manually authored defensive fixtures. A public URL alone does not establish permission.

The admitted seed must satisfy all of the following:

- at least 100 and at most 300 cases;
- at least 20 cases each for C, C++, and Python;
- at least five repository families represented per language;
- no repository family contributes more than 10% of admitted cases;
- at least 25% are adjudicated `no_violation` cases;
- each category promoted beyond the seed has at least 20 adjudicated positives;
- manually authored or model-generated fixtures contribute at most 20% and are reported separately.

These are schema/coverage constraints, not population weights. Outcome studies must sample separately.

## 4. Admission State Machine

Each candidate receives exactly one state:

- `admitted`: every hard gate passed;
- `quarantined`: a potentially resolvable fact is missing or disputed;
- `rejected`: a hard exclusion applies.

Admission requires an exact revision and snapshot digest, known source date, replay without unapproved network services, bounded verification, license evidence, `research_analysis=allowed`, a privacy/secret review, defensive safety scope, and sufficient outcome evidence. Quarantined and rejected cases never contribute to quotas or splits.

Stable reason codes are used in the append-only rejection log:

| Disposition | Reason codes |
|---|---|
| Reject | `license.denied`, `privacy.personal_data`, `secret.detected`, `safety.offensive`, `provenance.missing`, `revision.unpinned`, `snapshot.unreplayable`, `evidence.missing`, `lineage.duplicate`, `scope.unsupported`, `artifact.malformed` |
| Quarantine | `license.unclear`, `privacy.review_required`, `replay.transient`, `label.conflict`, `lineage.uncertain`, `contamination.uncertain`, `artifact.incomplete` |

Original decisions are never overwritten. Corrections append a superseding review event and dataset changelog entry.

## 5. Licensing and Permitted Use

Record the license as an SPDX expression, the SPDX License List version used to resolve it, and evidence from the pinned revision. SPDX provides standardized identifiers and expressions; the OSI registry identifies licenses approved under the Open Source Definition. Neither fact alone is treated here as a project-specific decision about dataset redistribution or model training.

Each case separately records `research_analysis`, `redistribute_metadata`, `redistribute_derived_labels`, `redistribute_source`, and `model_training` as `allowed`, `prohibited`, or `unknown`. Admission requires only research analysis. An `unknown` or disputed research right causes quarantine; source redistribution and model training require their own later `allowed` decision. Attribution and notice obligations remain attached to exported artifacts.

Authoritative terminology: [SPDX Specification 3.0.1](https://spdx.github.io/spdx-spec/v3.0.1/), [SPDX License List](https://spdx.org/licenses/), and [OSI Approved Licenses](https://opensource.org/licenses).

## 6. Privacy, Secrets, and Safety

- Collect only task, code, patch, and engineering evidence necessary for replay.
- Strip author identity and unrelated discussion before annotation.
- Scan the snapshot, task, patch, logs, and environment for credentials and personal data; manual review follows any match.
- Never store live secrets. Synthetic fixture credentials must be unmistakably nonfunctional.
- Admit security cases only as defensive repair tasks in isolated environments. Exclude live targets, operational credentials, weaponized payloads, and instructions whose release creates material misuse risk.
- Retain restricted artifacts only when permitted and necessary; public releases fall back to metadata and derived labels when source redistribution is not allowed.

## 7. Lineage, Duplication, and Contamination

`repository_family` identifies the canonical upstream project; forks inherit that family. `lineage_group` joins the original issue, equivalent task statements, reference patch, retries, generated variants, and backports.

Compute and retain:

- raw SHA-256 digests for task, snapshot, patch, tests, and evidence;
- a normalized task digest after UTF-8 NFC normalization, LF conversion, trailing-space removal, and outer-whitespace trimming;
- a patch fingerprint from sorted paths plus before/after blob digests;
- token five-gram Jaccard similarity for task text.

Exact digest matches share a duplicate group. Task pairs with Jaccard similarity at least `0.85`, or patches sharing the same changed paths and before/after blob digests, require blinded lineage review. All confirmed or unresolved near duplicates remain in one split.

Record benchmark membership, publication date, known prior use, and generator exposure as `known`, `none`, or `unknown`. Reference solutions and blinded checks never enter generator context. Every seed case is permanently excluded from the confirmatory test set and from calibration of confirmatory thresholds.

## 8. Annotation and Adjudication

Two trained reviewers independently label every admitted seed case while blinded to condition, generator identity, the other annotation, and study hypotheses. They receive the task contract, proposal, patch, and recomputed evidence required for the judgment.

For each finding they record:

1. directly observable fact and artifact/location reference;
2. applicable constraint, criterion, or check ID;
3. one category and severity;
4. evidence that could refute the finding; and
5. proportionate action: `accept`, `revise`, `block`, or `escalate`.

`no_violation` is mutually exclusive with positive categories. Style preference without a contract, outcome, safety, or maintainability consequence is not a finding. Generated labels may suggest candidates but never replace either reviewer.

A third reviewer adjudicates every category, severity, or action disagreement and audits a fixed 10% random sample of agreements. Original labels, the adjudicated label, rationale, reviewer pseudonyms, timestamps, guide version, and conflicts of interest remain append-only.

## 9. Agreement Gates

These are prespecified engineering gates, not claims of universal statistical standards:

- each retained binary category: raw agreement at least `0.80` and Cohen's kappa at least `0.60`;
- ordinal severity: exact agreement at least `0.75` and weighted kappa at least `0.60`;
- action/verdict: raw agreement at least `0.80` and kappa at least `0.60`;
- all blocking/escalation disagreements receive explicit adjudication.

Report prevalence and positive/negative agreement beside kappa. If a gate fails, revise the guide once and blindly relabel at least 20 affected cases. A second failure merges, demotes to a secondary tag, or removes the category; thresholds are not lowered after results are seen.

## 10. Split Contract

The Phase-6 seed has split `seed` and is development-only. It may inform schema and guide revisions but can never enter confirmatory testing.

If a learned residual task is later admitted, split only after deduplication and adjudication:

1. group all repository forks, issue/patch lineages, retries, and near duplicates;
2. reserve whole newest repository families until approximately 20% of cases form the held-out test set;
3. from remaining families, reserve the newest lineage groups until approximately 20% form validation/calibration;
4. assign the remaining approximately 60% to training;
5. keep challenge cases separate from these ratios.

Ordering uses source publication time and stable ID as the tie-breaker, never labels or model performance. The manifest and split algorithm revision are checksummed before training.

## 11. Replay and Phase Gate

Every admitted case must replay once from a clean snapshot. A deterministic 10% sample, selected by hashing `case_id` with the frozen manifest ID, is replayed independently by a second operator or environment. Any source, patch, evidence, or outcome mismatch quarantines the case and opens a deviation.

Phase 6 completes only when:

- the specification and schemas are frozen and checksummed;
- 100–300 admitted cases satisfy coverage limits;
- every case is content-addressed, replayable, double-labeled, and adjudicated;
- rejection, quarantine, lineage, split, and contamination logs resolve from the manifest;
- agreement gates pass or unreliable categories are removed; and
- a release matrix states exactly which artifacts may be analyzed, redistributed, or used for training.

Until then, no custom critic training begins.
