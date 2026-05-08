# Foundation Docs

This folder holds durable planning rules for MCP intent hardening.

## Read Order

1. `intent-boundary-adr.md`
2. `source-of-truth-matrix.md`

## File Roles

| File | Role | Not for |
| --- | --- | --- |
| `intent-boundary-adr.md` | Defines the intent-hardening boundary, invariants, and non-goals. | Live completion status. |
| `source-of-truth-matrix.md` | Names the authoritative code, test, and doc surfaces. | Replacing the execution ledger. |

## Durable Rules

- Intent-specific tools should encode the safest narrow interpretation of common
  user phrasing.
- Generic search and list tools remain available, but they must not silently
  undermine user-specific helper semantics.
- Runtime code and tests are the only proof that a hardening behavior is live.
- Public docs and validation checklists must follow the registered surface after
  code lands.
