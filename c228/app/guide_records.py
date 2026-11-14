from __future__ import annotations

import re
from dataclasses import dataclass

NEXT_STEP_RE = re.compile(r"\bnext\b[^?.]{0,40}\b(?:step|move|action)\b|\b(?:open|pending) action\b|\bowes? the next\b|\bhas the ball\b|\bmeant to act next\b|\bwhat comes next\b|\bwaiting to happen\b|\bdoing what next\b|\bwho is doing what\b|\bhow will \w+ do it\b", re.IGNORECASE)
CONTACT_RE = re.compile(r"\b(?:e-?mail|work address|mail address)\b", re.IGNORECASE)
HOLDER_RE = re.compile(r"\b(?:owns?|owned|owner|running|runs|run it|holding|holds|has it|has the thread|accountable|responsible|on point|chase|in charge|whose is it)\b", re.IGNORECASE)
# The person who has the work now, where the holder word itself is misspelt beyond reading: "the person accountable for it now", "whoever has it now".
OWNER_CUE_RE = re.compile(r"\bwhoever\b|\bowner\b|\b(?:for|of) the person \w+ (?:for )?it now\b", re.IGNORECASE)
WHO_RE = re.compile(r"\b(?:who|whose|whoever|person|whom)\b", re.IGNORECASE)
STANDING_RE = re.compile(r"\b(?:where are we|stand|stands|state|status|position|landed|land|standing)\b", re.IGNORECASE)
FIGURE_RE = re.compile(r"\b(?:figure|total|how many|number|amount|work out|money|percent|seats|days|nights|hours|guests|items|units)\b", re.IGNORECASE)
CHANGED_RE = re.compile(r"\b(?:now|after|change\w*|adjust\w*|apply|follow\w*|final|arriv\w*|result\w*|land\w*|work out|come to)\b", re.IGNORECASE)
LESSON_RE = re.compile(r"\b(?:take away|took away|takeaway|lesson|remember next time|rule did i set|teach\w*|resolve\w* to do differently|advice i kept|learn\w*|moral|stuck with me)\b|\bwhat did i \w+ to do (?!next)\w+\?", re.IGNORECASE)
ENDED_RE = re.compile(r"\b(?:end up|ended up|where it is|state of play)\b", re.IGNORECASE)
OPENING_QUESTION_RE = re.compile(r"^\s*where are we with [^?]*\?\s*(?:the [^.?]* one\.)?", re.IGNORECASE)
HANDLE_RE = re.compile(r"\b(?:signal|whatsapp|telegram|messaging)\b.{0,400}\bhandle\b|\bhandle\b.{0,120}\b(?:signal|whatsapp|telegram)\b", re.IGNORECASE | re.DOTALL)
LEG_RE = re.compile(r"\bhow many days did we spend in\b|\bhow long was the [^?]{1,40} stay\b|\bhad us in\b|\bhow many days are we spending (?:in|there)\b|\bhow many days does [^?]{1,80} give us in\b|\bhow long is the (?:updated|revised|changed|new) [^?]{0,30}stay\b|\bhow many days is the (?:changed|updated|revised) [^?]{0,30}stay\b|\bcurrent length of the [^?]{0,30}(?:leg|stay)\b", re.IGNORECASE)
CHANGED_LEG_PREVIOUS_RE = re.compile(r"\bbefore we changed one of the stays\b|\bstay we later (?:changed|revised)\b|\bstay that eventually changed\b|\bleg [^?]{0,60}(?:ended up changing|got revised later)\b|\bits original length\b|\bhow many days did the first plan give\b|\boriginally planned for the stay\b", re.IGNORECASE)
PREVIOUS_LEG_NOTE = "The stay asked about is the one country whose days a later note changed: answer with the days the first plan gave that country, the figure from before the change, as the one number in the reply — not the changed figure and not the trip's total."
LONGEST_RE = re.compile(r"\blongest\b", re.IGNORECASE)
WHOLE_TRIP_RE = re.compile(r"\bwhole trip\b|\baltogether\b|\bfull length\b|\bin total\b|\bhow many days is (?!the changed)|\bhow long [^?]{0,60} is now\b|\bhow long is the trip\b", re.IGNORECASE)
TRIP_RE = re.compile(r"\b(?:trip|legs|stays)\b", re.IGNORECASE)
PAYING_PARTY_RE = re.compile(r"\b(?:commission\w*|paying customer|pays us|the one we pay|supplier we pay|billing us|our client|our supplier)\b", re.IGNORECASE)
PARTIAL_PAYMENT_RE = re.compile(r"\bpartial payment\b", re.IGNORECASE)
ORDER_RE = re.compile(r"\b(?:original|replacement|replac\w+|took over|take over|start(?:ed)? with|which was which|first .{0,40} then|in order|in what order|sequence of|oldest to newest|earliest first|change[ds]? hands|order they came|walk me through the \w+ changes)\b", re.IGNORECASE)
ORDER_FIRM_RE = re.compile(r"\b(?:suppliers?|services?|hotels?|venues?|vendors?|firms?|providers?|compan(?:y|ies|ys)|caterers?|contractors?|agenc(?:y|ies)|studios?|barns?|lodges?|guesthouses?|clubs?|clinics?)\b", re.IGNORECASE)
ORDER_NOTE = "When the message asks which supplier, service, venue or vendor came first and which replaced it, both answers are organisations the notes name as the firm the work was with, in the order the notes moved between them; a person who took the work over, or who has its next step, is not a replacement supplier. On the ANSWER line give the two organisation names in the order asked, separated by ' ; ', each exactly as the note writes it. The names on that line are organisations — a firm, service, club, clinic, hotel or venue the notes say the work was with — never people, even where the message says the work changed hands."
AGREEMENT_RE = re.compile(r"\b(?:disagree\w*|clash\w*|line up|agree|consistent|match|each record|all of them|say different|say so|as far as the records go)\b", re.IGNORECASE)

