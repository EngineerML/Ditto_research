#include "lane.hpp"

#include <algorithm>
#include <cctype>
#include <map>
#include <regex>
#include <sstream>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace ditto {
namespace {

using Words = std::unordered_set<std::string>;

Words word_set(const char* space_separated) {
    Words out;
    std::istringstream stream(space_separated);
    for (std::string word; stream >> word;) out.insert(word);
    return out;
}

const Words kGenericNames = word_set(
    "search create set list run execute get file read main chat for team status in save update delete send discover");
const Words kReadSynonyms = word_set(
    "task tasks queue queued automatic scheduled app feature features option options setting settings control switch help calendar web online internet");
const Words kDoVerbs = word_set(
    "make set change switch use create build run start kick dispatch send email mail schedule put add delete remove forget bin update save search find look pull open read draw generate edit tweak file report check plan split turn spin fetch research see forward pass shoot grab crunch compute normalize calculate take list summarize summarise brighten adjust enable disable move retry try apply execute reason skip describe paint outline talk google browse book crop warm resize convert post launch trigger sort begin proceed handle deploy refactor scrape rework touch bump explain break correct fix");
const Words kFramingVerbs = word_set(
    "use read look see find search pull open fetch grab take apply list skip google browse research summarize summarise describe explain reason talk compute normalize calculate crunch handle try");
const Words kNonVerbs = word_set(
    "my our i i'm i've we the a an this that these those it its one for on in at when if what which who where how why did do does is are was were will would could can should has have had thanks hey hi ok okay so yes no ditto");
const Words kSpeechVerbs = word_set("answer reply respond say state name tell give word phrase");
const Words kCommonWords = word_set(
    "email emails there their theirs these those where three getting letting reference references planned plans phone phones price prices thing things month months meant means");
const Words kFetchVerbs = word_set("search find look fetch pull open grab read research see browse google");
const Words kRecordNouns = word_set("thread account invoice balance record records");
const Words kDetailNouns = word_set(
    "email emails e-mail address addresses phone phones telephone handle handles username usernames");
const Words kVerbLikeNouns = word_set("handle handles address email");
const Words kVerbLeads = word_set("will would can could should to they we i you must");
const Words kWriteVerbs = word_set(
    "create delete remove clear update change set send forward save add bin forget edit make schedule book put move run start dispatch post cancel rename replace fix define build draft write");
const Words kSendingVerbs = word_set("email mail text message");
const Words kVerbSlotLeads = word_set("and then also please to now just kindly");
const Words kLeadPointers = word_set("i me it this that these those");
const Words kPossessionModifiers = word_set("current latest present own usual");
const Words kStopwords = word_set(
    "a an the and or but if then else of to in on at by for with about from into over after before during between under without within "
    "i me my mine we our you your yours he him his she her hers they them their it its this that these those what which who whom whose where when why how "
    "is are was were be been being am do does did done have has had having can could should would will shall may might must "
    "not no yes so as than too very just only also still again ever never now then here there once twice "
    "please tell give remind remember recall know think say said mention mentioned told ask asked need want like "
    "get got use used using find found look looked back go went come came make made take took keep kept "
    "one two three first last next current currently latest actually really exactly right ago earlier later up down out off "
    "that's what's i'm i've you're don't doesn't didn't isn't aren't can't won't let's ok okay hey hi hello thanks thank "
    "which should now mean began around conversation talking going did much many how long far whole altogether everything anything something "
    "already any every per here ll re ve");
const Words kSentenceStart = word_set(
    "What Which Who Where When How Why Give Remind Think Remember Before After Looking For Can Did Work Read Answer Please "
    "Quick Checking Sorting Just Note Tell Find Search Look Use Set Switch Change Make Put Add Run Start Kick Time Go Have Send See Two Real Oh Hey "
    "The This That These Those Our My Your And But Or So If Then Also Once Again Now Later Earlier Here There Yes No Not Update Side Random Off One "
    "Notes Adding Recorded Noted Logged Kept Tracked Understood Got Nice Thanks Subject From Pasted Everyone Back Contact Handoff "
    "Ignore Treat When Against Do Assume Local Within Separately Eventually Lovely Perfect Underneath Meanwhile");

const std::regex kWord(R"rx([A-Za-z][A-Za-z'\-]*)rx");
const std::regex kRetrievalWord(R"rx([A-Za-z0-9][A-Za-z0-9']*)rx");
const std::regex kClauseSplit(R"rx([;—–]|\s-\s|,\s*(?:and|but|then|so)\s+|\b(?:and then|then)\b|\.\s+|\?\s+)rx");
const std::regex kPartSplit(R"rx([,:])rx");
const std::regex kQuestionTail(R"rx([^.!?]*\?)rx");
const std::regex kQuestion(R"rx(\?\s*$|^\s*(?:what|which|who|whom|whose|where|when|how|why|did|do|does|is|are|was|were|will|would|could|can|should|has|have|had)\b)rx", std::regex::icase);
const std::regex kVerbInitial(R"rx(^\s*(?:(?:hey|hi|hello|ok|okay|so|well|thanks|also)[,:\-—\s]*)*(?:please\s+|kindly\s+|just\s+|go ahead and\s+|now\s+|actually\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?([a-z]+)\b)rx", std::regex::icase);
const std::regex kLiveCues(R"rx(\b(latest|current(?:ly)?|right now|at (?:\w+ )?now|up[- ]to[- ]date|live|online|the web|news|today'?s?|nowadays|these days|changed since|actually changed|what'?s new)\b)rx", std::regex::icase);
const std::regex kArithmetic(R"rx(\b(percent|percentage|sum|average|mean|total|times|minus|plus|split|divide|divided|compound|spread|multiply|normalize|fractions?|tip|median|crunch|calc(?:ulation)?)\b)rx", std::regex::icase);
const std::regex kDateSpan(R"rx(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|\b(?:19|20)\d{2}\b|\b\d{1,2}:\d{2}\s*(?:am|pm)?\b)rx", std::regex::icase);
const std::regex kSaveForm(R"rx(^\s*(?:please\s+)?(?:remember|note|keep in mind|bear in mind|make a note|jot down)\s+(?:that|to|this|for later|:))rx", std::regex::icase);
const std::regex kSaveWide(R"rx(^\s*(?:please\s+)?(?:remember|note|log|record)\s*(?:that|to|this|it|them|for later|:|\.|$)|^\s*(?:please\s+)?(?:keep|bear)\s+(?:that|this|it|them)?\s*in\s+min)rx", std::regex::icase);
const std::regex kNeedForm(R"rx(\b(i need|i want|i'd like|i would like)\s+(?:you to\s+|it\s+|that\s+|this\s+|the \w+\s+|a \w+\s+)?(\w+))rx", std::regex::icase);
const std::regex kNegatedOpener(R"rx(^\s*(?:do|does|did|is|are|was|were|will|would|could|can|should|has|have|had)(?:\s+not|n't)\b)rx", std::regex::icase);
const std::regex kQuestionWord(R"rx(\b(?:what|what'?s|which|who|who'?s|whom|whose|where|where'?s|when|why|how)\b)rx", std::regex::icase);
const std::regex kRequestForm(R"rx(\b(?:can|could|would|will|shall)\s+(?:i|you|we)\b)rx", std::regex::icase);
const std::regex kRecallQuestion(R"rx(^\s+me\s+(?:again\s+)?how\s+(?:long|many|much)\b)rx", std::regex::icase);
const std::regex kPoliteRequest(R"rx(^\s*(?:can|could|would|will)\s+you\s+(?:please\s+)?([a-z]+)\b)rx", std::regex::icase);
const std::regex kCausative(R"rx(^\s*(?:please\s+)?(?:have|get)\s+((?:[a-z']+\s+){1,3}[a-z']+))rx", std::regex::icase);
const std::regex kOutsideSource(R"rx(\b(?:web|online|internet|google|browse|news|look (?:it|this|that) up)\b)rx", std::regex::icase);
const std::regex kLeadIn(R"rx(^\s*([^:?!.;]{1,60}):\s+)rx");
const std::regex kStatementSubject(R"rx(^\s*(?:(?:also|by the way|fyi|note)[,:\-—\s]*)?(?:my|our|i|i'm|i am|i've|i'd|we|we're|for (?:long|short|my|our|the|work|client|everyday|daily|any)|when i|whenever i|on (?:my|our)|in (?:my|our)|ditto should|you should)\b)rx", std::regex::icase);
const std::regex kPossessed(R"rx(\b(?:my|our)\s+((?:[a-z]+\s+){0,2}[a-z]+))rx", std::regex::icase);
const std::regex kNameWord(R"rx(\b[A-Z][a-z]{2,}\b)rx");
const std::regex kCapitalized(R"rx(\b[A-Z][a-z]{2,}\b)rx");
const std::regex kLower(R"rx(\b[a-z]{3,}\b)rx");
const std::regex kEmail(R"rx([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})rx");
const std::regex kAlnumWord(R"rx(\b[0-9a-z]+\b)rx");

bool has(const Words& set, const std::string& word) { return set.find(word) != set.end(); }

bool effect_verb(const std::string& word) {
    return has(kDoVerbs, word) && !has(kFramingVerbs, word);
}

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

std::string strip(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n\f\v");
    if (first == std::string::npos) return "";
    const auto last = value.find_last_not_of(" \t\r\n\f\v");
    return value.substr(first, last - first + 1);
}

std::vector<std::string> regex_items(const std::string& text, const std::regex& expression) {
    std::vector<std::string> out;
    for (std::sregex_iterator it(text.begin(), text.end(), expression), end; it != end; ++it) {
        out.push_back(it->str());
    }
    return out;
}

std::vector<std::string> split(const std::string& text, const std::regex& expression) {
    std::vector<std::string> out;
    std::sregex_token_iterator it(text.begin(), text.end(), expression, -1), end;
    for (; it != end; ++it) out.push_back(it->str());
    return out;
}

std::vector<std::string> tokens(const std::string& text) {
    auto out = regex_items(text, kWord);
    for (auto& word : out) {
        word = lower(std::move(word));
        const auto first = word.find_first_not_of('\'');
        word = first == std::string::npos ? "" :
            word.substr(first, word.find_last_not_of('\'') - first + 1);
    }
    return out;
}

std::vector<std::string> retrieval_tokens(const std::string& text) {
    auto out = regex_items(text, kRetrievalWord);
    for (auto& word : out) {
        const bool title = std::isupper(static_cast<unsigned char>(word[0])) != 0;
        word = lower(std::move(word));
        const auto first = word.find_first_not_of('\'');
        word = first == std::string::npos ? "" :
            word.substr(first, word.find_last_not_of('\'') - first + 1);
        if (title && word.size() > 3 && word.ends_with("'s")) word.resize(word.size() - 2);
    }
    return out;
}

std::vector<std::string> clauses(const std::string& text) {
    std::vector<std::string> out;
    for (auto& clause : split(text, kClauseSplit)) if (!strip(clause).empty()) out.push_back(clause);
    if (out.empty()) out.push_back(text);
    return out;
}

std::vector<std::string> question_tails(const std::string& text) {
    return text.find('?') == std::string::npos ? std::vector<std::string>{} :
        regex_items(text, kQuestionTail);
}

bool search(const std::string& text, const std::regex& expression) {
    return std::regex_search(text, expression);
}

bool match_start(const std::string& text, const std::regex& expression,
                 std::smatch* captured = nullptr) {
    std::smatch result;
    const bool found = std::regex_search(text, result, expression,
                                         std::regex_constants::match_continuous);
    if (found && captured) *captured = result;
    return found;
}

std::string singular(const std::string& word) {
    return word.size() > 4 && word.ends_with('s') && !word.ends_with("ss") ?
        word.substr(0, word.size() - 1) : word;
}

bool within_one_edit(const std::string& a, const std::string& b) {
    if (a == b) return true;
    if (a.size() < 4 || (a.size() > b.size() ? a.size() - b.size() : b.size() - a.size()) > 1)
        return false;
    if (a.size() == b.size()) {
        std::vector<size_t> different;
        for (size_t i = 0; i < a.size(); ++i) if (a[i] != b[i]) different.push_back(i);
        return different.size() == 1 ||
            (different.size() == 2 && different[1] == different[0] + 1 &&
             a[different[0]] == b[different[1]] && a[different[1]] == b[different[0]]);
    }
    const auto& longer = a.size() > b.size() ? a : b;
    const auto& shorter = a.size() > b.size() ? b : a;
    for (size_t i = 0; i < longer.size(); ++i) {
        if (longer.substr(0, i) + longer.substr(i + 1) == shorter) return true;
    }
    return false;
}

std::vector<std::string> tool_names(const json& catalog) {
    std::vector<std::string> out;
    if (!catalog.is_array()) return out;
    for (const auto& item : catalog) {
        const auto name = json_string(item, "name");
        if (!name.empty()) out.push_back(name);
    }
    return out;
}

std::vector<std::string> name_parts(const std::string& name) {
    std::vector<std::string> out;
    std::istringstream stream(name);
    for (std::string part; std::getline(stream, part, '_');) out.push_back(part);
    return out;
}

struct Vocabulary {
    Words read;
    Words write;
};

Vocabulary vocabulary(const json& catalog) {
    Vocabulary result;
    for (const auto& name : tool_names(catalog)) {
        if (is_memory_read(name)) continue;
        Words& target = reads_state(name) ? result.read : result.write;
        for (const auto& part : name_parts(name)) {
            if (!has(kGenericNames, part) && part.size() > 2) target.insert(singular(part));
        }
    }
    result.read.insert(kReadSynonyms.begin(), kReadSynonyms.end());
    return result;
}

bool nearest(const std::string& word, const Words& vocab, bool lexicon = true) {
    const auto base = singular(word);
    if (has(vocab, base) || has(vocab, base + "s")) return true;
    if (base.size() < 5) return false;
    if (lexicon) {
        if (has(kCommonWords, base) || has(kCommonWords, word)) return false;
        for (const auto& common : kCommonWords) if (within_one_edit(base, common)) return false;
    }
    for (const auto& entry : vocab) {
        if (entry.size() >= 5 && within_one_edit(base, entry)) return true;
    }
    return false;
}

bool question_shape(const std::string& text) { return search(text, kQuestion); }

std::string verb_initial(const std::string& text, size_t* matched_end = nullptr) {
    std::smatch captured;
    if (!match_start(text, kVerbInitial, &captured)) return "";
    if (matched_end) *matched_end = static_cast<size_t>(captured.length());
    return lower(captured[1].str());
}

bool recall_question(const std::string& text) {
    size_t after = 0;
    if (verb_initial(text, &after) != "remind") return false;
    return match_start(text.substr(after), kRecallQuestion);
}

bool asks(const std::string& text, const std::vector<std::string>& split_clauses,
          bool wide, const std::vector<std::string>& tails) {
    if (question_shape(text) && !match_start(text, kNegatedOpener)) return true;
    if (wide && recall_question(text)) return true;
    if (text.find('?') == std::string::npos) return false;
    for (const auto& clause : split_clauses) if (question_shape(strip(clause))) return true;
    if (!wide) return false;
    for (const auto& tail : tails) {
        if (search(tail, kQuestionWord) && !search(tail, kRequestForm)) return true;
    }
    return false;
}

std::vector<std::string> verb_slots(const std::vector<std::string>& words) {
    std::vector<std::string> out;
    for (size_t i = 0; i < words.size(); ++i) {
        if (i == 0 || has(kVerbSlotLeads, words[i - 1])) out.push_back(words[i]);
    }
    return out;
}

bool framing_only(const std::string& clause, const std::vector<std::string>& words,
                  const Vocabulary& vocab, bool lexicon) {
    const auto verb = verb_initial(clause);
    if (!has(kFramingVerbs, verb) && !has(kSpeechVerbs, verb)) return false;
    for (const auto& word : verb_slots(words)) if (effect_verb(word)) return false;
    for (const auto& word : words) {
        if (nearest(word, vocab.read, lexicon) || nearest(word, vocab.write, lexicon)) return false;
    }
    return true;
}

bool record_anchor(const std::string& text) {
    for (const auto& word : tokens(text)) {
        const auto base = singular(word);
        if (has(kRecordNouns, base)) return true;
        if (base.size() >= 5) {
            for (const auto& noun : kRecordNouns) if (within_one_edit(base, noun)) return true;
        }
    }
    return false;
}

bool names_listed_tool(const std::string& text, const json& catalog) {
    const auto words = tokens(text);
    std::string joined = " ";
    for (const auto& word : words) joined += word + " ";
    for (const auto& name : tool_names(catalog)) {
        const auto parts = name_parts(lower(name));
        if (is_memory_read(name) || parts.size() < 2) continue;
        if (std::all_of(parts.begin(), parts.end(), [](const auto& part) {
                return has(kGenericNames, part);
            })) continue;
        std::string phrase = " ";
        for (const auto& part : parts) phrase += part + " ";
        if (joined.find(phrase) != std::string::npos) return true;
    }
    return false;
}

bool code_identifier(const std::string& text) {
    for (const auto& word : regex_items(lower(text), kAlnumWord)) {
        if (word.size() < 12) continue;
        const bool digit = std::any_of(word.begin(), word.end(), [](unsigned char c) {
            return std::isdigit(c) != 0;
        });
        const bool letter = std::any_of(word.begin(), word.end(), [](unsigned char c) {
            return std::islower(c) != 0;
        });
        if (digit && letter) return true;
    }
    return false;
}

bool asks_stored_detail(const std::string& text) {
    const auto words = tokens(text);
    if (code_identifier(text)) return false;
    for (const auto& word : words) if (has(kWriteVerbs, word)) return false;
    for (const auto& clause : split(text, kClauseSplit)) {
        const auto slots = verb_slots(tokens(clause));
        for (const auto& word : slots) if (has(kSendingVerbs, word)) return false;
    }
    for (size_t i = 0; i < words.size(); ++i) {
        const auto& word = words[i];
        if (has(kDetailNouns, word) &&
            !(has(kVerbLikeNouns, word) && i && has(kVerbLeads, words[i - 1]))) return true;
    }
    return false;
}

bool requests_action(const std::string& text) {
    std::smatch matched;
    if (match_start(text, kPoliteRequest, &matched) && has(kDoVerbs, lower(matched[1].str())))
        return true;
    if (match_start(text, kCausative, &matched)) {
        const auto words = tokens(matched[1].str());
        for (size_t i = 1; i < words.size(); ++i) if (has(kDoVerbs, words[i])) return true;
    }
    const auto parts = split(text, kPartSplit);
    for (size_t i = 1; i < parts.size(); ++i) {
        if (effect_verb(verb_initial(parts[i]))) return true;
    }
    return false;
}

std::string after_lead_in(const std::string& text) {
    std::smatch matched;
    if (!match_start(text, kLeadIn, &matched)) return "";
    const auto words = tokens(matched[1].str());
    if (words.empty() || words.size() > 4) return "";
    for (const auto& word : words) if (has(kLeadPointers, word)) return "";
    return text.substr(static_cast<size_t>(matched.length()));
}

bool states_own_fact(const std::string& text) {
    return match_start(text, kStatementSubject) ||
           match_start(after_lead_in(text), kStatementSubject);
}

std::string snap_spelling(const std::string& text, const std::vector<std::string>& cues,
                          size_t minimum) {
    std::string out;
    size_t previous = 0;
    for (std::sregex_iterator it(text.begin(), text.end(), kWord), end; it != end; ++it) {
        const auto& match = *it;
        out.append(text, previous, static_cast<size_t>(match.position()) - previous);
        const std::string word = match.str();
        const std::string folded = lower(word);
        std::string replacement = word;
        if (folded.size() >= minimum &&
            std::all_of(folded.begin(), folded.end(), [](unsigned char c) {
                return std::isalpha(c) != 0;
            }) && std::find(cues.begin(), cues.end(), folded) == cues.end()) {
            for (const auto& cue : cues) {
                if (within_one_edit(folded, cue)) {
                    replacement = cue;
                    break;
                }
            }
        }
        out += replacement;
        previous = static_cast<size_t>(match.position() + match.length());
    }
    out.append(text, previous, std::string::npos);
    return out;
}

bool verb_in(const std::string& text, const Words& verbs) {
    for (const auto& clause : split(text, kClauseSplit)) {
        if (strip(clause).empty()) continue;
        for (const auto& part : split(clause, kPartSplit)) {
            for (const auto& word : verb_slots(tokens(part))) if (has(verbs, word)) return true;
        }
    }
    return false;
}

bool acting(const std::string& text) { return verb_in(text, kDoVerbs); }
bool fetching(const std::string& text) { return verb_in(text, kFetchVerbs); }

bool effecting(const std::string& text) {
    Words effect;
    for (const auto& word : kDoVerbs) if (effect_verb(word)) effect.insert(word);
    return verb_in(text, effect);
}

bool reading_request(const std::string& text) {
    Words reading = kFramingVerbs;
    reading.insert(kSpeechVerbs.begin(), kSpeechVerbs.end());
    return verb_in(text, reading);
}

bool near_reading_tool(const std::string& text, const json& catalog) {
    Words words;
    for (const auto& name : tool_names(catalog)) {
        if (is_memory_read(name) || !reads_state(name)) continue;
        for (const auto& word : name_parts(name)) {
            if (!has(kGenericNames, word) && word.size() > 2) words.insert(singular(word));
        }
    }
    for (const auto& word : tokens(text)) if (nearest(word, words)) return true;
    return false;
}

struct WordIndex {
    std::unordered_map<std::string, int> df;
    std::unordered_map<std::string, int> lower_df;
    std::unordered_map<std::string, int> cap_df;
    std::vector<std::string> vocab;

