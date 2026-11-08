from __future__ import annotations

from .. import guide_records

NO_RECORD_REPLY = 'say plainly that you have no record of it, and say which records you did check by naming who or what each one is about — not by its label, and without repeating its contents or figures'


def routed_no_record(text: str, message: str, decline: str = '') -> str:
    clause = guide_records.no_record_clause(message) or decline
    return (
        text.replace(guide_records.NO_RECORD_LEAD + NO_RECORD_REPLY, clause, 1)
        if clause
        else text
    )


def shape_skip(
    records: int, names_identifier: bool, statement: bool, names_value: bool
) -> str:
    if records < 1:
        return 'no records to check against'
    if names_identifier:
        return 'the message names an identifier its records carry'
    if statement:
        return 'the message states something and asks nothing'
    if not names_value:
        return 'the message names no value its records hold, and no full name, address, code or quoted words'
    return ''