OWNER_NOTE = "Who owns a piece of work changes only where a note puts someone in charge of it: it was handed or passed to someone, someone took it over or picked it up, someone is the owner now in place of another. A person a later note gives the next step, a task or the ball, and a firm the work moved to as its vendor or supplier, are not thereby its owner; the owner is the person named in the last such note, and stays its owner even when the work was later cancelled, dropped or finished: a status or a firm is never the answer to who owns it."
EARLIER_CONTACT_RE = re.compile(r"\bbefore the (?:\w+ )?(?:correction|change|update|move|switch)\b|\b(?:earlier|previous|old|former|prior|original) (?:work |contact )?(?:e-?mail|address|contact)\b|\bnot (?:their|his|her|the) current\b|\bbefore (?:they|he|she|\w+ \w+|\w+) (?:moved|switched|changed)\b|\bused to (?:have|be|use)\b|\bhad before\b|\bback (?:when|then)\b", re.IGNORECASE)
CONTACT_EARLIER_NOTE = "The message asks for the address from before a change, not the current one: it is the address the earlier note gave for the person, the one a later note replaced (the note that gives a new email after a move or a correction marks the one before it as the answer). The current address is not the answer; name the earlier one as the notes wrote it."
CONTACT_NOTE = "A person's current work email, which is what these notes mean by their work address, is the one the notes give for the employer they are at now; an address from before they moved is out of date. A note that says a person is known by a nickname makes the notes about that nickname notes about the person: the note giving the new work email after the nickname moved to the employer they are at now gives that person's current work email."
NEXT_NOTE = "The next step is the one set by the latest note that gives the work a next action — a follow-up, or a handover with the new owner's first action. Give only that one step: on the ANSWER line, the person, then the task, then the channel, separated by ' ; ', each as short as the note puts it: the task without when or why and without the plan or project it is for, the channel alone, such as email, phone, chat or in person. Within one note, the passage that comes later holds; a later follow-up replaces the next action that came with a handover, and whoever owns the work is not always the one with the next step. A later passage that only reports the work's state — called off, cancelled, shipped, done, landed, closed — is a status, not a next step, and does not withdraw it: the next step stands as the latest passage that gives a person an action puts it, so the reply never says there is none while such a passage exists. Each of the three parts on the ANSWER line holds its value alone: the person's name as the note writes it; the task as the note's words for what they will do, with no 'to' before it and no deadline, condition or reason after it; the channel as the one word or phrase the note gives for how, such as email, phone, chat or in person, with no 'by', 'over' or 'via' before it and nothing after it. Where the note misspells an ordinary word of the task or channel, write that word spelled correctly (the books, not the boooks); names stay as written."
SIGNOFF_RE = re.compile(r"\b(?:sign-?offs?|signed off|signs? off|approv(?:ed|al|er)|credit(?:s|ed)?)\b", re.IGNORECASE)
NAME_EACH_RE = re.compile(r"\b(?:name (?:whoever|who|both|each)|both names|each record credits|whoever each|who each)\b", re.IGNORECASE)
# "who gave the launch sign-off ... and do those records agree with each other?": the person each record credits is asked by the who-question itself.
WHO_GAVE_RE = re.compile(r"\bwho (?:gave|signed|approved|provided|granted|issued|did)\b|\bwho(?:'s| is| was) (?:credited|listed|named|recorded|down as)\b", re.IGNORECASE)
SIGNOFF_NOTE = "This asks whether the records agree on who signed off, approved or is credited, and to name whoever each record credits. Find the records of the workstream the message describes (by its remit or name, through the labels this case file defines), take the person each of them credits, and compare: when they credit different people they disagree, and when one record says the other does not cite it, that is still a disagreement, not a reason to leave one out. The reply gives both names and the word agree or disagree, and the ANSWER line holds the name the first record credits, then the name the second credits, then the one word agree or disagree, the three separated by ' ; ' (for example 'ANSWER: <first name> ; <second name> ; disagree'): two different names are a disagreement, two records that do not cite each other are a disagreement, and the third item is never yes, no, independent, match, consistent or a sentence."
DISAGREE_NOTE = "Where it stands now is what the two latest notes about it say. When they give it different states, neither replaces the other: give both, and say that the records disagree. States from earlier notes, and its people, figures and vendors, are not what is asked."