    explicit WordIndex(const std::vector<MemoryPair>& pairs) {
        for (const auto& pair : pairs) {
            const std::string text = pair.prompt + "\n" + pair.response;
            const auto words = retrieval_tokens(text);
            for (const auto& word : Words(words.begin(), words.end())) ++df[word];
            const std::string without_emails = std::regex_replace(text, kEmail, " ");
            const auto lowers = regex_items(without_emails, kLower);
            for (const auto& word : Words(lowers.begin(), lowers.end())) ++lower_df[word];
            const auto caps = regex_items(text, kCapitalized);
            for (const auto& word : Words(caps.begin(), caps.end())) ++cap_df[lower(word)];
        }
        vocab.reserve(df.size());
        for (const auto& [word, count] : df) vocab.push_back(word);
        std::sort(vocab.begin(), vocab.end());
    }

    int frequency(const std::string& word) const {
        const auto it = df.find(word);
        return it == df.end() ? 0 : it->second;
    }

    std::string fix_typo(const std::string& word) const {
        if (frequency(word) || word.size() < 4 ||
            !std::all_of(word.begin(), word.end(), [](unsigned char c) {
                return std::isalpha(c) != 0;
            })) return word;
        std::string best = word;
        int best_df = 0;
        for (const int length : {static_cast<int>(word.size()) - 1,
                                 static_cast<int>(word.size()),
                                 static_cast<int>(word.size()) + 1}) {
            for (const auto& candidate : vocab) {
                if (static_cast<int>(candidate.size()) != length) continue;
                const int count = frequency(candidate);
                if (count > best_df && candidate != word && within_one_edit(word, candidate)) {
                    best = candidate;
                    best_df = count;
                }
            }
        }
        return best;
    }
};

bool unknown_name(const std::string& text, const WordIndex& index) {
    for (std::sregex_iterator it(text.begin(), text.end(), kNameWord), end; it != end; ++it) {
        const auto& match = *it;
        const std::string before = strip(text.substr(0, static_cast<size_t>(match.position())));
        if (before.empty()) continue;
        if (std::string(".?!:;-\"(").find(before.back()) != std::string::npos ||
            before.ends_with("—") || before.ends_with("–") || before.ends_with("“")) continue;
        if (has(kSentenceStart, match.str())) continue;
        if (!index.frequency(index.fix_typo(lower(match.str())))) return true;
    }
    return false;
}

bool held_in_records(const std::string& text, const json& catalog,
                     const WordIndex& index, const std::set<char>& kinds) {
    for (const char kind : {'e', 'c', 'q', 'n', 'i'}) if (kinds.contains(kind)) return true;
    if (kinds.contains('k') && kinds.contains('b')) return true;
    const Vocabulary vocab = vocabulary(catalog);
    for (std::sregex_iterator it(text.begin(), text.end(), kPossessed), end; it != end; ++it) {
        const auto phrase = tokens(lower((*it)[1].str()));
        bool capability = false;
        for (const auto& word : phrase) {
            if (has(kReadSynonyms, word) || nearest(word, vocab.read) || nearest(word, vocab.write)) {
                capability = true;
                break;
            }
        }
        if (capability) continue;
        for (const auto& word : phrase) {
            if (!has(kPossessionModifiers, word)) {
                if (word.size() >= 4 && !has(kStopwords, word) && index.frequency(word))
                    return true;
                break;
            }
        }
    }
    return false;
}

}  // namespace

