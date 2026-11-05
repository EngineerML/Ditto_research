"""Spelling-tolerant reading of the words that say which kind of story question is asked.

Messages arrive with dropped, doubled, swapped or mistyped letters ("Whsoe", "stte of ply", "taech"). Before the routed
note patterns (`app/guide_records.py`) read a question, a word one or two letters away from one of these words, with the
same first letter, is read as that word. Capitalised words inside a sentence (names) and ordinary words that sit close to
one of these words are left as written. The deciding model always receives the message exactly as the user wrote it.
"""
from __future__ import annotations

import difflib
import re
from collections import Counter
from functools import lru_cache

from .english_words import WORDS

# Ordinary words of everyday notes that the word list lacks.
NOTE_WORDS = frozenset("""attendee cafe communication footer handoff headcount neighbours onboarding organisation payables reconstructing rollout scratchpad transcription workspace workstream""".split())

WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
CUE_WORDS = frozenset("""next step move action pending waiting happen meant doing comes owes owner owns owned running holding
holds thread accountable responsible point chase charge whose person whoever email address work where stand stands standing
state status position landed figure total many number amount money percent seats days nights change after apply final
resulting result adjustment operation arrive take away takeaway lesson remember teach learn moral stuck advice kept rule
myself resolve differently wrapped disagree disagreement clash match consistent agree handle signal whatsapp telegram
spend spending stay partial payment paid balance whole trip altogether long raise lower leave unchanged increase
decrease""".split())
LOOKALIKES = frozenset("""stop stem steep steps stake skate slate spate stage stale stare stall stank stance strand there here were
whore wheel whole while those hose own pint print paint points poin threat dress currents accountant response responses
positions positive states statue statues stack stick stuff chose chaste cause plan plans plat pray prey plays player played
lander landes mane mans many's mandy marry numbed totals tonal figures finals finale amounts apple amply chance changed
changes charge charged note noted nodes record recorded recorder opera arrived arrives tech teacher teaches leach lean
leant learnt morale mortal morals advise kepi role roles rude ruse rules tame tale tape taken takes wrapper move moved
moves mover action's actions acting ball's balls bell bale owed owes owner's owners runner runny hold holder holdings
match's matches matched mother clad clash's agreed agrees bill bills chapel channel started starts stated state's stats plane plain happy coming comet comma mean means meaning dining dying doling resolved resolves hand hands handled handles handler single signals spent stag star stab stray partly parties
partner partners pavement paint pain pair paired bale balances while whale whose trap trim tripe trips lone lung longer raised raises rise raisin lowered lowers flower power leaves leaved lease league
increased increases decreased decreases changed""".split())