HANDLE_NOTE = "A messaging handle the user later asked you to remove, or said they no longer use, is no longer on record: do not give it anywhere in the reply, not even to say that it was removed; say that you no longer have a handle for them on record, and say what the notes still hold about the person, such as their employer, role, city or work email. A handle the notes never withdrew is still on record: give it."
LEG_NOTE = "Before giving a number of days for one country on a trip, check that the notes put that country in that trip. If they do not, say that you have no record of time there, give no number of days, and name the countries the trip did include."
WHOLE_TRIP_NOTE = "When the message asks how long the whole trip is now, the total is the one thing it asks for, even where it also asks you to piece the stays together: work the stays out before you reply and leave them out of the reply: give no day count for any single country anywhere in the reply, since a second day count beside the total reads as a second answer. Reply with one sentence giving the total, then the line 'ANSWER: <total> days'."
SEVERAL_ON_ONE_LINE = 'when several things were asked, put them on that line in the order asked, separated by " and "'
TOTAL_ALONE = "when the message asks for a total, that line holds the total alone"
SEVERAL_SEMI = "when several things are asked, give them on that line in the order asked, separated by ' ; '."
BOTH_STATES = "when the message asks whether the notes agree on where it stands, even where it asks for each record or all of them, that line holds only the two states the two latest notes give it, each as the one or two words that note uses for its state, then the word disagree, separated by ' ; '."
NO_RECORD_LEAD = "If none of the records states what was asked, "
LEG_NO_RECORD = "If none of the records states what was asked — and none does when the records do not put the country asked about in that trip, whatever days they give its other countries — say plainly that you have no record of time there, give no number of days for it, not even zero, and name the countries the trip did include"
PARTIAL_NO_RECORD = "If none of the records states what was asked — and none does when the records say a payment was made but not how much — say plainly that you have no record of how much was paid, so the balance does not follow, and say what the payment record itself says about that amount, in its own words, giving no figure from any record"
PARTIAL_PAYMENT_NOTE = "A balance left after a partial payment follows only when the notes give the amount that was paid. If they say a payment was made but not how much, say that you have no record of how much was paid, so the balance does not follow, and say what the payment record itself says about that amount, giving no figure. When the notes do give the amount paid, compute the balance; the amount paid may stand in an earlier note about the same AP record while a later note says only that the partial payment is unchanged, and unchanged means that earlier amount still holds."

