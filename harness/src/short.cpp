#include "short.hpp"
#include "output.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <map>
#include <numeric>
#include <regex>
#include <set>
#include <sstream>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace ditto {
namespace {

constexpr int kProgramMaxRecordChars = 2000;
constexpr int kLeadMaxStatementChars = 1000;
constexpr int kShortRecordChars = 400;
constexpr int kMinDenseNotes = 3;
constexpr int kMinThreadNotes = 2;
constexpr int kMaxPhraseWords = 6;
constexpr int kRecurMaxWords = 40;
constexpr int kRecurExtraWords = 6;
constexpr int kRecurTimes = 2;
constexpr double kRecurShare = 0.8;
constexpr const char* kOperatorSeam =
    "Operator instructions (from the product operator; where they conflict with anything above, they take precedence):";
constexpr const char* kShortOpening =
    "You are Ditto, the user's assistant with long-term memory. Answer the message from the user's saved notes below.";
constexpr const char* kProgramEnding =
    " Reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the notes put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '. Write any date in full, with day, month and year. If the notes do not state it, say so.";
constexpr const char* kNotesTogether =
    "Read every note before answering. When several notes speak of the same person, thread or reference, read them together, with their dates, before deciding what holds now.";
constexpr const char* kOrderSystem =
    "You read a user's saved notes and put them in the order the things they describe must have happened. Do not answer anything else.";
constexpr const char* kOrderTail =
    "\n\nThe notes above are listed in no particular order. Judging from their words, put them in the order the things they describe happened: a note that refers back to an earlier state of the same thing comes after the note that set that state. Reply with one line: the marks in that order, separated by commas.";
constexpr const char* kLeadHeader =
    "The statements of the notes below, in the order an earlier reading of their words put them:";
constexpr const char* kRecentHeader =
    "Picked out by code from the dates of the notes and the order of the passages within each note, leaving out passages that recur almost word for word in the notes about other things; not checked — the notes above decide wherever they differ:";

std::size_t codepoints(const std::string& text) {
    std::size_t count = 0;
    for (unsigned char c : text) if ((c & 0xc0) != 0x80) ++count;
    return count;
}

std::string lower_ascii(std::string text) {
    for (char& c : text) if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    return text;
}

std::string trim(const std::string& text) {
    std::size_t first = 0, last = text.size();
    while (first < last && std::isspace(static_cast<unsigned char>(text[first]))) ++first;
    while (last > first && std::isspace(static_cast<unsigned char>(text[last - 1]))) --last;
    return text.substr(first, last - first);
}

std::string join(const std::vector<std::string>& parts, const std::string& separator) {
    std::string out;
    for (const auto& part : parts) {
        if (!out.empty()) out += separator;
        out += part;
    }
    return out;
}

std::vector<std::string> identifiers(const std::string& text) {
    static const std::regex pattern(R"(\b(?=[0-9a-z]*[0-9])(?=[0-9a-z]*[a-z])[0-9a-z]{12,}\b)");
    const std::string lowered = lower_ascii(text);
    std::vector<std::string> out;
    for (std::sregex_iterator it(lowered.begin(), lowered.end(), pattern), end; it != end; ++it)
        out.push_back(it->str());
    return out;
}

std::vector<std::string> tokens(const std::string& text) {
    std::vector<std::string> out;
    for (std::size_t i = 0; i < text.size();) {
        if (!std::isalnum(static_cast<unsigned char>(text[i]))) { ++i; continue; }
        const bool capped = std::isupper(static_cast<unsigned char>(text[i])) != 0;
        std::string word;
        while (i < text.size()) {
            const unsigned char c = static_cast<unsigned char>(text[i]);
            if (std::isalnum(c) || c == '\'') { word.push_back(static_cast<char>(c)); ++i; }
            else if (i + 2 < text.size() && text.compare(i, 3, "’") == 0) {
                word.push_back('\''); i += 3;
            } else break;
        }
        while (!word.empty() && word.back() == '\'') word.pop_back();
        word = lower_ascii(word);
        if (capped && word.size() > 3 && word.ends_with("'s")) word.resize(word.size() - 2);
        if (!word.empty()) out.push_back(std::move(word));
    }
    return out;
}

const std::unordered_set<std::string>& stopwords() {
    static const std::unordered_set<std::string> words = [] {
        std::istringstream in(R"(a an the and or but if then else of to in on at by for with about from into over after before during between under without within i me my mine we our you your yours he him his she her hers they them their it its this that these those what which who whom whose where when why how is are was were be been being am do does did done have has had having can could should would will shall may might must not no yes so as than too very just only also still again ever never now then here there once twice please tell give remind remember recall know think say said mention mentioned told ask asked need want like get got use used using find found look looked back go went come came make made take took keep kept one two three first last next current currently latest actually really exactly right ago earlier later up down out off that's what's i'm i've you're don't doesn't didn't isn't aren't can't won't let's ok okay hey hi hello thanks thank which should now mean began around conversation talking going did much many how long far whole altogether everything anything something already any every per here ll re ve)");
        std::unordered_set<std::string> out;
        std::string word;
        while (in >> word) out.insert(word);
        return out;
    }();
    return words;
}

std::string collapse_space(const std::string& text) {
    std::string out;
    bool gap = false;
    for (unsigned char c : text) {
        if (std::isspace(c)) gap = !out.empty();
        else {
            if (gap) out.push_back(' ');
            gap = false;
            out.push_back(static_cast<char>(c));
        }
    }
    return out;
}

std::string strip_edges(std::string text) {
    static const std::string ascii = " \t\r\n:;.,-|\"'`";
    static const std::vector<std::string> unicode = {"–", "—", "“", "”", "‘", "’"};
    bool changed = true;
    while (changed && !text.empty()) {
        changed = false;
        if (!text.empty() && ascii.find(text.front()) != std::string::npos) {
            text.erase(text.begin()); changed = true;
        }
        if (!text.empty() && ascii.find(text.back()) != std::string::npos) {
            text.pop_back(); changed = true;
        }
        for (const auto& edge : unicode) {
            if (text.starts_with(edge)) { text.erase(0, edge.size()); changed = true; }
            if (text.ends_with(edge)) { text.resize(text.size() - edge.size()); changed = true; }
        }
    }
    return text;
}

std::string statement(const MemoryPair& pair, const std::string& token) {
    const std::size_t at = lower_ascii(pair.prompt).find(token);
    const std::string body = at == std::string::npos ? pair.prompt : pair.prompt.substr(at + token.size());
    return strip_edges(collapse_space(body));
}

std::vector<std::vector<MemoryPair>> by_statement(std::vector<MemoryPair> records,
                                                   const std::string& token) {
    std::sort(records.begin(), records.end(), [](const auto& a, const auto& b) {
        return std::tie(a.timestamp, a.pair_id) < std::tie(b.timestamp, b.pair_id);
    });
    std::unordered_map<std::string, std::size_t> positions;
    std::vector<std::vector<MemoryPair>> groups;
    for (const auto& pair : records) {
        const std::string key = statement(pair, token);
        auto [it, inserted] = positions.emplace(key, groups.size());
        if (inserted) groups.emplace_back();
        groups[it->second].push_back(pair);
    }
    return groups;
}

std::vector<std::size_t> by_text(const ShortProgram& program) {
    std::vector<std::size_t> indexes(program.groups.size());
    std::iota(indexes.begin(), indexes.end(), 0);
    std::stable_sort(indexes.begin(), indexes.end(), [&](std::size_t a, std::size_t b) {
        return lower_ascii(statement(program.groups[a].front(), program.token)) <
               lower_ascii(statement(program.groups[b].front(), program.token));
    });
    return indexes;
}

std::string record_block(std::size_t mark, const MemoryPair& pair) {
    const std::string head = "[M" + std::to_string(mark) + "]" +
                             (pair.timestamp.empty() ? "" : " " + pair.timestamp.substr(0, 10));
    return head + "\nUser: " + pair.prompt + "\nAssistant: " + pair.response;
}

std::string system_with_operator(const std::string& own, const std::string& operator_prompt) {
    const std::string operator_text = trim(operator_prompt);
    return operator_text.empty() ? own : own + "\n\n" + kOperatorSeam + "\n" + operator_text;
}

std::string program_system(bool full_dates) {
    std::string own = std::string(kShortOpening) + kProgramEnding;
    if (full_dates) {
        const std::string before = "with day, month and year.";
        const auto at = own.find(before);
        if (at != std::string::npos) own.replace(at, before.size(),
            "with day, month and year, even when the message asks for less.");
    }
    return own;
}

std::string topic_system() {
    return std::string(kShortOpening) + " " + kNotesTogether + kProgramEnding;
}

std::vector<std::string> paragraphs(const std::string& text) {
    static const std::regex paragraph_break(R"(\n\s*\n)");
    std::vector<std::string> parts;
    for (std::sregex_token_iterator it(text.begin(), text.end(), paragraph_break, -1), end; it != end; ++it) {
        const std::string part = trim(it->str());
        if (!part.empty()) parts.push_back(part);
    }
    return parts;
}

std::vector<MemoryPair> by_date(std::vector<MemoryPair> notes);
bool whole_word(const std::string& text, const std::string& word);

std::vector<std::string> full_names(const std::string& text,
                                    const std::vector<MemoryPair>& corpus) {
    static const std::regex pattern(R"(\b([A-Z][a-z]+ [A-Z][a-z]+)\b)");
    std::vector<std::string> names;
    for (std::sregex_iterator it(text.begin(), text.end(), pattern), end; it != end; ++it) {
        const std::string name = (*it)[1].str();
        if (std::find(names.begin(), names.end(), name) != names.end()) continue;
        if (std::any_of(corpus.begin(), corpus.end(), [&](const auto& pair) {
                return codepoints(pair.prompt) < kShortRecordChars && pair.prompt.find(name) != std::string::npos;
            })) names.push_back(name);
    }
    return names;
}

std::vector<MemoryPair> cards_for(const std::vector<std::string>& names,
                                  const std::vector<MemoryPair>& corpus) {
    static const std::regex alias_re(R"([“"]([A-Z][A-Za-z\-]{1,20})[.,]?[”"])");
    std::unordered_set<std::string> held;
    std::vector<MemoryPair> cards;
    for (const auto& name : names) {
        std::vector<MemoryPair> first;
        std::set<std::string> aliases;
        std::set<std::string> name_parts;
        std::istringstream name_words(name);
        std::string name_part;
        while (name_words >> name_part) name_parts.insert(name_part);
        for (const auto& pair : corpus) {
            if (codepoints(pair.prompt) >= kShortRecordChars ||
                pair.prompt.find(name) == std::string::npos) continue;
            first.push_back(pair);
            for (std::sregex_iterator it(pair.prompt.begin(), pair.prompt.end(), alias_re), end; it != end; ++it) {
                const std::string alias = (*it)[1].str();
                if (!name_parts.contains(alias)) aliases.insert(alias);
            }
        }
        std::set<std::string> first_ids;
        for (const auto& pair : first) {
            first_ids.insert(pair.pair_id);
            if (held.insert(pair.pair_id).second) cards.push_back(pair);
        }
        for (const auto& pair : corpus) {
            if (first_ids.contains(pair.pair_id) || codepoints(pair.prompt) >= kShortRecordChars) continue;
            if (std::any_of(aliases.begin(), aliases.end(), [&](const auto& alias) {
                    return whole_word(pair.prompt, alias);
                }) && held.insert(pair.pair_id).second) cards.push_back(pair);
        }
    }
    return by_date(std::move(cards));
}

int edits(const std::string& a, const std::string& b) {
    std::vector<std::vector<int>> rows(a.size() + 1, std::vector<int>(b.size() + 1));
    for (std::size_t i = 0; i <= a.size(); ++i) rows[i][0] = static_cast<int>(i);
    for (std::size_t j = 0; j <= b.size(); ++j) rows[0][j] = static_cast<int>(j);
    for (std::size_t i = 1; i <= a.size(); ++i) {
        for (std::size_t j = 1; j <= b.size(); ++j) {
            rows[i][j] = std::min({rows[i - 1][j] + 1, rows[i][j - 1] + 1,
                                    rows[i - 1][j - 1] + (a[i - 1] != b[j - 1])});
            if (i > 1 && j > 1 && a[i - 1] == b[j - 2] && a[i - 2] == b[j - 1])
                rows[i][j] = std::min(rows[i][j], rows[i - 2][j - 2] + 1);
        }
    }
    return rows[a.size()][b.size()];
}

int typo_budget(const std::string& word) {
    return word.size() <= 2 ? 0 : word.size() <= 5 ? 1 : 2;
}

bool typo_of(const std::string& word, const std::string& seen) {
    if (word == seen) return true;
    const int budget = typo_budget(word);
    return budget > 0 && std::abs(static_cast<int>(word.size()) - static_cast<int>(seen.size())) <= budget &&
           edits(word, seen) <= budget;
}

using WordSet = std::set<std::string>;
using Variants = std::unordered_map<std::string, WordSet>;

bool holds(const std::vector<std::string>& phrase, const std::vector<std::string>& words,
           const Variants& variants) {
    if (phrase.empty() || words.size() < phrase.size()) return false;
    for (std::size_t start = 0; start + phrase.size() <= words.size(); ++start) {
        bool matched = true;
        for (std::size_t k = 0; k < phrase.size(); ++k) {
            if (!variants.at(phrase[k]).contains(words[start + k])) { matched = false; break; }
        }
        if (matched) return true;
    }
    return false;
}

std::vector<MemoryPair> by_date(std::vector<MemoryPair> notes) {
    std::sort(notes.begin(), notes.end(), [](const auto& a, const auto& b) {
        return std::tie(a.timestamp, a.pair_id) < std::tie(b.timestamp, b.pair_id);
    });
    return notes;
}

bool whole_word(const std::string& text, const std::string& word) {
    std::size_t at = 0;
    auto boundary = [](unsigned char c) { return std::isalnum(c) || c == '_'; };
    while ((at = text.find(word, at)) != std::string::npos) {
        const auto end = at + word.size();
        if ((at == 0 || !boundary(static_cast<unsigned char>(text[at - 1]))) &&
            (end == text.size() || !boundary(static_cast<unsigned char>(text[end])))) return true;
        at = end;
    }
    return false;
}

std::vector<MemoryPair> thread_of(const std::string& question,
                                  const std::vector<MemoryPair>& notes,
                                  const std::vector<MemoryPair>& corpus) {
    static const std::regex alias_re(R"([“"]([A-Z][A-Za-z\-]{1,20})[.,]?[”"])");
    std::set<std::string> aliases;
    for (const auto& pair : corpus) {
        if (codepoints(pair.prompt) >= kShortRecordChars) continue;
        for (std::sregex_iterator it(pair.prompt.begin(), pair.prompt.end(), alias_re), end; it != end; ++it)
            aliases.insert((*it)[1].str());
    }
    std::vector<std::string> mentioned;
    for (const auto& alias : aliases) if (whole_word(question, alias)) mentioned.push_back(alias);
    if (mentioned.empty()) return notes;
    std::vector<MemoryPair> thread;
    int dense = 0;
    for (const auto& pair : notes) {
        if (std::any_of(mentioned.begin(), mentioned.end(), [&](const auto& alias) {
                return whole_word(pair.prompt, alias);
            })) {
            thread.push_back(pair);
            if (pair.prompt.find("\n\n") != std::string::npos) ++dense;
        }
    }
    return dense >= kMinThreadNotes ? thread : notes;
}

struct DatedPassage {
    std::string head;
    std::string text;
};

std::vector<DatedPassage> dated_passages(const TopicNotes& found,
                                         const std::map<std::string, std::string>& labels) {
    std::vector<DatedPassage> out;
    for (std::size_t i = 0; i < found.notes.size(); ++i) {
        const auto& pair = found.notes[i];
        const auto excerpt = found.excerpts.find(pair.pair_id);
        if (excerpt == found.excerpts.end()) continue;
        const auto label = labels.find(pair.pair_id);
        const std::string mark = label == labels.end() ? "M" + std::to_string(i + 1) : label->second;
        const std::string head = "[" + mark + "]" +
                                 (pair.timestamp.empty() ? "" : " " + pair.timestamp.substr(0, 10));
        for (const auto& text : paragraphs(excerpt->second)) out.push_back({head, text});
    }
    return out;
}

std::string passages_view(const TopicNotes& found,
                          const std::map<std::string, std::string>& labels = {}) {
    std::vector<std::string> parts;
    for (const auto& passage : dated_passages(found, labels))
        parts.push_back(passage.head + " " + passage.text);
    return "Passages that name “" + found.phrase + "”, copied from the notes below:\n\n" + join(parts, "\n\n");
}

std::map<WordSet, int> other_paragraphs(const TopicNotes& found,
                                       const std::vector<MemoryPair>& corpus) {
    std::set<std::string> held;
    for (const auto& pair : found.notes) held.insert(pair.pair_id);
    std::map<WordSet, int> out;
    for (const auto& pair : corpus) {
        if (held.contains(pair.pair_id)) continue;
        for (const auto& paragraph : paragraphs(pair.prompt)) {
            const auto words = tokens(paragraph);
            if (words.size() <= kRecurMaxWords) ++out[WordSet(words.begin(), words.end())];
        }
    }
    return out;
}

WordSet passage_shape(const std::string& text, const std::string& phrase) {
    const auto asked = tokens(phrase);
    WordSet shape;
    for (const auto& word : tokens(text)) {
        if (std::none_of(asked.begin(), asked.end(), [&](const auto& part) {
                return typo_of(part, word);
            })) shape.insert(word);
    }
    return shape;
}

int shared_words(const WordSet& shape, const WordSet& other) {
    int exact = 0;
    for (const auto& word : shape) if (other.contains(word)) ++exact;
    if (exact == static_cast<int>(shape.size())) return exact;
    std::vector<std::string> rest;
    for (const auto& word : other) if (!shape.contains(word)) rest.push_back(word);
    int near = 0;
    for (const auto& word : shape) {
        if (other.contains(word) || word.size() <= 4) continue;
        if (std::any_of(rest.begin(), rest.end(), [&](const auto& seen) { return typo_of(word, seen); })) ++near;
    }
    return exact + near;
}

bool recurs(const WordSet& shape, const std::map<WordSet, int>& others) {
    if (shape.empty()) return true;
    const double need = kRecurShare * static_cast<double>(shape.size());
    int times = 0;
    for (const auto& [other, seen] : others) {
        if (std::abs(static_cast<int>(other.size()) - static_cast<int>(shape.size())) > 2 * kRecurExtraWords)
            continue;
        int maximum = 0;
        for (const auto& word : shape) if (other.contains(word) || word.size() > 4) ++maximum;
        if (maximum < need) continue;
        const int shared = shared_words(shape, other);
        if (shared >= need && static_cast<int>(other.size()) - shared <= kRecurExtraWords) {
            times += seen;
            if (times >= kRecurTimes) return true;
        }
    }
    return false;
}

struct RecentPick {
    bool names_person = false;
    std::string passage;
};

std::vector<RecentPick> recent_picks(const TopicNotes& found,
                                    const std::vector<MemoryPair>& corpus,
                                    const std::map<std::string, std::string>& labels) {
    const auto passages = dated_passages(found, labels);
    if (passages.empty()) return {};
    const auto others = other_paragraphs(found, corpus);
    std::vector<DatedPassage> kept;
    for (const auto& passage : passages) {
        if (!recurs(passage_shape(passage.text, found.phrase), others)) kept.push_back(passage);
    }
    if (kept.empty()) kept = passages;
    const auto& last = kept.back();
    std::vector<RecentPick> picks = {{false, last.head + " " + last.text}};
    // Check the last passage for a full name too. A project title such
    // as "Orchid Delta" can satisfy that test, suppressing a second pick.
    if (!full_names(last.text, corpus).empty()) return picks;
    for (std::size_t i = kept.size() - 1; i-- > 0;) {
        if (!full_names(kept[i].text, corpus).empty()) {
            picks.push_back({true, kept[i].head + " " + kept[i].text});
            break;
        }
    }
    return picks;
}

std::string recent_view(const TopicNotes& found, const std::vector<MemoryPair>& corpus,
                        const std::map<std::string, std::string>& labels = {}) {
    const auto picks = recent_picks(found, corpus, labels);
    if (picks.empty()) return "";
    std::vector<std::string> lines;
    for (const auto& pick : picks) {
        lines.push_back(std::string("- The most recent passage about “") + found.phrase +
                        (pick.names_person ? "” that names a person: " : "”: ") + pick.passage);
    }
    return std::string(kRecentHeader) + "\n" + join(lines, "\n");
}

std::string record_view(const std::vector<MemoryPair>& notes) {
    std::vector<std::string> blocks;
    for (std::size_t i = 0; i < notes.size(); ++i) blocks.push_back(record_block(i + 1, notes[i]));
    return join(blocks, "\n\n");
}

}  // namespace

