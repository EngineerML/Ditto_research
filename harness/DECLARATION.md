# Pipeline declaration

The served path, the host steps that touch scorer-visible fields, and where they are. No model weights or opaque
components; the only model is the hosted one, called over HTTP through the request's inference endpoint.

## 1. Served path

- `Dockerfile` starts `app.main:app`. `POST /run` (`app/main.py:60`) calls `CaseRunner.run` (`app/engine/agent.py:102`),
  with a case deadline of 285 s (`app/config.py:145`).
- Without a model, the host ranks the requesting user's stored conversations and picks a lane from the request's words
  and its catalog (`app/engine/agent.py:126-139`). The lane chooses the prompt and the record packet; every deciding
  turn carries the whole supplied catalog.
- Records lane: the short path for programs and topics (`app/engine/agent.py:79-100`, `app/engine/short.py`), or the
  records engine (`app/engine/agent.py:149-150`, `app/engine/records.py`). Action lane: `app/engine/agent.py:156-157`,
  `app/engine/action.py`.
- Action lane decision step (`app/engine/action.py:216-235`, called at `app/engine/action.py:252`; switch
  `HARNESS_PLAN_FIRST`, on): before its first turn, the deciding model is shown its own conversation (system prompt,
  records, request) followed by one more user message listing every tool of the request's catalog by name and
  description and asking which tool its first call should use, or NONE (`PLAN_QUESTION`, `app/engine/action.py:137`).
  This call offers no tools. When the reply has text and was not cut at the length limit, the question, the reply as
  written and `PLAN_ACT` ("Now respond to the user's message as you decided: make that call, or reply without one.",
  `app/engine/action.py:138`) are added to the conversation, and the lane's turns run as before with the whole catalog.
  The host does not read, parse or act on the reply; every call that follows is the model's own native tool call, and
  the model may make a different call or none.
- Program short path, shared draft (`app/engine/short.py:245-253`; setting `short_shared_draft`, on): after the
  order reading, one advisory model call writes a draft answer from the program's grouped notes and the complete
  request, with the same system prompt and the same input as the deciding call. Requests of this run over the same
  notes whose asking sentence (`asked_part`) is the same are rewordings of one question: the first of them writes the
  draft with its own complete message and the others reuse it, as rewordings already share one order reading
  (`app/engine/short.py:198`, keyed by user, operator prompt and the draft's input). The deciding call receives its
  complete notes, its own full message and the draft under `SHARED_DRAFT_NOTE` (`app/engine/short.py:61`: not
  checked, the notes decide); it decides for itself, and the draft's text never ships.
- The reply is the deciding model's final text. `answer` is the value of the model's own last `ANSWER:` line
  (`app/answer.py:34`, called at `app/engine/action.py:354` and `app/engine/records.py:585`), with only a matching pair
  of `**` around the whole value removed (`app/answer.py:22`); a line written wholly in such a pair is read the
  same way (`app/answer.py:11`). No value is synthesized when the model wrote no such line.
- `final_text` is the model's reply text exactly as written and `answer` is the model's own slot value as described
  above; no character of either is changed. `tool_calls` is the executor's list of calls that crossed to the request's
  tool endpoint and were acknowledged (`app/tooling/executor.py:148`).

## 2. Fixed properties

- Every deciding turn carries the whole supplied catalog; the host reorders it for presentation only
  (`app/routing/surface.py`) and never removes a tool.
- A tool call is executed only as the model emitted it, with its arguments unchanged; a call the host does not send is
  reported to the model as not sent, never as executed (`app/tooling/executor.py:69-148`).
- A first sending of a call goes out as the model emitted it. An identical call (same tool, same canonical
  arguments) that already ran is sent again only when a one-word model check of the user's message (`SEND`/`HOLD`,
  `app/engine/action.py:69`) finds the message asks for it again; a held repeat is reported to the model as not sent.
- The catalog is fixed for the whole request; no tool is removed while a request runs. A user's wish that no tool be
  used reaches the deciding model in the lane prompt ("If the user wants no tools, use none.",
  `app/engine/action.py:34`); nothing in the host reads the request's wording to grant or withdraw tools.
- Records-lane memory reads are sent to the request's tool endpoint, which records them, and are answered from this
  harness's own store for the requesting user (`app/engine/records.py`, `MemoryTools`); action-lane memory reads are
  answered locally and are not listed in `tool_calls`.
- Advisory passes (order reading, latest-passages reading, result reading, search passes, drafts, follow-up question)
  reach the deciding model only as labelled context beside the complete records it decides from; their text never
  ships as the reply.
- No behaviour depends on a case id, a seed, a validator identity or an expected answer; the case id is used for logs
  and for the tool endpoint's own bookkeeping only.

## 3. Changes on top of the released base

- Meaning router (`app/routing/meaning.py`, `app/engine/agent.py` `meaning_lane`; switch `HARNESS_MEANING_ROUTE`,
  on): after the word rules and their rescues pick a lane, the request is embedded and compared with the
  hand-written example requests in `app/routing/intents.tsv`, none of which comes from a benchmark dataset. When at
  least 80% of the similarity-weighted vote of the 5 nearest examples names the other lane, that lane is used. It
  chooses the prompt and record packet only; the catalog and every tool call are unchanged.
- Packet widening (`app/memory/packet.py` `widen`, `app/engine/agent.py` `widening`; switch `HARNESS_WIDEN`, on): when
  the request names something the records hold (the retriever's anchors; `HARNESS_WIDEN_ANCHORED`, on), the records
  and action packets gain up to 12 records closest to the request by meaning and up to 8 best full-text matches
  that they lack, only while the packet stays within the base budget of 24,000 characters. Existing records keep
  their order and marks; nothing is removed. The program and topic short paths are unchanged.
- Decision-step cap (`app/engine/action.py` `PLAN_ATTEMPTS`): the action lane's one-word decision step may write at
  most 2,500 tokens; when it is cut off, it is asked once more at low effort with 1,200 tokens. As before, the host
  never reads the decision.