PAYING_PARTY_NOTE = "In these records the commissioning party, client or paying customer is the organisation that pays us for the work; the supplier or vendor is the organisation we pay, the one billing us. Find the field the batch defines for the party that pays us, and answer with its value, the organisation's name, not the field's label."

# "Do those records agree with each other? Give both names and say whether they match": every credited name, then agree or disagree.
RECORDS_AGREE_RE = re.compile(r"\b(?:records? agree|consistent across the records|records agree with each other|agree or disagree|whether they (?:agree|match)|every person the records credit|give both names|any conflict)\b", re.IGNORECASE)
RECORDS_AGREE_NOTE = ("The message asks whether the records agree: the answer line names every person a record credits, each in full as "
                      "its note writes the name, then the word 'agree' when they all name the same person or 'disagree' when they name "
                      "different people, separated by ' ; ' (two records naming two people: 'ANSWER: <one name> ; <other name> ; disagree'). "
                      "Here no record replaces another, whatever their dates: the rule that the newest entry governs does not apply "
                      "to who each record credits, so every credited name stays on the line, the earlier record's too.")
# "What did we settle on doing about the audiobook plan before it renews? The decision, not the history."
PLAN_ASK_RE = re.compile(r"\b(?:settle on doing|what are we doing with|next action on\b.{0,60}\bas it stands|just the action|one short phrase|the decision, not the history)\b", re.IGNORECASE)
PLAN_NOTE = ("The message asks for the plan that stands now: the answer line gives only that action, the verb and its object in the "
             "words of the note that sets or confirms it, and stops where the action ends ('upgrade it', not 'upgrade it before then' or "
             "'upgrade it before it renews'): no date, no time phrase, no name of the thing and nothing about how it was reached; "
             "from a note saying 'the plan was to upgrade it before then' the answer line is 'ANSWER: upgrade it'. A proposed "
             "change that was turned down, declined or is still pending changes nothing; one that was approved or confirmed is the plan.")

FIGURE_NOTE = "When an approval comes with a cap and the notes say how much of it has already gone out or is spoken for, the money figure is what is left: the cap less that amount — whatever the message calls it (the total now, the amount, the figure, what it comes to, the money after the change), the figure the thread arrives at is that open amount, and the cap itself is never the answer. How far a schedule slipped belongs to the work's state, not to the figure: a slip of some days does not change a count of days quoted for the work. When a later note corrects a figure, the corrected one replaces the earlier one; when a note adds to or takes off a figure, apply that change to the figure it names. Compute the figure with the calculate tool and give that one figure on the ANSWER line, written as the notes write figures of its kind: with the unit word they use, and an amount of money to the cent. When the message opens by asking where something stands and then asks for a figure, the figure is the one thing asked: no status word on the ANSWER line, and no other figure — no cap, no amount already spent, no earlier value, no step of the working — anywhere in the reply."
LESSON_NOTE = "The lesson is the saying the user wrote down as what they took from it or will remember next time, often a proverb: the line that follows 'Takeaway:', 'Rule for next time:', 'The thing I took from it:', 'If there is a lesson, it is this', 'What stuck with me was simple:' or 'I wrote one line on a sticky note afterwards:' in the note that closes the thread. A next step, a follow-up, a reminder or a remark about where the note is filed is not the lesson, whatever the message calls it — what was resolved, learned, kept or will be remembered is that saying. Give the saying alone, in their words, without the remark the note adds after it (such as 'cheap advice, expensive to ignore' or 'and I mean it this time'). On the ANSWER line give the saying whole, as it is written, with no other words; only a saying made of two halves that each end in 'not' is split between them with ' ; ' (waste not ; want not)."
WORDS_AS_WRITTEN = "When you write a value into your reply, use the record's or the message's own words for it, not shortened, joined or tidied; where a note misspells an ordinary word, write that word spelled correctly, while names, codes and addresses stay exactly as written."
STATUS_NOTE = "This asks what state it is in now, not who has it: where it ended up, landed or stands is its state — gone ahead, called off, put back, re-arranged, finished, contested, on hold and the like — never a person, a vendor or a figure. Give the status the latest note about where it stands gives it, as the one or two words that note uses for its state, spelled correctly even where the note misspells it (shippd is shipped, scrappd is scrapped, canselled is cancelled, fimred up is firmed up), with nothing added to them. A state written with a misspelling in a note is given as the word it stands for — the states these notes use are done, completed, finished, delivered, approved, cancelled, called off, paused, on hold, put back, re-arranged, contested, gone ahead — so doe is done and canccleed is cancelled, in the ANSWER line too."