std::vector<Candidate> short_identifier_focus(const std::string& question,
                                               const std::vector<Candidate>& ordered) {
    for (const auto& token : identifiers(question)) {
        std::vector<Candidate> carrying;
        for (const auto& candidate : ordered) {
            if (lower_ascii(candidate.pair.prompt + " " + candidate.pair.response).find(token) != std::string::npos)
                carrying.push_back(candidate);
        }
        if (carrying.size() >= 3) {
            std::sort(carrying.begin(), carrying.end(), [](const auto& a, const auto& b) {
                return std::tie(a.pair.timestamp, a.pair.pair_id) <
                       std::tie(b.pair.timestamp, b.pair.pair_id);
            });
            return carrying;
        }
    }
    return {};
}

bool short_records(const std::vector<Candidate>& focus, int max_chars) {
    std::size_t total = 0;
    for (const auto& candidate : focus) {
        const std::size_t size = codepoints(candidate.pair.prompt) + codepoints(candidate.pair.response);
        if (size > kProgramMaxRecordChars) return false;
        total += size;
    }
    return max_chars >= 0 && total <= static_cast<std::size_t>(max_chars);
}

std::string focus_token(const std::string& question,
                        const std::vector<Candidate>& focus) {
    for (const auto& token : identifiers(question)) {
        if (!focus.empty() && std::all_of(focus.begin(), focus.end(), [&](const auto& candidate) {
                return lower_ascii(candidate.pair.prompt + " " + candidate.pair.response).find(token) != std::string::npos;
            })) return token;
    }
    return "";
}