bool reads_state(const std::string& name) {
    for (const std::string_view prefix : {"list_", "search_", "discover_", "read_",
                                          "get_", "fetch_", "find_", "lookup_"}) {
        if (name.starts_with(prefix)) return true;
    }
    return name.find("_search") != std::string::npos;
}

Lane classify_lane(const std::string& request, const json& catalog,
                   const LaneLevers& levers) {
    const Vocabulary vocab = vocabulary(catalog);
    const std::string cue_text = levers.typo_cues ?
        snap_spelling(request, {"latest", "current", "currently", "online", "today",
                                "nowadays", "right"}, 4) : request;
    const auto names = tool_names(catalog);
    const bool compute = std::find(names.begin(), names.end(), "run_code") != names.end();
    const auto split_clauses = clauses(request);
    const auto tails = question_tails(request);
    const bool question = asks(request, split_clauses, levers.route_asking, tails);
    std::string reason;
    for (const auto& clause : split_clauses) {
        const auto words = tokens(clause);
        if (levers.route_preamble && framing_only(clause, words, vocab, levers.route_lexicon))
            continue;
        const std::string verb = verb_initial(clause);
        const std::string trimmed = strip(clause);
        const bool verb_at_start = !verb.empty() && !has(kNonVerbs, verb) &&
            (trimmed.empty() || !trimmed.ends_with('?')) &&
            !(levers.route_asking && question_shape(trimmed));
        std::smatch need;
        const std::string need_verb = search(clause, kNeedForm) &&
            std::regex_search(clause, need, kNeedForm) ? lower(need[2].str()) : "";
        std::string action = has(kDoVerbs, verb) ? verb :
            (has(kDoVerbs, need_verb) ? need_verb : "");
        if (levers.route_preamble && question && has(kFramingVerbs, action)) {
            bool capability = false;
            for (const auto& word : words) {
                if (effect_verb(word) || nearest(word, vocab.read, levers.route_lexicon) ||
                    nearest(word, vocab.write, levers.route_lexicon)) {
                    capability = true;
                    break;
                }
            }
            if (!capability) action.clear();
        }
        if (match_start(clause, kSaveForm) ||
            (levers.route_save && match_start(clause, kSaveWide)) || !action.empty()) {
            if (reason.empty()) reason = "imperative";
        } else if (verb_at_start) {
            for (const auto& word : words) {
                if (nearest(word, vocab.write, levers.route_lexicon)) {
                    if (reason.empty()) reason = "imperative-setter";
                    break;
                }
            }
        }
        for (const auto& word : words) {
            if (levers.route_lexicon && verb_at_start && word == verb &&
                has(kReadSynonyms, word)) continue;
            if (nearest(word, vocab.read, levers.route_lexicon)) {
                if (reason.empty()) reason = "read-capability";
                break;
            }
        }
    }
    if (search(cue_text, kLiveCues) && !(levers.route_anchor && record_anchor(request))) {
        if (reason.empty()) reason = "live";
    }
    const std::string figures = levers.route_operands ?
        std::regex_replace(request, kDateSpan, " ") : request;
    const std::string arithmetic_text = levers.typo_cues ?
        snap_spelling(request,
            {"percent", "percentage", "average", "divide", "divided",
             "compound", "spread", "multiply", "normalize", "fractions",
             "median", "crunch"}, 5) : request;
    if (compute && search(arithmetic_text, kArithmetic) &&
        search(figures, std::regex(R"rx(\d)rx"))) {
        if (reason.empty()) reason = "arithmetic";
    }
    if (names_listed_tool(request, catalog) && reason.empty()) reason = "names-tool";
    if ((reason == "live" || reason == "read-capability" || reason == "imperative" ||
         reason == "imperative-setter") && asks_stored_detail(request))
        return {"records", "stored-detail"};
    if (!reason.empty()) return {"action", reason};
    if (requests_action(request)) return {"action", "request"};
    if (!question && states_own_fact(request)) return {"records", "statement"};
    if (question) return {"records", "question"};
    if (levers.route_asking && !tails.empty()) {
        bool request_tail = false;
        for (const auto& tail : tails) if (search(tail, kRequestForm)) request_tail = true;
        if (!request_tail) return {"records", "asked"};
    }
    if (asks_stored_detail(request)) return {"records", "stored-detail"};
    return {"action", "default"};
}