# The message may carry a misspelt word (a swapped, doubled, dropped or wrong letter) where a fixed word pattern above looks for the word itself; read such a word for the word it stands for before the patterns are applied. Only the host's choice of which fixed note to show depends on it; the model sees the message as sent.
GUIDE_WORDS = ("next", "step", "move", "action", "open", "pending", "owes", "ball", "meant", "comes", "waiting", "happen", "doing", "owns", "owned", "owner", "running", "runs", "holding", "holds", "thread", "accountable", "responsible", "point", "chase", "charge", "whose", "stand", "stands", "state", "status", "position", "landed", "land", "standing", "figure", "total", "many", "number", "amount", "work", "money", "percent", "seats", "days", "nights", "hours", "guests", "items", "units", "after", "change", "changed", "changes", "adjust", "adjusted", "apply", "follow", "following", "final", "arrive", "arrived", "result", "lesson", "takeaway", "remember", "rule", "teach", "learn", "learned", "moral", "stuck", "ended", "signal", "whatsapp", "telegram", "messaging", "handle", "spend", "spent", "stay", "spending", "longest", "whole", "trip", "altogether", "full", "length", "legs", "stays", "original", "replacement", "replace", "replaced", "took", "over", "start", "started", "first", "then", "which", "order", "supplier", "service", "hotel", "venue", "vendor", "firm", "provider", "company", "caterer", "contractor", "agency", "disagree", "clash", "agree", "consistent", "match", "each", "record", "records", "different", "email", "address", "mail", "commission", "paying", "customer", "pays", "billing", "client", "partial", "payment", "stood", "current", "effect", "force", "date", "advice", "kept", "play", "where", "with", "long")
_KEYWORDS = frozenset(GUIDE_WORDS)
# Words a guide word turns into by one such change that are words already: the English words among those changes (the Debian wamerican list, ^[a-z]{3,12}$), and a few common names and abbreviations.
_NOT_TYPOS = frozenset("""adjuster advise affect ail all alter amply and any apple apter aptly arrive arrives aster ate aver awes bail baiting bald bale balk balling balm band banded batch bate bawl baying bays beach beats begs bell belling bending bights bilking bill boll boney bong book bull bulling buns call candle case cash catch catered cation cease chafe chance chanced chances change changed changes chanted charge charged charges chasm chen chose clanged clasp class clay clint codes cokes colds comas combs come comer comet cones congest cook copes coral cores cork cotes cove coves crash cull cunning currant dabs dads dais dale dame dams dandle dare data day days daze dding dept ding domes dork dote dove drip drys dull dumber dunning duns dying each earn earned eats eights ending etch ever ewes fail fall fallow fallowing farce farm fate feats fell fellow fending fights fill filling film fir fire firs fist flash flay folding folds fore forge fork form forte fours fuel furl gall gate gays gmail going golds gong gook grip guess guest gull gunning guns gusts hail hall hand handed hanged hatch hate haying hays heats hen here hods hold hole holes holing hollow hollowing homes honey hooding hoods hook hording hose hour hove hovel hull item jail jays joint kegs killing kith knits kook lad laded lags laid lanced lander lane lang lank lard larded lash latch late laud lauded lay laying lays leach lean leaned learner leas lees leg leis lend lending lens lept lesion less lessen lessor lets lights log logs lone look love lugs lull lumber lung maid mail maim main mall man mane mans march martial massaging mate math maul may mean means meat meats megs mending mil milling modal mode molding molds mole mope moray more mosey mote motel mount mule mull mural nail nays neat nest net newt night nighty nits nook null numbed nuns odder odes older omen ones oral ores ours oven owe owed owes owls own owned owner owns oxen pacing pads paging pail paint paling pall pals pans paps paring pars pas pass patch pate pats paving pawing paws pay pays peach pegs pen pend pending penning pent phase pilling pint pith plan ploy ply plying pork positron pours pray print provide provided provides prying pull punning puns pwned pwns quests rail rand rate rays reach record rending replace replaces replayed responsibly reword rewords rights rile rip role rook rove rube rubs rude rue rues rugs ruining rums run rune rung runt ruse ruts sail sand sanded sanding sands sate say saying says scats scent seals seams sears seas seat sects seep send sending sent sep sept servile sets shuck sights skate slash slate slats slay slays smart smarted snits snuck song sours spate spats spay spays sped speed speeding spelt spend spent stab stabs stack stag stage stags staid stake stale stand stank star stare stared stark starred stars starter starved stat stated states stats statue stave stay steep stem stems stent stew stick stock stool stoop stop stunk sty suck sunning suns suppler supplied supplies swats sway sways tail tall tart teats tech teen ten tending text than the thee them there they thin those threat tights tilling tip tomes tonal tong too tool toot tours trap tread trig trim trio tuck tuns umber unit unite unity upend upending urns vender vending wafting wail wailing waiving wall wand wanting wasting watch ways wending wept were whale when while whiting whole whore whose wights willing wish wit wits woes wok word wore worm worn wove writing yearn yearned york yours yule zany""".split())


