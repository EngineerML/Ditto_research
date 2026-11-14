"""Hold back a figure-posting call while the run it reports on is still going.

A message like "run the pipeline workflow, and once it's done, post this run's figure in Jira" asks for the figure
of the finished run. When the latest job listing still shows the run (or its automatic retry) running, a call that
would post or send something goes out with a figure that is not final. The first such call is not sent; the model is
told the run is not finished and to read the job listing again. It decides: send the call again and it goes out.
No model call.
"""

from __future__ import annotations

import re
from typing import Iterable, Protocol

from .tools import UNFINISHED_RE

WRITE_VERB = re.compile(r"(?:^|_)(?:create|add|post|send|new|update|file|log|record|publish|comment|message|write|reply)(?:_|$)", re.IGNORECASE)
JOB_READ = re.compile(r"(?:^|_)(?:list_agent_jobs|list_jobs|get_job|job_status|get_job_status)$", re.IGNORECASE)
WAIT_ASK = re.compile(
    r"\b(?:once it(?:'s| is| has)?\s*(?:done|finished|complete[d]?)|wait (?:for it )?(?:to finish|until)|after it (?:finishes|completes|is done)|"
    r"when it(?:'s| is| has)?\s*(?:done|finished|complete[d]?)|once (?:the )?(?:run|job|workflow) (?:is )?(?:done|finished|complete[d]?))",
    re.IGNORECASE)
JOB_RUNNING_NOTE = ("Not sent, so nothing was posted: the latest {reader} result still shows this run or its retry as "
                    "{status}, so its figure is not final yet. Call {reader} again until it shows the run finished, then send "
                    "{name} with the finished run's own figure. Only if the message does not wait for the run, send it again "
                    "and it goes out.")


class Receipt(Protocol):
    name: str
    output: str
    state: str


def running_job(name: str, message: str, ledger: Iterable[Receipt], completed: str) -> str | None:
    if JOB_READ.search(name) or not WRITE_VERB.search(name) or not WAIT_ASK.search(message):
        return None
    reads = [receipt for receipt in ledger if receipt.state == completed and JOB_READ.search(receipt.name)]
    if not reads:
        return None
    status = UNFINISHED_RE.search(reads[-1].output)
    if not status:
        return None
    return JOB_RUNNING_NOTE.format(reader=reads[-1].name, status=status.group(0).lower(), name=name)
