# Provenance

This harness is DrPresident's released source, v22 (agent eeb26552-3719-42dd-91f1-c1aab7353f33, artifact sha256
098f3e82408872cf1dd40a601cc79c42295aa4f69910e03fa6efedb21f419098, finalized 2026-10-30), which SN118 publishes
after its embargo and permits building on. Everything not listed below is DrPresident's code as released, and
`DECLARATION.md` is DrPresident's declaration with this revision's change added at the top.

One change:

- `app/available.py`, `app/agent.py` (`CaseRunner.run`): a listed tool whose own description says it needs a
  connector or integration linked or connected (for example "Needs the Asana connector to be linked in
  Settings.") is left out of the request's catalog when the request arrives. Lane routing and every menu the
  model sees then use only tools this workspace can run. Each remaining tool keeps its name, description,
  schema and order, and the harness log records how many tools were left out.

Policy reading:
- W4: availability and configuration may restrict a capability class. Nothing in a request links a connector,
  and the tool endpoint answers such a call "not connected" and performs nothing.
- I7 is not engaged: no unlinked tool is an available capability.
- W10: the tools that stay are unchanged.
- No benchmark-specific trigger: the test reads each tool's own description, never a tool name, an app list or
  `bench_version`.