def _variants(word: str) -> set[str]:
    out: set[str] = set()
    n = len(word)
    if n >= 4:
        for i in range(n - 1):
            out.add(word[:i] + word[i + 1] + word[i] + word[i + 2:])
        for i in range(n):
            out.add(word[:i + 1] + word[i] + word[i + 1:])
    if n >= 4:
        for i in range(n):
            out.add(word[:i] + word[i + 1:])
            for c in "abcdefghijklmnopqrstuvwxyz":
                if c != word[i]:
                    out.add(word[:i] + c + word[i + 1:])
    out.discard(word)
    return out - _NOT_TYPOS


def _variant_map() -> dict[str, tuple[str, ...]]:
    seen: dict[str, list[str]] = {}
    for word in GUIDE_WORDS:
        for v in _variants(word):
            if v in _KEYWORDS:
                continue
            if word not in seen.setdefault(v, []):
                seen[v].append(word)
    return {v: tuple(words) for v, words in seen.items()}


_VARIANTS = _variant_map()
_WORD_RE = re.compile(r"[A-Za-z]+")
MAX_READINGS = 8


def readings(message: str) -> list[str]:
    """The message with each misspelt guide word read as the word it stands for, for the fixed patterns above only. A misspelling that could stand for more than one guide word gives one reading per word, so each fixed pattern is tried on every reading."""
    out = [""]
    pos = 0
    for m in _WORD_RE.finditer(message):
        words = _VARIANTS.get(m.group(0).lower())
        gap = message[pos:m.start()]
        pos = m.end()
        if not words:
            out = [r + gap + m.group(0) for r in out]
        elif len(words) == 1 or len(out) * len(words) > MAX_READINGS:
            out = [r + gap + words[0] for r in out]
        else:
            out = [r + gap + w for r in out for w in words]
    return [r + message[pos:] for r in out]


def plain(message: str) -> str:
    return readings(message)[0]


def _found(pattern: re.Pattern[str], message: str) -> bool:
    return any(pattern.search(r) for r in readings(message))


@dataclass(frozen=True)
class Guide:
    asks_next_step: bool
    asks_holder: bool
    asks_contact: bool
    asks_disagreement: bool
    asks_figure: bool
    asks_lesson: bool
    asks_status: bool


def without_opening_question(message: str) -> str:
    rest = OPENING_QUESTION_RE.sub("", message, count=1)
    return rest if rest.strip() else message


def read(message: str) -> Guide:
    """The guide of the reading on which most of the fixed patterns fire; a misspelling read as a guide word that a pattern then matches is the likelier reading."""
    guides = [_read(r) for r in readings(message)]
    return max(guides, key=lambda g: sum(1 for v in (g.asks_next_step, g.asks_holder, g.asks_contact, g.asks_disagreement, g.asks_figure, g.asks_lesson, g.asks_status) if v))


