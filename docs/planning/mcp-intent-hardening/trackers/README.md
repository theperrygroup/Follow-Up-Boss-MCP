# Tracker Docs

This folder holds current readiness scoreboards for MCP intent hardening.

## Read Order

1. `readiness-overview.md`
2. `intent-routing-readiness.md`
3. `safety-validation-readiness.md`
4. `battle-test-readiness.md`

## Grade Rules

| Status | Meaning |
| --- | --- |
| `Complete` | The tracked planning or prerequisite slice is checked in. It does not imply all runtime behavior is live. |
| `In progress` | Some proof exists, but one or more required code, test, doc, or validation items remain open. |
| `Planned` | The work is defined but no implementation proof has landed. |
| `Blocked` | The next step is known but cannot honestly proceed yet. |

## Update Rules

- Update the focused tracker first when one risk area changes.
- Update `readiness-overview.md` after focused tracker changes.
- Update `execution/execution-plan.md` after the readiness state changes.
- Do not mark live-account validation complete until the offline contract is
  already checked in.
- Do not mark battle-test readiness complete until prompt transcripts, selected
  MCP tool paths, direct API oracles, and cleanup evidence are recorded.