def within_one_edit(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    return any(longer[:i] + longer[i + 1:] == shorter for i in range(len(longer)))


def close_to(word: str, cue: str, heavy: bool = True) -> bool:
    if word[0] != cue[0] or word.startswith(cue) or cue.startswith(word):
        return False
    if within_one_edit(word, cue):
        return True
    if len(word) >= 5 and sorted(word) == sorted(cue):
        return True
    if not heavy:
        return False
    # Longer words are recognised through heavier misspelling (two or three letters off).
    return len(word) >= 6 and abs(len(word) - len(cue)) <= 2 and difflib.SequenceMatcher(None, word, cue).ratio() >= (0.7 if len(cue) >= 7 else 0.85)


# Words of the tool-request kinds (`app/request_kinds.py`), read the same way by `fold_request`.
REQUEST_CUES = frozenset("""throwaway scratch receipt reconciliation feedback workflow workflows schedule schedules calendar
reasoning effort thinking artifact interactive clickable sandbox accent typeface appearance options configured background
agent remember record handoff search compute calculation image picture previous latest generated exists already closest
matching verify confirm inspect review spelling misspelled kick saved""".split())
REQUEST_LOOKALIKES = frozenset("""through throw scratched scratches receipts recipe deceit reconcile feed feeding feedbacks workout
workplace reschedule schedule's scheduled calendars reason reasons reasonable effect efforts thinkin thanking artifacts artificial
interaction interact clickbait sandboxes access accents accept typefaces appearances option optional configure backgrounds
agents agenda agency remembered remainder record's records recorded handoffs handout searched searches computer computed
computes calculations images imagine pictures previously lately latter generate generates existed exits already's closet
closer matching's matched verified confirmed inspected reviewed reviews spell spelled spellings remaining remain
interface interfaces reasoned reasonably kicks kicked kink sated saves safed""".split())


def fold(text: str, cues: frozenset[str] = CUE_WORDS, lookalikes: frozenset[str] = LOOKALIKES, heavy: bool = True) -> str:
    def fix(match: re.Match[str]) -> str:
        word = match.group(0)
        low = word.lower()
        inside = match.start() > 0 and not re.search(r"(?:^|[.?!:;—–-])\s*$", text[: match.start()])
        if len(low) < 4 or low in cues or low in lookalikes or (word[0].isupper() and inside):
            return word
        near = [cue for cue in sorted(cues) if close_to(low, cue, heavy)]
        # The closest cue word wins ("stadning" is "standing", not "spending").
        return max(near, key=lambda cue: difflib.SequenceMatcher(None, low, cue).ratio()) if near else word
    return WORD.sub(fix, text)


def fold_request(text: str) -> str:
    # Request words are read through one-letter slips and scrambles only: longer request words sit close to ordinary
    # ones ("remaining" / "reasoning", "interface" / "interactive").
    return fold(text, REQUEST_CUES, REQUEST_LOOKALIKES, heavy=False)


# A key to the misspelt ordinary words in passages shown to the model, so a reply that uses one of them writes the word
# meant ("deoivered" is "delivered"). Notes are shown unchanged; the key sits beside them. A word is misspelt when it is not
# an English word (app/english_words.py), occurs once in all of the user's notes, and is one letter off an English word
# those notes use; the most used such word is the one meant.
SPELLING_KEY_HEADER = "What code takes to be misspelt words in the passages above, each with the word it stands for, not checked; where your reply uses one of them, write the word it stands for, and do not repeat this list in your reply:"
# Ordinary words only: not a piece of an email address, link or identifier.
KEY_WORD = re.compile(r"(?<![\w'@./-])[a-z]{3,12}(?![\w'@/-]|\.\w)")
KEY_MAX = 20


LETTERS = "abcdefghijklmnopqrstuvwxyz"
KEY_LONG = 7
KEY_LONG_RATIO = 0.8
KEY_SHORT = 5
KEY_TYPO_TIMES = 2
CAPITALISED = re.compile(r"\b[A-Z][a-z]+\b")
KEY_SEEN = 3
KEY_SLIP_MIN = 3
KEY_SLIP_TIMES = 2
PAIR_WORD = re.compile(r"[a-z]+")


def edits(word: str) -> set[str]:
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    return ({a + b[1:] for a, b in splits if b} | {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
            | {a + c + b[1:] for a, b in splits if b for c in LETTERS} | {a + c + b for a, b in splits for c in LETTERS})


def letters_off(a: str, b: str, limit: int = 2) -> int:
    # Edit distance counting a swap of neighbouring letters as one; anything over the limit reads as limit + 1.
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    before: list[int] = []
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        now = [i]
        for j, y in enumerate(b, 1):
            cost = min(row[j] + 1, now[j - 1] + 1, row[j - 1] + (x != y))
            if i > 1 and j > 1 and x == b[j - 2] and a[i - 2] == y:
                cost = min(cost, before[j - 2] + 1)
            now.append(cost)
        if min(now) > limit:
            return limit + 1
        before, row = row, now
    return row[-1]


# The words this miner's routing and note patterns are written in. `read_form` turns a misspelt word of a message into the
# one of these it stands for, for the choice of lane and note only: the deciding model always gets the message as written.
READING_WORDS = frozenset("""abilities able about accent account accountable accountant across acting action actions actual actually added
address addresses adds adjust adjustment advice advise affecting after afterwards again agent agents agree agreed
agreement agrees ahead alias aliases alone along already also altogether always amount amounts amply anchor anchors
angles annotations another answer answers anything anywhere appearance append apple apply approval approved
arithmetic around arrive arrived arrives articles artifact artifacts asked asking asks assistant august automatic
autumn available average away back background balance balances bale ball balls band bank base batch bear been before
begin being bell belongs beside best bill billing bills binding block blower blurb boil book both braise breach
break brief brighten browse budget budgeting build builds built bump cadence calculate calculation calendar came
cancel cancelled cannot capabilities capability capable carried case causative cause chance change changed changes
channel chapel charge charged chars chase chaste chat check checked chile choice chose city clad clash class
classify clause clauses clear click clickable client close closest code collections color come comes comet coming
comma commission committed common company compile completed compound compute concurrently configured confirm connect
consistent contact continue control convert correct corrected correction correctly corrects could count counter
countries country counts covered create crop crunch cues current currently currents customer daily dark date dated
dates days decide decided deciding decrease decreased decreases deducted deep deeply default define defines delegate
delete delivered deploy depth describe detail device diff different differently digit digits dining direction
disable disagree disagreement discover dispatch dispatched disposable ditto divide divided does doing doling done
double doubled down draft draw dress drop dropped dying each earlier earliest edit effect effecting effort else
email emails employer enable ended entirely entry enumerate envelope escape even every everyday everything exactly
execute existing exists explain export fact fall false feature features feedback fetch fetches fetching field figure
figures file filed final finale finals find finished fire firm firms first flight float flower fold folks follow
following follows font fonts forget form format forward found fractions framing fresh from frozen full future game
generate generated generic gets getting gist give gives giving goes going gone google grab ground group guests guide
habit hand handed handle handled handler handles hands hang happen happened happy hard have head header headlines
heads held hello help here hold holder holding holdings holds hose hours however identifier image imperative import
inbox include including incomplete increase increased increases independent index information initial inside inspect
instead interact interactive interface internet into invoice item items itself jobs join just keep kept kick kicked
kind kindly kinds know known label lacks lambda land landed lander landing lane last later latest launch leach lead
leading leads league lean learn learnt lease leave leaved leaves ledger left legs length less lesson letter letters
letting level light like line lined lines link linked list listed live local lone long longer longest look
lookalikes looked looks lookup loose loosely looser lower lowered lowers lung made mail main make manage mane mans
many march markdown marry match matched matches matching matter mean meaning means meant median memory message
messages might mind minus minute mirror missing misspell misspells misspelt mode model modifiers moment money month
months moral morale morals more mortal mother move moved mover moves much multiply must myself name named names near
nearest need needed needs negated never newest news next nickname nights nodes none normal normalize note noted
notes noun nouns nowadays numbed number numbers often okay once online only onto open opener opening opera operation
option options order ordinary original originally other outline outside over owed owes owned owner owners owns page
paid pain paint pair paired pairs parallel part partial parties partition partly partner partners parts party pass
passage passed pasted pattern patterns paused pavement paying payment pays pencil pending people percent percentage
person personal phone phones phrase pick picked picture piece pieces pint place plain plan plane planned plans play
played player plays please plus point pointers points polite position positions positive possessed possession post
postponed power pray prefixes present preview previous prey price prices print prior probes proceed process product
program progress project prompt protocol proverb pull pushed puts qualifiers question queue queued quick raise
raised raises raisin range ratio read reading reads real reason reasoning reasons recall recap receipt receives
record recorded recorder records recurring reference references registry remain remaining remains remark remember
remind remove removed rename render rendered renders repeat repeating replace replaces reply report reported request
requests research resolve resolved resolves respond response responses responsible rest result resulting resume
retrieval retry return review reviewer rework right rise role roles routed routing rude rule rules runner running
runny runs ruse said same sandbox save saved saying says schedule scheduled schedules scrape scratch search seats
seen send sending sense sent sentence separate separated setter setting settings settled setup several shall shifted
shoot short shorter should show shown side signal signals signature signed since single singular sitting skate skip
slate slipped slot slots snake snap snippet some someone something soon sort sorted source span spate speech spell
spelled spelling spellings spend spending spent spin split spoken spread spreadsheet spring stab stack stag stage
stake stale stall stance stand standing stands stank star stare start started starting starts state stated statement
states stats statue statues status stay stays steep stem step steps stick still stop store stored story strand stray
strip stuck stuff subject subordinate such summarize summary summer supplier sure swapped switch sync synonyms
system tail tails take taken takes tale talk tame tape target task tasks teach teacher teaches team tech telegram
telephone tell tense text thanks that their theirs them theme then there thereby these they thing things think
thinking this those thread threat three through throwaway tighten time timed timer times timestamp timetable today
together tokens tolerant tonal took tool tools topic total totals touch track tracker trap trigger trim trip tripe
trips true trust turn tweak twice typeface typo unchanged unit units unknown update updated usable used user
username usernames usual value values vendor vendors venue verb verbs verify version vocabulary waiting walk want
warm ways week weekly weeks well went were whale what whatever wheel when whenever where whether which while whoever
whole whom whore whose wide will winter with withdrew within without word worded words work worked worker workers
workflow workflows working world would wrapped wrapper write written wrong wrote year your""".split())
# Three-letter English words (app/english_words.py starts at four letters).
SHORT_WORDS = frozenset("""ace act add adj ado ads adv adz aft age ago aha aid ail aim air alb ale all alt amp amt and ani ant any ape app apt
arc are ark arm art ash ask asp ass ate auk avg awe awl axe aye baa bad bag bah ban bar bat bay bed bee beg bet bib
bid big bin bit boa bob bog boo bop bot bow box boy bpm bra brr bud bug bum bun bur bus but buy bye cab cad cal cam
can cap car cat caw chi cis cob cod cog col con coo cop cot cow cox coy cry cub cud cue cum cup cur cut dab dad dam
day dds deb den dew did die dig dim din dip dis doc doe dog don dos dot doz dpi dry dub dud due dug duh dun duo dye
ear eat ebb eds eel egg ego eke elf elk ell elm emo ems emu end eon era ere erg err esp est eta etc eve ewe eye fad
fag fan far fat fax fed fee fem fen fer few fey fez fib fie fig fin fir fit fix flu fly fob foe fog foo fop for fox
fro fry ftp fum fun fur fwd gab gad gag gal gap gas gay gee gel gem gen get gig gin gnu gob god goo got gov gum gun
gut guy gym gyp had hag hah ham has hat haw hay hem hen hep her hes hew hex hey hgt hid hie him hip his hit hob hoc
hod hoe hog hop hos hot how hrs hub hue hug huh hum hut hwy ice icy ids ifs iii ilk ill imp inc ind ink inn ins int
ion ire irk ism its ivy jab jag jam jar jaw jay jet jib jig job jog jot joy jug jut keg ken key kid kin kit lab lad
lag lam lap lat law lax lay lbs lea led lee leg lei let lib lid lie lii lip lit lix lob log lop lot low lox lug lvi
lxi lye mad man map mar mas mat maw max may med meg meh men mes met mew mfg mfr mid mil min mix mob mod mom moo mop
mos mow mpg mph mud mug mum nab nag nap nay neg net new nib nil nip nit nix nod non nor nos not now nth nub nun nut
oaf oak oar oat obj odd ode off oft ohm oho ohs oil old one ops opt orb orc ore our out ova owe owl own pad pal pan
pap par pas pat paw pay pct pea pee peg pen pep per pet pew pie pig pin pip pis pit pkg ply pod poi pol pop pot pox
pro pry pub pug pun pup pus put pwn pyx qua rag ram ran rap rat raw ray red ref rep rev rho rib rid rig rim rip rob
rod roe rot row rpm rps rte rub rue rug rum run rut rye sac sad sag sap sat saw sax say sea sec see set sew sex she
shy sic sim sin sip sir sis sit six ski sky sly sob sod sol son sop sos sot sow sox soy spa spy sty sub sue sum sun
sup tab tad tag tam tan tap tar tat tax tbs tea tee tel ten the tho thy tic tie tin tip tit toe tog tom ton too top
tor tot tow toy try tsp tub tug tun tux two ugh ump ups urn use van var vat vet vex via vie vii vim viz vol vow wad
wag wan war was wax way web wed wee wen wet who why wig win wit wiz woe wok won woo wot wow wry xci xii xiv xix xor
xvi xxi xxv xxx yak yam yap yaw yea yen yep yes yet yew yip yon you yrs yuk yum yup zap zed zen zip zit zoo""".split())
READ_WORD = re.compile(r"[A-Za-z]+(?:['’][a-z]+)?")
READ_MIN = 3
READ_TWO_OFF = 6
READ_THREE_OFF = 9


def shared_start(a: str, b: str) -> int:
    return next((at for at, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


# Heavier slips ("claed", "cleoed", "hnaddd"): a lower-case word that is no English word, with the first and last letter of a word
# the reader is looking for and at most two letters off it, is that word.
SLIP_MIN = 5
SLIP_WORD = re.compile(r"(?<![\w'@./-])[a-z]{5,12}(?![\w'@/-]|\.\w)")
STATE_WORDS = frozenset("""started underway quoted approved cleared authorised authorized paused stalled frozen suspended corrected revised amended
moving delivered shipped fulfilled closed finished complete completed cancelled canceled scrapped dropped abandoned withdrawn planned booked reserved
secured confirmed definite postponed delayed deferred rebooked moved rescheduled disputed contested challenged settled resolved sorted agreed""".split())


def slipped_to(word: str, words: frozenset[str]) -> list[str]:
    # The words it may stand for, nearest first; equally near words are all named.
    if len(word) < SLIP_MIN or word in WORDS or word in NOTE_WORDS or word in SHORT_WORDS:
        return []
    near = sorted((letters_off(word, candidate), candidate) for candidate in words if candidate[0] == word[0] and candidate[-1] == word[-1] and letters_off(word, candidate) <= 2)
    return [candidate for off, candidate in near if off == near[0][0]]


def read_slips(text: str, words: frozenset[str]) -> str:
    return SLIP_WORD.sub(lambda found: next(iter(slipped_to(found.group(0), words)), found.group(0)), text)


@lru_cache(maxsize=4096)
def read_word(low: str) -> str:
    if low in WORDS or low in READING_WORDS or low in SHORT_WORDS or len(low) < READ_MIN or "'" in low or "’" in low:
        return low
    limit = 2 if len(low) >= READ_TWO_OFF else 1
    # Two letters off is read only in a longer word that keeps its first and last letter: other words that far off are names.
    near = [(letters_off(low, word, limit), word) for word in READING_WORDS if word[0] == low[0] and abs(len(word) - len(low)) <= limit]
    near = [(off, word) for off, word in near if off == 1 or (off == 2 and word[-1] == low[-1])]
    near = [(off, -shared_start(low, word), -len(word), word) for off, word in near if off <= limit]
    if not near:
        return low
    near.sort()
    # Equally near words give no reading: the message stays as written.
    return near[0][3] if len(near) == 1 or near[0][:3] != near[1][:3] else low


@lru_cache(maxsize=4096)
def read_form(text: str) -> str:
    def fix(match: re.Match[str]) -> str:
        word = match.group(0)
        inside = match.start() > 0 and not re.search(r"(?:^|[.?!:;—–-])\s*$", text[: match.start()])
        if word[0].isupper() and inside:
            return word
        meant = read_word(word.lower())
        if meant == word.lower():
            return word
        return meant.capitalize() if word[0].isupper() else meant
    return READ_WORD.sub(fix, text)


@lru_cache(maxsize=4096)
def read_request_word(low: str) -> str:
    # For the choice of a tool note only, where a word misread costs no answer: swapped letters count first, then the word of
    # the nearest letters and length; a long word may be three off when nearly the same letters are there, moved about.
    if low in WORDS or low in READING_WORDS or low in SHORT_WORDS or len(low) < READ_MIN or "'" in low or "’" in low:
        return low
    limit = 3 if len(low) >= READ_THREE_OFF else 2 if len(low) >= READ_TWO_OFF else 1
    near = [(letters_off(low, word, limit), word) for word in READING_WORDS if word[0] == low[0] and abs(len(word) - len(low)) <= limit]
    near = [(off, word) for off, word in near if off == 1 or (off <= limit and word[-1] == low[-1])]
    near = [(off, sum((Counter(low) - Counter(word)).values()), abs(len(word) - len(low)), -shared_start(low, word), word) for off, word in near if off <= limit]
    near = sorted(row for row in near if row[0] < 3 or row[1] <= 1)
    if not near:
        return low
    return near[0][4] if len(near) == 1 or near[0][:4] != near[1][:4] else low


def read_request(text: str) -> str:
    def fix(match: re.Match[str]) -> str:
        word = match.group(0)
        inside = match.start() > 0 and not re.search(r"(?:^|[.?!:;—–-])\s*$", text[: match.start()])
        if word[0].isupper() and inside:
            return word
        meant = read_request_word(word.lower())
        if meant == word.lower():
            return word
        return meant.capitalize() if word[0].isupper() else meant
    return READ_WORD.sub(fix, text)


def word_pairs(text: str) -> list[tuple[str, str]]:
    words = PAIR_WORD.findall(text.lower())
    return list(zip(words, words[1:]))


class SpellingKey:
    def __init__(self, corpus: list[str]) -> None:
        self.seen: Counter[str] = Counter(word for text in corpus for word in KEY_WORD.findall(text))
        self.used = [word for word in self.seen if (word in WORDS or word in NOTE_WORDS)]
        # Words the dictionary lacks but the notes keep writing ("headcount") count as words in the two-letter reading.
        self.common = [word for word, times in self.seen.items() if times >= KEY_SEEN]
        self.pairs: Counter[tuple[str, str]] = Counter(pair for text in corpus for pair in word_pairs(text))

    def meant(self, word: str) -> str:
        if (word in WORDS or word in NOTE_WORDS) or word in SHORT_WORDS or self.seen[word] > KEY_TYPO_TIMES:
            return ""
        near = (edits(word) & WORDS) - {word}
        used = [candidate for candidate in near if self.seen[candidate]]
        # A rare word one letter off ("cleoed": clewed) gives way to the status word it was meant for.
        if not used and (state := slipped_to(word, STATE_WORDS)):
            return " or ".join(state[:2])
        if used:
            # Two words the notes use could be meant ("cyat": coat, chat): both are named and the sentence decides.
            first, *rest = sorted(used, key=lambda candidate: (-self.seen[candidate], candidate))
            return f"{first} or {rest[0]}" if rest else first
        if len(near) == 1:
            return next(iter(near))
        if near or len(word) < KEY_SHORT:
            return ""
        # Two letters off ("rviesed", "hnafed"): the word the notes use most among those that close, when one clearly leads.
        scored = sorted(((self.seen[candidate], candidate) for candidate in self.common if candidate[0] == word[0] and letters_off(word, candidate) <= 2), reverse=True)
        if scored:
            return " or ".join(candidate for _, candidate in scored[:2])
        if len(word) < KEY_LONG:
            return ""
        close = sorted(((difflib.SequenceMatcher(None, word, candidate).ratio(), candidate) for candidate in self.used if candidate[0] == word[0] and abs(len(candidate) - len(word)) <= 2), reverse=True)
        if close and close[0][0] >= KEY_LONG_RATIO and (len(close) == 1 or close[1][0] < close[0][0]):
            return close[0][1]
        return ""

    def slipped(self, before: str, word: str, after: str) -> str:
        # A real word typed for another ("the sire visit", "by chit"): that one pair of words is written once in the notes,
        # and the same pair with one letter changed many times.
        if len(word) < KEY_SLIP_MIN or self.seen[word] > 1 or word in SHORT_WORDS:
            return ""
        best, most = "", 0
        for candidate in (edits(word) & self.seen.keys()) - {word}:
            # "decide" beside "decided" is the same word in another form, not one typed for the other.
            if candidate not in WORDS or candidate.startswith(word) or word.startswith(candidate):
                continue
            for kept, wrote, other in ((before, (before, word), (before, candidate)), (after, (word, after), (candidate, after))):
                if kept and self.pairs[wrote] == 1 and self.pairs[other] > most and self.pairs[other] >= KEY_SLIP_TIMES:
                    best, most = candidate, self.pairs[other]
        return best


    def lines(self, texts: list[str]) -> str:
        pairs: dict[str, str] = {}
        for text in texts:
            for word in KEY_WORD.findall(text):
                if word not in pairs and len(pairs) < KEY_MAX and (meant := self.meant(word)):
                    pairs[word] = meant
            words = PAIR_WORD.findall(text.lower())
            # A word written with a capital in the passage is a name ("Kaelynn Knight"), not another word mistyped.
            names = {found.lower() for found in CAPITALISED.findall(text)}
            for at, word in enumerate(words):
                if word not in names and word not in pairs and len(pairs) < KEY_MAX and (meant := self.slipped(words[at - 1] if at else "", word, words[at + 1] if at + 1 < len(words) else "")):
                    pairs[word] = meant
        if not pairs:
            return ""
        return SPELLING_KEY_HEADER + "\n" + "\n".join(f"- {typo} = {word}" for typo, word in pairs.items())