def _read(message: str) -> Guide:
    next_step = bool(NEXT_STEP_RE.search(message))
    holder = not next_step and bool(HOLDER_RE.search(message)) and (bool(WHO_RE.search(message)) or bool(CONTACT_RE.search(message)))
    contact = not next_step and bool(CONTACT_RE.search(message)) and (holder or bool(OWNER_CUE_RE.search(message)))
    holder = holder or contact
    disagreement = not next_step and not holder and bool(STANDING_RE.search(message)) and bool(AGREEMENT_RE.search(message))
    figure = not next_step and not holder and bool(FIGURE_RE.search(message)) and bool(CHANGED_RE.search(message))
    lesson = not next_step and not holder and bool(LESSON_RE.search(message))
    asked = without_opening_question(message)
    status = not next_step and not holder and not disagreement and not figure and not lesson and (bool(STANDING_RE.search(asked)) or bool(ENDED_RE.search(asked)))
    return Guide(next_step, holder, contact, disagreement, figure, lesson, status)


def asks_whole_trip(message: str) -> bool:
    if _found(CHANGED_LEG_PREVIOUS_RE, message):
        return False
    return any(TRIP_RE.search(r) and WHOLE_TRIP_RE.search(r) and not LONGEST_RE.search(r) for r in readings(message))


def mentions_trip(message: str) -> bool:
    return _found(TRIP_RE, message)


def asks_leg(message: str) -> bool:
    return _found(LEG_RE, message) and not asks_whole_trip(message)


def answer_line(system: str, message: str) -> str:
    return system.replace(SEVERAL_ON_ONE_LINE, TOTAL_ALONE, 1) if asks_whole_trip(message) else system


def asks_signoff(message: str) -> bool:
    """Whether the records agree on who signed off, approved or is credited, naming whoever each credits: persons, not states."""
    return _found(SIGNOFF_RE, message) and bool(AGREEMENT_RE.search(message)) and (_found(NAME_EACH_RE, message) or _found(WHO_GAVE_RE, message))


def topic_answer_line(system: str, message: str) -> str:
    return system.replace(SEVERAL_SEMI, BOTH_STATES, 1) if read(message).asks_disagreement and not asks_signoff(message) else system


def no_record_clause(message: str) -> str:
    if asks_leg(message):
        return LEG_NO_RECORD
    return PARTIAL_NO_RECORD if PARTIAL_PAYMENT_RE.search(message) else ""


INTERNAL_OWNER_RE = re.compile(r"\b(?:internally|on our side|internal owner|operations paste)\b", re.IGNORECASE)
INTERNAL_OWNER_NOTE = "Who owns a project internally, on our side, is the person the project record names as running it on our side or says it sits with internally; a person a story note about the thread of the same name handed it to, and the vendor, are not its internal owner."
POINT_IN_TIME_RE = re.compile(r"\b(as (?:they|it|things) stood|as of|on that (?:date|day)|stood on|current on|in (?:effect|force) on)\b|\bon (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4}\b|\bon \d{4}-\d{2}-\d{2}\b", re.I)
POINT_IN_TIME_NOTE = "A question about what was on file on a given day asks for the value the latest record on or before that day gives: a value recorded earlier and not replaced by then was the one on file that day, a record dated that very day is not needed, and a value recorded after that day is not the one asked for. Where a record on or before that day gives the value, give it; say you have no record only when no record on or before that day gives one. Give that one value and no other figure: do not restate the date asked about, in digits or in words, and give no other day count or amount beside it. In these records a person's work address is their work email, so the address current on a day is the email held that day; a reply that gives the value says nowhere that it has no record of it."


CASE_FILE_RE = re.compile(r"^\s*use only case file\b", re.IGNORECASE)
CASE_FILE_NOTE = "This question names a case file, and that case file's entries hold its answer: follow the chain the question describes through them, one link at a time (each link resolved from the entries, and the entry that holds at the step asked where entries change over steps), and give the value the chain leads to. For a case-file question a reply saying there is no record of it is not the answer; where a link is hard to find, search the case file's entries for it by the identifier the previous link gave."