bool ShortProgram::needs_order() const { return groups.size() >= 2; }

json ShortProgram::order_messages() const {
    if (!needs_order()) return json::array();
    std::vector<std::string> listed;
    const auto shuffled = by_text(*this);
    for (std::size_t i = 0; i < shuffled.size(); ++i) {
        listed.push_back("[M" + std::to_string(i + 1) + "]\nUser: " +
                         statement(groups[shuffled[i]].front(), token));
    }
    return json::array({{{"role", "system"}, {"content", kOrderSystem}},
                        {{"role", "user"}, {"content", join(listed, "\n\n") + kOrderTail}}});
}

std::optional<json> ShortProgram::answer_messages(const RunRequest& request,
                                                    const std::optional<std::string>& order_reply,
                                                    bool full_dates) const {
    std::vector<std::size_t> sequence;
    if (needs_order()) {
        if (!order_reply) return std::nullopt;
        const auto shuffled = by_text(*this);
        std::set<std::size_t> seen;
        static const std::regex marks(R"(\bM(\d+)\b)");
        for (std::sregex_iterator it(order_reply->begin(), order_reply->end(), marks), end; it != end; ++it) {
            std::size_t mark = 0;
            try { mark = static_cast<std::size_t>(std::stoull((*it)[1].str())); } catch (...) { continue; }
            if (mark >= 1 && mark <= shuffled.size() && seen.insert(mark - 1).second)
                sequence.push_back(shuffled[mark - 1]);
        }
        for (std::size_t i = 0; i < shuffled.size(); ++i)
            if (!seen.contains(i)) sequence.push_back(shuffled[i]);
    } else if (!groups.empty()) {
        sequence.push_back(0);
    }
    std::vector<std::string> blocks;
    std::vector<std::string> statements;
    std::size_t mark = 0;
    for (const auto index : sequence) {
        const auto& group = groups[index];
        statements.push_back(statement(group.front(), token));
        std::vector<std::string> lines;
        for (const auto& pair : group) lines.push_back(record_block(++mark, pair));
        blocks.push_back(join(lines, "\n"));
    }
    std::string lead;
    if (statements.size() >= 2 &&
        std::all_of(statements.begin(), statements.end(), [](const auto& text) {
            return codepoints(text) <= kLeadMaxStatementChars;
        })) {
        lead = std::string(kLeadHeader) + "\n";
        for (std::size_t i = 0; i < statements.size(); ++i)
            lead += (i ? "\n" : "") + std::to_string(i + 1) + ". " + statements[i];
        lead += "\n\n";
    }
    const std::string user = lead + "Saved notes:\n\n" + join(blocks, "\n\n") +
                             "\n\nMessage:\n" + request.user_input;
    return json::array({{{"role", "system"},
                         {"content", system_with_operator(program_system(full_dates), request.system_prompt)}},
                        {{"role", "user"}, {"content", user}}});
}

