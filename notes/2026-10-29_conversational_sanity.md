# Conversational sanity for horizon v5 (2026-10-29)

Prompted by Hades v18's third scored run (0.7348): one declarative-acknowledgement miss and one
behavior miss ("abstained on an answerable question") put the sanity metric at 0.763 and the factor
at 0.822. The v14 factor is 0.25 + 0.75 × metric, where the metric is the geometric mean of the
chitchat, declarative-ack and behavior slice pass rates (scorer.go:694, v7.go:278). Each slice has
3 cases, so one miss costs ×0.905 and a miss in each of two slices costs ×0.822.

## Evidence

- Platform, 78 scored runs of 26 top agents (case_results): chitchat 0/234 missed, behavior 1/234,
  declarative-ack 4/234. Agents built on dan0l v28 (dan0l v28-v30, mvkdata v3, hfull-h3 v4,
  crown-v194, Hades v16/v17, horizon v5): no misses except Hades v18's two. horizon v5: 18/18.
- Local v5 full run (seed 7429735794480221645): 9/9. All earlier local designs are a different code base.
- Routing (practice/gates/conv_routing_check.py): all 12 statement and 12 question templates
  of the v14 grammar (datagen gen/v13_integrity.go), each with 3-4 values, switch on
  own_setting_stated / own_setting_asked and the reply-only path. Statements land in four lanes and
  questions in three; agent.py moves records-lane ones to action:guided because a kind is set.
- Packet (practice/gates/conv_packet_check.py): on 40 fresh seeds, the preference record is in the
  action-lane packet for 120/120 behavior questions. It is first in 40 and fourth or later in 80,
  in packets of 10+ records, so the model picks it out from other records.

## Reading

Routing and retrieval are deterministic and fully covered. What remains is the model sampling:
a statement reply that does not repeat the value, or a question reply that abstains or takes the
wrong value. In the field that happens in about 1% of cases, so about 6% of runs take ×0.905.
Expected cost about -0.5% per run, against about -1% from consistency splits for v5. A host-side
check that compares or rewrites the reply would be I3/I4 (precedent #3270), so the only lever is
prompt wording, and with no observed v5 failure a change would be fitting noise. No change now;
consistency stays first.

Latent: one of three local acknowledgement replies said 'Your Ditto accent is set to "tan green".'
without making a call. It passes the grader today. The claim-provenance and catalog gates that
count uncorroborated claims run in shadow only.
