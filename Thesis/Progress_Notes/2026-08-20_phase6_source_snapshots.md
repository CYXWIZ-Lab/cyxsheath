# Phase 6 Source-Snapshot Snapshot — 2026-08-20

## Completed Slice

The Redis C, fmt C++, and Astropy Python base revisions were resolved inside the same digest-pinned images that passed replay. Each probe ran with Docker networking disabled and addressed the requested commit explicitly rather than trusting the image's ambient `HEAD`. Git 2.34.1 confirmed every revision is a commit and emitted a canonical tar stream with `git archive --format=tar <base_revision>`.

| Case | Base tree | Source archive SHA-256 |
|---|---|---|
| `redis__redis-10068` | `d8da3bf4f76dcc17fa05280f74ac16b33e636f1d` | `9c944759c334437881e2e1a5f9c5d09412b86c174ce14977fd013509c59936c4` |
| `fmtlib__fmt-1683` | `8ccd12ea7ab379e67dacb1ab7b1b0dcd8ef8113a` | `bfbaf9054e2a71f10abf96aefc073c97ff407bac569eedb3674c1ad8ac7e857d` |
| `astropy__astropy-12907` | `4d9ea46e57a9bc539b358a59c526dfd933f98aba` | `02c679de5f990f4963ff09230f46bfcc9fa859fda6f9a95be6d4e1d0a76d3b38` |

Redis and fmt images had `HEAD` at the requested base. Astropy's ambient `HEAD` was `d350420dae50c80ca33b845734c31428d62af0a8`; the requested base `d16bfe05a744909de4b27f5875fe0d4ed41ce607` was nevertheless present and was the object archived. This diagnostic difference is retained in the evidence and does not substitute ambient image state for the pinned task revision.

No additional raw source archive was retained. [phase6_source_snapshots.json](../pilot_data/proposal_evidence/phase6_source_snapshots.json) contains only Git/image identities, digests, method metadata, and status.

## Evidence and Validation

- Source evidence SHA-256: `8a2bab755b4cd876d9b5498b2c2cf805fe57e1ae790bbdd7db3df72690f66814`
- Capture script SHA-256: `d16cf0c45915de9efd4c13b58514cec7bd51cb54897646859044b9f4d9d5ae72`
- Validator SHA-256: `24de92bda3a91c3aa81af73ce4911556d2f98c032e15850f18b1f1b380d3d452`
- Validation: 16/16 pilot-data tests pass; all three snapshot gates pass and proposals remain pending.

## Superseded Handoff

This snapshot originally identified provider selection and credentials as the next blocker. Subsequent live checks verified `opencode/big-pickle` through CyxCode's built-in public token. The apparent proposal latency was diagnosed as exhausted anonymous cloud quota plus a retry loop: two isolated checks returned HTTP 429 `FreeUsageLimitError`, and no patch existed. CyxCode now fails fast for that condition and disables learned state context in experiment runs. A later disclosure audit blocks Big Pickle from further benchmark submission and partially resolves research-analysis rights; see [2026-08-21_phase6_rights_and_provider_exposure.md](2026-08-21_phase6_rights_and_provider_exposure.md). `artifact.incomplete` remains valid; append-only rights decisions are events 27–28.