std::optional<ShortProgram> plan_short_program(const std::string& question,
                                                const std::vector<Candidate>& focus,
                                                int max_chars) {
    if (focus.empty() || !short_records(focus, max_chars)) return std::nullopt;
    const std::string token = focus_token(question, focus);
    if (token.empty()) return std::nullopt;
    std::vector<MemoryPair> records;
    for (const auto& candidate : focus) records.push_back(candidate.pair);
    return ShortProgram{token, by_statement(std::move(records), token)};
}

std::optional<TopicNotes> find_topic(const std::string& question,
                                    const std::vector<MemoryPair>& pairs,
                                    int min_density, int max_chars) {
    if (pairs.empty() || !full_names(question, pairs).empty()) return std::nullopt;
    static const std::regex quoted(R"(“[^”\n]{2,60}”|"[^"\n]{2,60}"|‘[^’\n]{2,60}’)");
    if (std::regex_search(question, quoted)) return std::nullopt;
    const auto asked = tokens(question);
    if (asked.size() < 2) return std::nullopt;

    struct Part { std::string text; std::vector<std::string> words; };
    std::vector<std::vector<Part>> parts;
    WordSet vocabulary;
    for (const auto& pair : pairs) {
        std::vector<Part> record;
        for (const auto& paragraph : paragraphs(pair.prompt)) {
            auto words = tokens(paragraph);
            vocabulary.insert(words.begin(), words.end());
            record.push_back({paragraph, std::move(words)});
        }
        parts.push_back(std::move(record));
    }
    Variants variants;
    for (const auto& word : asked) {
        if (variants.contains(word)) continue;
        auto& accepted = variants[word];
        for (const auto& seen : vocabulary) if (typo_of(word, seen)) accepted.insert(seen);
    }
    std::vector<std::string> best_phrase;
    std::tuple<int, int, int, int> best_rank{0, 0, 0, 0};
    for (std::size_t size = 2; size <= std::min<std::size_t>(kMaxPhraseWords, asked.size()); ++size) {
        for (std::size_t start = 0; start + size <= asked.size(); ++start) {
            const std::vector<std::string> phrase(asked.begin() + start, asked.begin() + start + size);
            if (stopwords().contains(phrase.front()) || stopwords().contains(phrase.back()) ||
                std::any_of(phrase.begin(), phrase.end(), [&](const auto& word) { return variants[word].empty(); }))
                continue;
            int records = 0, densest = 0, total = 0;
            for (const auto& record : parts) {
                int hits = 0;
                for (const auto& part : record) if (holds(phrase, part.words, variants)) ++hits;
                if (hits) { ++records; densest = std::max(densest, hits); total += hits; }
            }
            if (records < 2) continue;
            const auto rank = std::tuple{std::min(densest, 3), static_cast<int>(size), densest, total};
            if (best_phrase.empty() || rank > best_rank) { best_phrase = phrase; best_rank = rank; }
        }
    }
    if (best_phrase.empty() || std::get<2>(best_rank) < min_density) return std::nullopt;
    std::vector<MemoryPair> excerpts;
    for (std::size_t i = 0; i < pairs.size(); ++i) {
        std::vector<std::string> matching;
        for (const auto& part : parts[i]) if (holds(best_phrase, part.words, variants)) matching.push_back(part.text);
        if (!matching.empty()) {
            MemoryPair copy = pairs[i];
            copy.prompt = join(matching, "\n\n");
            copy.response.clear();
            excerpts.push_back(std::move(copy));
        }
    }
    excerpts = by_date(std::move(excerpts));
    std::unordered_map<std::string, MemoryPair> original;
    for (const auto& pair : pairs) original[pair.pair_id] = pair;
    std::vector<MemoryPair> chosen;
    int room = max_chars;
    for (const auto& excerpt : excerpts) {
        const auto& pair = original.at(excerpt.pair_id);
        if (excerpt.prompt.find("\n\n") != std::string::npos) {
            chosen.push_back(pair);
            room -= static_cast<int>(codepoints(pair.prompt) + codepoints(pair.response));
        }
    }
    if (chosen.size() < kMinDenseNotes) return std::nullopt;
    for (const auto& excerpt : excerpts) {
        const auto& pair = original.at(excerpt.pair_id);
        if (excerpt.prompt.find("\n\n") != std::string::npos) continue;
        const int size = static_cast<int>(codepoints(pair.prompt) + codepoints(pair.response));
        if (size <= room) { chosen.push_back(pair); room -= size; }
    }
    chosen = by_date(thread_of(question, chosen, pairs));
    TopicNotes found;
    found.phrase = join(best_phrase, " ");
    found.densest = std::get<2>(best_rank);
    found.notes = std::move(chosen);
    std::set<std::string> kept;
    for (const auto& pair : found.notes) kept.insert(pair.pair_id);
    for (const auto& excerpt : excerpts) if (kept.contains(excerpt.pair_id))
        found.excerpts[excerpt.pair_id] = excerpt.prompt;
    return found;
}

bool topic_fits(const TopicNotes& found, int max_chars) {
    if (max_chars < 0) return false;
    std::size_t total = 0;
    for (const auto& pair : found.notes)
        total += codepoints(pair.prompt) + codepoints(pair.response);
    return total <= static_cast<std::size_t>(max_chars);
}

TopicNotes topic_with_cards(const TopicNotes& found,
                           const std::vector<MemoryPair>& corpus, int max_chars,
                           const std::vector<std::string>& named) {
    TopicNotes out = found;
    std::vector<std::string> names = named;
    if (names.empty()) {
        std::vector<std::string> full;
        for (const auto& pair : out.notes) full.push_back(pair.prompt + "\n" + pair.response);
        names = full_names(join(full, "\n"), corpus);
    }
    std::set<std::string> held;
    for (const auto& pair : out.notes) held.insert(pair.pair_id);
    for (const auto& pair : cards_for(names, corpus)) {
        if (held.contains(pair.pair_id)) continue;
        TopicNotes candidate = out;
        candidate.notes.push_back(pair);
        if (topic_fits(candidate, max_chars)) {
            out.notes.push_back(pair);
            held.insert(pair.pair_id);
        }
    }
    out.notes = by_date(std::move(out.notes));
    return out;
}

std::vector<std::string> topic_names_from_reading(const std::string& reply,
                                                  const std::vector<MemoryPair>& corpus) {
    return full_names(collapse_space(reply), corpus);
}

json topic_messages(const RunRequest& request, const TopicNotes& found,
                    const std::vector<MemoryPair>& corpus, const std::string& draft) {
    const std::string recent = recent_view(found, corpus);
    const std::string beside = recent.empty() ? "" : "\n\n" + recent;
    const std::string after = draft.empty() ? "" :
        "\n\nA draft reply, written from a reading of only the passages picked out above:\n\n" + draft +
        "\n\nCheck the draft against every note above, then reply to the message as asked at the start: briefly, ending with the line 'ANSWER: …', without mentioning the draft.";
    const std::string user = passages_view(found) + "\n\nSaved notes:\n\n" +
                             record_view(found.notes) + beside + after +
                             "\n\nMessage:\n" + request.user_input;
    return json::array({{{"role", "system"},
                         {"content", system_with_operator(topic_system(), request.system_prompt)}},
                        {{"role", "user"}, {"content", user}}});
}

json topic_latest_messages(const RunRequest& request, const TopicNotes& found,
                           const std::vector<MemoryPair>& corpus) {
    const auto picks = recent_picks(found, corpus, {});
    if (picks.empty()) return json::array();
    std::vector<std::string> passages;
    for (const auto& pick : picks) passages.push_back(pick.passage);
    const std::string user = "Passages:\n" + join(passages, "\n") +
                             "\n\nMessage:\n" + request.user_input;
    const std::string system =
        "You are Ditto, the user's assistant with long-term memory. Below are the latest passages of a longer thread in the user's saved notes. Answer the message only if these passages settle it by themselves. If the answer depends on anything earlier in the thread, reply with one sentence saying that these passages do not settle it, and nothing else. Otherwise reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the passages put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '.";
    return json::array({{{"role", "system"},
                         {"content", system_with_operator(system, request.system_prompt)}},
                        {{"role", "user"}, {"content", user}}});
}

json topic_named_messages(const RunRequest& request, const TopicNotes& found,
                          const std::vector<MemoryPair>& corpus) {
    json messages = topic_messages(request, found, corpus);
    messages.push_back({{"role", "user"},
                        {"content", "Before the message is answered: which person is it asking about? Reply with that person's full name as the notes give it, and nothing else."}});
    return messages;
}

bool topic_draft_usable(const std::string& reply) {
    const auto answer = parse_slot(reply).second;
    return answer && !answer->empty();
}

TopicLead topic_lead(const std::string& question, const Packet& packet,
                     const std::vector<MemoryPair>& corpus,
                     int min_density, int max_chars) {
    TopicLead out{packet, ""};
    const auto found = find_topic(question, corpus, min_density, max_chars);
    if (!found) return out;
    std::set<std::string> held;
    for (const auto& pair : out.packet.records) held.insert(pair.pair_id);
    for (const auto& pair : found->notes) {
        if (held.insert(pair.pair_id).second) {
            out.packet.records.push_back(pair);
            out.packet.rendered.clear();
        }
    }
    std::map<std::string, std::string> labels;
    for (std::size_t i = 0; i < out.packet.records.size(); ++i)
        labels[out.packet.records[i].pair_id] = "M" + std::to_string(i + 1);
    out.lead = passages_view(*found, labels);
    const auto recent = recent_view(*found, corpus, labels);
    if (!recent.empty()) out.lead += "\n\n" + recent;
    return out;
}

}  // namespace ditto
