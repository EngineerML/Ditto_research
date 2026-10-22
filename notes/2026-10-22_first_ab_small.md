# First paid A/B, small profile (2026-10-22)

Same dataset for both: bench 13, seed 4242, run size small (6 tool + 27 memory questions),
local rehearsal with the official scorer (`tools/practice_docker.py`), gpt-oss-20b on OpenRouter.

| image | composite | tool | memory | consistency gate | cost |
|---|---|---|---|---|---|
| `ditto-harness:hades-v6` (unchanged base, 3feb1ea) | 0.511 | 0.833 | 0.870 | 0 | $0.122 |
| `ditto-harness:dev` (meaning router + widening, 6d6ad6a) | 0.769 | 0.667 | 0.870 | 1 | $0.148 |

Reports: `practice/20261022T152419Z_ditto-harness-hades-v6_small`, `practice/20261022T153037Z_ditto-harness-dev_small`.

Reading it honestly:
- The composite gap is one case. The small profile has a single twin group; Hades got the base
  question of it wrong (trip leg total), which sets the consistency gate to 0 and multiplies the
  composite by 0.6. We got that group right. One flip either way moves the composite by about 0.3.
- Tool: we lost `multi_web_result_usage` (called `search_web` but not `read_links`, answered from
  the search summary, which is the decoy). Hades got it. Memory: same total, different misses (we
  fixed Hades's empty reply on a case-file question, lost a quantity question).
- Both lose 0.5 on each chit-chat question: the grader caps chit-chat at 0.5 for everyone
  (`grade/grade.go` `chitchatCredit`).
- Cost: +21% for us (the widened packets).

Conclusion: no signal yet beyond "nothing broke". A decision needs the medium profile
(143 questions, several twin groups), about $0.55 per image.
