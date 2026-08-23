# Integrations

CyxSheath keeps external tools outside its dependency-free decision core. The first concrete generator adapter targets [CyxCode](https://github.com/code3hr/cyxcode), while the Python boundary lives in `sheath/src/sheath/cyxcode.py`.

## CyxCode Checkout

The local `integrations/cyxcode/` directory is intentionally ignored because it is an independent Git worktree with its own history, contribution rules, dependencies, and experimental bridge changes. Do not commit it as an embedded repository or copy its generated dependency tree into CyxSheath.

The current public checkpoint supports the deterministic Python adapter tests without that checkout. Rebuilding or running the pinned live bridge requires the separately maintained experimental CyxCode worktree and is not yet a public reproduction path. The integration will become public only through a reviewed CyxCode commit or release with an immutable revision and documented setup.

See [the adapter usage guide](../usage/CyxCode_Adapter.md) and [publication boundary](../docs/Publication_Boundary.md) for the supported paths and limitations.
