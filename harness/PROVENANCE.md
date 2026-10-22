# Provenance

This harness starts from a released SN118 king artifact, used under the subnet's source-release
policy ("building on a released miner agent is permitted", ditto-subnet
`apps/platform/docs/anti-copy-reference.md`).

- base: agent `e6638d76-f48c-41c5-9752-d1ddfa9d7355` (Hades v6), bench v13
- artifact sha256: `2c42cb08fd2ad1779d0115f60c8e1dd67c4682b2556592ad69ce1acc701b733b`
- released through `GET /api/v1/public/agent/{agent_id}/artifact`, downloaded 2026-10-22

The commit that adds this folder is the unmodified base. Every later commit is our own work.
The earlier blinkrazor v3 base stays on branch `harness/blinkrazor-v3-base`.
