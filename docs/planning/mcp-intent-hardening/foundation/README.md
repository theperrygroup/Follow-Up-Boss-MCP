# Foundation Docs

This folder holds durable planning rules for MCP intent hardening.

## Read Order

1. `intent-boundary-adr.md`
2. `battle-test-verification-adr.md`
3. `source-of-truth-matrix.md`

## File Roles

| File | Role | Not for |
| --- | --- | --- |
| `intent-boundary-adr.md` | Defines the intent-hardening boundary, invariants, and non-goals. | Live completion status. |
| `battle-test-verification-adr.md` | Defines how vague chatbot prompts must be verified through MCP tool routing and direct API oracle checks. | Replacing the focused battle-test plan or run evidence. |
| `source-of-truth-matrix.md` | Names the authoritative code, test, and doc surfaces. | Replacing the execution ledger. |

## Durable Rules

- Intent-specific tools should encode the safest narrow interpretation of common
  user phrasing.
- Generic search and list tools remain available, but they must not silently
  undermine user-specific helper semantics.
- Runtime code and tests are the only proof that a hardening behavior is live.
- Public docs and validation checklists must follow the registered surface after
  code lands.
- Battle-test prompts pass only when observed MCP routing and direct API truth
  agree with the scenario contract.