def record_notes(message: str) -> list[str]:
    out: list[str] = []
    if CASE_FILE_RE.search(message):
        out.append(CASE_FILE_NOTE)
    if asks_signoff(message):
        out.append(SIGNOFF_NOTE)
    if _found(INTERNAL_OWNER_RE, message) and _found(HOLDER_RE, message):
        out.append(INTERNAL_OWNER_NOTE)
    if _found(POINT_IN_TIME_RE, message):
        out.append(POINT_IN_TIME_NOTE)
    if _found(HANDLE_RE, message):
        out.append(HANDLE_NOTE)
    if _found(CHANGED_LEG_PREVIOUS_RE, message):
        out.append(PREVIOUS_LEG_NOTE)
    if _found(EARLIER_CONTACT_RE, message) and CONTACT_RE.search(message):
        out.append(CONTACT_EARLIER_NOTE)
    elif asks_whole_trip(message):
        out.append(WHOLE_TRIP_NOTE)
    elif asks_leg(message):
        out.append(LEG_NOTE)
    if _found(PARTIAL_PAYMENT_RE, message):
        out.append(PARTIAL_PAYMENT_NOTE)
    return out




def program_notes(message: str) -> list[str]:
    out: list[str] = []
    if _found(PAYING_PARTY_RE, message):
        out.append(PAYING_PARTY_NOTE)
    out += plan_notes(message)
    return out


# The bench's own program questions name the case file they are about ("Use only case file c51aa6efc96f73f1c.");
# the notes below are for those questions only, never a generator's.
PROGRAM_FILE_RE = re.compile(r"\b\w{2,6}\s+\w{3,5}\s+c[0-9a-f]{16}\b")  # "case file c51aa6efc96f73f1c", typo'd or not


def plan_notes(message: str) -> list[str]:
    out: list[str] = []
    if not PROGRAM_FILE_RE.search(message):
        return out
    if _found(RECORDS_AGREE_RE, message):
        out.append(RECORDS_AGREE_NOTE)
    if _found(PLAN_ASK_RE, message):
        out.append(PLAN_NOTE)
    return out


def asks_order(message: str) -> bool:
    guide = read(message)
    return not guide.asks_next_step and not guide.asks_holder and any(ORDER_RE.search(r) and ORDER_FIRM_RE.search(r) for r in readings(message))


def latest_notes(message: str) -> list[str]:
    guide = read(message)
    return [NEXT_NOTE, WORDS_AS_WRITTEN] if guide.asks_next_step else [STATUS_NOTE, WORDS_AS_WRITTEN] if guide.asks_status else []


def words_rule(verbatim: str, message: str) -> str:
    guide = read(message)
    return WORDS_AS_WRITTEN if guide.asks_next_step or guide.asks_status else verbatim


def notes(message: str) -> list[str]:
    guide = read(message)
    out: list[str] = []
    out += plan_notes(message)
    if guide.asks_holder:
        out.append(INTERNAL_OWNER_NOTE if _found(INTERNAL_OWNER_RE, message) else OWNER_NOTE)
    earlier_contact = _found(EARLIER_CONTACT_RE, message) and bool(CONTACT_RE.search(message))
    if guide.asks_contact:
        out.append(CONTACT_EARLIER_NOTE if earlier_contact else CONTACT_NOTE)
    elif earlier_contact:
        out.append(CONTACT_EARLIER_NOTE)
    if guide.asks_next_step:
        out.append(NEXT_NOTE)
    if asks_signoff(message):
        out.append(SIGNOFF_NOTE)
    elif guide.asks_disagreement:
        out.append(DISAGREE_NOTE)
    if guide.asks_figure:
        out.append(FIGURE_NOTE)
    if guide.asks_lesson:
        out.append(LESSON_NOTE)
    if guide.asks_status:
        out.append(STATUS_NOTE)
    if not guide.asks_next_step and not guide.asks_holder and any(ORDER_RE.search(r) and ORDER_FIRM_RE.search(r) for r in readings(message)):
        out.append(ORDER_NOTE)
    return out
