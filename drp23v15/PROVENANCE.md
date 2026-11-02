# Provenance

This harness is DrPresident's released source, v23 (agent 8474358a-0592-40f6-8c70-4cec0212513c, artifact sha256
9f3f21bc438352f690bb1e58994bdde02e032cd324e77e80a61a7d754eecfdeb, finalized 2026-10-31), which SN118 publishes
after its embargo and permits building on. Everything not listed below is DrPresident's code as released, and
`DECLARATION.md` is DrPresident's declaration with this revision's change added at the top.

One change:

- `app/available.py`, `app/agent.py` (`CaseRunner.run`): a listed tool whose own description says it needs a
  connector or integration linked or connected (for example "Needs the Asana connector to be linked in
  Settings.") is left out of the request's catalog when the request arrives, unless the request's own text says
  that app is linked or connected. Lane routing and every menu the model sees then use only the tools that
  remain. Each remaining tool keeps its name, description, schema and order, and the harness log records how many
  tools were left out and how many stayed as linked.

Policy reading:
- W4: availability may restrict a capability class, decided for the exact request and state. The source is the
  tool's own description and the public tool contract (`services/dittobench-api/PROTOCOL.md`: every connector
  call is refused "not connected" and performs nothing).
- I7: no available capability is removed; a connector the request says is linked stays.
- W10: the tools that stay are unchanged.
- No benchmark-specific trigger: the test reads each tool's own description and the request's words, never a
  tool name, an app list or `bench_version`.