bool own_records_question(const std::string& request, const json& catalog) {
    if (search(request, kOutsideSource) || names_listed_tool(request, catalog) ||
        (fetching(request) && near_reading_tool(request, catalog))) return false;
    return (asks(request, clauses(request), true, question_tails(request)) ||
            reading_request(request)) && !effecting(request);
}

bool about_own_records(const std::string& request, const json& catalog,
                       const Lane& lane, const std::vector<MemoryPair>& pairs,
                       const std::set<char>& anchor_kinds) {
    if (lane.name != "action" || lane.reason != "live" || search(request, kOutsideSource))
        return false;
    if (!asks(request, clauses(request), true, question_tails(request)) || acting(request))
        return false;
    const WordIndex index(pairs);
    if (unknown_name(request, index)) return false;
    // Pass the retriever's exact question anchors even
    // when that set is empty.  A substring reconstruction here can fabricate
    // a quoted/name anchor ("opal path" inside "opal pathway") and change
    // the lane from live action to stored records.
    return held_in_records(request, catalog, index, anchor_kinds);
}

Lane refine_lane(const Lane& initial, const std::string& request,
                 const json& catalog, bool focus,
                 const std::vector<MemoryPair>& pairs,
                 const std::set<char>& anchor_kinds, bool short_route) {
    if (initial.name == "records") return initial;
    if (initial.reason == "live" && focus) return {"records", "identifier"};
    if (short_route && focus && own_records_question(request, catalog))
        return {"records", "identifier-held"};
    if (initial.reason == "live" &&
        about_own_records(request, catalog, initial, pairs, anchor_kinds))
        return {"records", "own-records"};
    return initial;
}

}  // namespace ditto
