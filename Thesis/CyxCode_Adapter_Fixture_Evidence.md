# CyxCode Adapter Fixture Evidence

## Scope

This record covers the Phase-5 execution boundary completed on 2026-08-20. It is integration evidence, not evidence that Sheath improves coding-agent outcomes. The protected upstream checkout was not used as a writable workspace.

## Exercised Path

The adapter launches an absolute command without a shell, sends the deterministic prompt through standard input, and invokes:

```text
cyxcode run --dir <snapshot> --format json --model <provider/model> --title <run-id>
cyxcode export <explicit-session-id>
```

Each run receives fresh XDG/CyxCode state directories, an explicit configuration, disabled update/model-fetch/plugin variability, a wall-time limit, and an aggregate output limit. State removal occurs in `finally` after export or failure.

Three fixture levels passed:

- A subprocess fixture validated successful mutation of only a disposable snapshot, zero-exit error-event mapping, mixed-session rejection, export-session mismatch, malformed NDJSON, timeout, output limiting, and state cleanup.
- The real CyxCode TypeScript entrypoint ran against a deterministic loopback OpenAI-compatible stream. Its NDJSON session ID matched explicit export, the terminal assistant message had no error, prompt bytes reached the provider, isolated state was removed, and the protected source file remained unchanged.
- `SubprocessCyxCodeExecutor` drove the TypeScript bridge and immutable Linux image from the Python coordinator. The image reverified `/usr/local/bin/cyxcode` before each invocation, completed `run` and explicit-ID `export`, passed through the trusted Docker patch extractor, and produced an accepted schema-v1.7 record. Docker-side cleanup removed adapter-owned state and metadata before Windows snapshot disposal.

The Python boundary now accepts the versioned canonical execution envelope and composes it with the existing trusted patch extractor. Before extraction it restores the exact top-level `.cyxcode` and `.opencode` trees from the immutable snapshot source. A successful fixture produces a validated, content-derived `GeneratorProposal` and schema-v1.7 accepted record; a failed execution produces no proposal but preserves its response artifact in the failed record. Two independent success runs produced identical proposal IDs and patch bytes.

The loopback test uses an explicit fixture-only CyxWatch policy. It does not weaken production policy.

## Validation Results

```text
bun typecheck
PASS

bun test test/cyxcode-adapter.test.ts test/cyxcode-adapter-live.test.ts
9 pass, 0 fail, 69 assertions

Python 3.12 Sheath suite: 138 pass
Python 3.14 Sheath suite: 138 pass

Draft 2020-12 schema validation with date-time formats enabled:
fixture success/failure records valid; pinned CyxCode success record valid
```

The Sheath rerun exposed and verified two narrow corrections: exceptions raised inside `GeneratorAdapter.propose` now remain typed as generator failures, and non-failure export checks the required `EXPORTED` state before secondary history validation.

## Content Identities

- `src/cmd.ts`: `5BD47C90C3F9F7FEAFD5E5EF5B43AB53AF1003F34273CB0FA1010C72DFE8ADDC`
- `src/runner.ts`: `A2CD66C8C8CB012297996E4BA006672615E35536BB7BC06F469729664A79F711`
- `src/sheath-bridge.ts`: `9337D0527CD9727EB933EEF0EBD9BD5733AC0F7948FA6A66DBE2486302E8A329`
- `src/sheath-docker.ts`: `B6484D0282155F41202011D3093437242B76BCBF11D90EF537C582AA5248A795`
- adapter unit test: `95F387BFFF068CF83934DD12B11284219316BA34F9810CB2955004DD6DCED811`
- live test: `998668C55E181ED0DA2B450FEF5D36B7D6501C5CBE7746E98A6C49A8C43C9AEF`
- subprocess fixture: `93AD8DB4A82CC72666AA235933EE12EF167A57FE4E482EED5E336BEC518161FE`
- Python adapter: `3D2E233BCBDF3AEFE54B86B7F6E4A2F326C319CA32AA27EE55724348525740FF`
- Python adapter test: `730D897B07337A316A5E4F8B50A06D2C80410AFC0C70B97E5A425E00FC29ADAA`
- pinned smoke script: `F21225D7DBD6BECCD6473380C6EFAB9E00BDFD9230D25EF1442F0DB7A817B6E5`

## Pinned Smoke Evidence

- CyxCode image: `sha256:8a797f1541bc715f362d0e42981c12d57aa599ee4b6ba38ea5e8332a4c06539a`
- executable: `sha256:e9e88c1635c5c357395fd2e46c211c20c5c1b99d11d81ce83ea67fce580234b0`
- patch image: `python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65`
- decision: `accept`
- run-record digest: `sha256:6696088aea38a8b7c3bdab05129c8375aa776c473483a4b76eba80e131184d0f`
- response artifact: `artifact:response:578b42ee73c8c4424c34ee3156247cac386c16dc8b76b434e33e380cf06a0e6c`
- manifest artifact: `artifact:manifest:2b3f1236e10cbb1c3cc133a65d86fa0de321e61e7ec89a940f5c6445995f8fac`

The Phase-5 exit gate is complete. External-provider behavior, cancellation/process-tree guarantees, token/cost capture, real-model variability, and benchmark effectiveness remain unevidenced and must not be inferred from this deterministic infrastructure smoke.
