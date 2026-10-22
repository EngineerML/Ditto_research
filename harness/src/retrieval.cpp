#include "retrieval.hpp"

#include <algorithm>
#include <cmath>
#include <cctype>
#include <iterator>
#include <map>
#include <numeric>
#include <regex>
#include <set>
#include <sstream>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>

#include <unicode/locid.h>
#include <unicode/unistr.h>

namespace ditto {
namespace {

constexpr int kLongPairChars = 2500;
constexpr int kMaxTraversedValues = 16;
constexpr int kMaxExpansionsPerHop = 24;
constexpr int kMaxRecords = 60;
constexpr int kLinkReserve = 4000;
constexpr int kLinkMaxChars = 700;
constexpr int kLinkPerHop = 10;
constexpr int kLinkHops = 2;
constexpr int kLinkFanout = 16;

std::size_t codepoints(const std::string& s) {
    std::size_t n = 0;
    for (unsigned char c : s) n += (c & 0xc0) != 0x80;
    return n;
}

std::string lower_ascii(std::string s) {
    for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}

std::string lower_unicode(const std::string& s) {
    std::string out;
    icu::UnicodeString::fromUTF8(s).toLower(icu::Locale::getRoot()).toUTF8String(out);
    return out;
}

std::string upper_ascii(std::string s) {
    for (char& c : s) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    return s;
}

std::string trim(const std::string& s) {
    auto first = s.find_first_not_of(" \t\r\n\f\v");
    if (first == std::string::npos) return {};
    return s.substr(first, s.find_last_not_of(" \t\r\n\f\v") - first + 1);
}

const std::unordered_set<std::string>& stopwords() {
    static const std::unordered_set<std::string> out = [] {
        const char* words = R"(a an the and or but if then else of to in on at by for with about from into over after before during between under without within i me my mine we our you your yours he him his she her hers they them their it its this that these those what which who whom whose where when why how is are was were be been being am do does did done have has had having can could should would will shall may might must not no yes so as than too very just only also still again ever never now then here there once twice please tell give remind remember recall know think say said mention mentioned told ask asked need want like get got use used using find found look looked back go went come came make made take took keep kept one two three first last next current currently latest actually really exactly right ago earlier later up down out off that's what's i'm i've you're don't doesn't didn't isn't aren't can't won't let's ok okay hey hi hello thanks thank which should now mean began around conversation talking going did much many how long far whole altogether everything anything something already any every per here ll re ve)";
        std::istringstream in(words);
        std::unordered_set<std::string> result;
        std::string w;
        while (in >> w) result.insert(w);
        return result;
    }();
    return out;
}

const std::unordered_set<std::string>& sentence_starts() {
    static const std::unordered_set<std::string> out = [] {
        const char* words = R"(What Which Who Where When How Why Give Remind Think Remember Before After Looking For Can Did Work Read Answer Please Quick Checking Sorting Just Note Tell Find Search Look Use Set Switch Change Make Put Add Run Start Kick Time Go Have Send See Two Real Oh Hey The This That These Those Our My Your And But Or So If Then Also Once Again Now Later Earlier Here There Yes No Not Update Side Random Off One Notes Adding Recorded Noted Logged Kept Tracked Understood Got Nice Thanks Subject From Pasted Everyone Back Contact Handoff Ignore Treat When Against Do Assume Local Within Separately Eventually Lovely Perfect Underneath Meanwhile)";
        std::istringstream in(words);
        std::unordered_set<std::string> result;
        std::string w;
        while (in >> w) result.insert(w);
        return result;
    }();
    return out;
}

std::vector<std::string> tokens(const std::string& text) {
    std::vector<std::string> out;
    for (std::size_t i = 0; i < text.size();) {
        if (!std::isalnum(static_cast<unsigned char>(text[i]))) { ++i; continue; }
        const bool capped = std::isupper(static_cast<unsigned char>(text[i])) != 0;
        std::string word;
        while (i < text.size()) {
            const auto c = static_cast<unsigned char>(text[i]);
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

std::vector<std::string> content_words(const std::string& text) {
    std::vector<std::string> out;
    std::unordered_set<std::string> seen;
    for (const auto& w : tokens(text)) {
        if ((w.size() < 3 && !std::all_of(w.begin(), w.end(), [](unsigned char c) { return std::isdigit(c); })) || stopwords().contains(w)) continue;
        if (seen.insert(w).second) out.push_back(w);
    }
    return out;
}

std::vector<std::string> identifiers(const std::string& text) {
    // Identifier matching scans the original lowered text. Tokenizing
    // first would keep an internal possessive apostrophe (e.g. id123...'s)
    // and incorrectly discard the identifier before it.
    static const std::regex pattern(
        R"(\b(?=[0-9a-z]*[0-9])(?=[0-9a-z]*[a-z])[0-9a-z]{12,}\b)");
    const std::string lowered = lower_ascii(text);
    std::vector<std::string> out;
    for (std::sregex_iterator it(lowered.begin(), lowered.end(), pattern), end;
         it != end; ++it) out.push_back(it->str());
    return out;
}

bool one_edit(const std::string& a, const std::string& b) {
    if (a == b || std::abs(static_cast<int>(a.size()) - static_cast<int>(b.size())) > 1) return false;
    if (a.size() == b.size()) {
        std::vector<std::size_t> diff;
        for (std::size_t i = 0; i < a.size(); ++i) if (a[i] != b[i]) diff.push_back(i);
        return diff.size() == 1 || (diff.size() == 2 && diff[1] == diff[0] + 1 && a[diff[0]] == b[diff[1]] && a[diff[1]] == b[diff[0]]);
    }
    const auto& shorter = a.size() < b.size() ? a : b;
    const auto& longer = a.size() < b.size() ? b : a;
    std::size_t i = 0;
    while (i < shorter.size() && shorter[i] == longer[i]) ++i;
    return shorter.substr(i) == longer.substr(i + 1);
}

std::vector<std::string> codes(const std::string& text, bool normalize = true) {
    // Same two alternatives and left-to-right matching as store.py::CODE_RE.
    // Both alternatives require a hyphen and a digit. Avoid libstdc++ regex's
    // costly failed backtracking on long uninterrupted prose/opaque blobs.
    if (text.find('-') == std::string::npos ||
        std::none_of(text.begin(), text.end(), [](unsigned char c) { return std::isdigit(c); }))
        return {};
    static const std::regex re(R"(\b(?:(?=[A-Za-z0-9-]*\d)(?=[A-Za-z0-9-]*[A-Za-z])[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+|[A-Z]{2,6}-[A-Z0-9]{4,}(?:-[A-Z0-9]+)*)\b)");
    std::vector<std::string> out;
    for (std::sregex_iterator it(text.begin(), text.end(), re), end; it != end; ++it) {
        const auto s = it->str();
        out.push_back(normalize ? upper_ascii(s) : s);
    }
    return out;
}

struct Node {
    MemoryPair pair;
    std::size_t size = 0;
    std::set<std::string> words;
    std::vector<std::string> token_order;
    std::vector<std::pair<std::string, char>> values;
};

int fanout(char kind) {
    switch (kind) { case 'e': case 'c': return 32; case 'q': return 24;
        case 'n': case 'i': return 16; case 'k': return 12; case 'b': return 12; default: return 6; }
}
double anchor_weight(char kind) {
    switch (kind) { case 'e': case 'c': return 1.2; case 'q': return 2.4;
        case 'n': return .9; case 'i': return .7; case 'k': return .6; case 'b': return .8; default: return 0; }
}
double edge_weight(char kind) {
    switch (kind) { case 'e': return 1.; case 'c': case 'k': return .4;
        case 'q': return .9; case 'n': return .85; case 'i': return .7; default: return 0.; }
}
int edge_order(char kind) {
    switch (kind) { case 'e': return 0; case 'c': return 1; case 'q': return 2;
        case 'n': return 3; case 'i': return 4; case 'k': return 5; default: return 6; }
}

class Index {
public:
    std::vector<Node> nodes;
    std::map<std::string, int> df, lower_df, cap_df;
    std::map<std::string, std::vector<int>> postings, word_postings, bigrams;
    std::map<int, std::vector<std::string>> vocab_by_len;
    std::map<std::string, int> by_id;

    explicit Index(const std::vector<MemoryPair>& input) {
        std::vector<MemoryPair> pairs = input;
        std::sort(pairs.begin(), pairs.end(), [](const auto& a, const auto& b) {
            return std::tie(a.timestamp, a.pair_id) < std::tie(b.timestamp, b.pair_id);
        });
        static const std::regex lower_re(R"(\b[a-z]{3,}\b)");
        static const std::regex cap_re(R"(\b[A-Z][a-z]{2,}\b)");
        static const std::regex short_cap_re(R"(\b[A-Z][a-z]\b)");
        static const std::regex email_re(R"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})");
        for (const auto& p : pairs) {
            const auto text = p.prompt + "\n" + p.response;
            auto words = tokens(text);
            std::set<std::string> unique(words.begin(), words.end());
            for (const auto& w : unique) ++df[w];
            auto no_email = text.find('@') == std::string::npos ?
                text : std::regex_replace(text, email_re, " ");
            std::set<std::string> lower, cap;
            for (std::sregex_iterator it(no_email.begin(), no_email.end(), lower_re), end; it != end; ++it) lower.insert(it->str());
            for (std::sregex_iterator it(text.begin(), text.end(), cap_re), end; it != end; ++it) cap.insert(lower_ascii(it->str()));
            for (std::sregex_iterator it(text.begin(), text.end(), short_cap_re), end; it != end; ++it) cap.insert(lower_ascii(it->str()));
            for (const auto& w : lower) ++lower_df[w];
            for (const auto& w : cap) ++cap_df[w];
        }
        for (const auto& [w, _] : df) vocab_by_len[static_cast<int>(w.size())].push_back(w);
        for (const auto& p : pairs) {
            const auto text = p.prompt + "\n" + p.response;
            Node n{p, codepoints(text), {}, tokens(text), {}};
            n.words.insert(n.token_order.begin(), n.token_order.end());
            n.values = extract_values(text);
            int id = static_cast<int>(nodes.size());
            nodes.push_back(std::move(n));
            by_id[p.pair_id] = id;
            for (const auto& w : nodes.back().words) word_postings[w].push_back(id);
            for (const auto& [key, _] : nodes.back().values) postings[key].push_back(id);
            std::set<std::string> unique_bigrams;
            for (std::size_t i = 1; i < nodes.back().token_order.size(); ++i)
                unique_bigrams.insert("b:" + nodes.back().token_order[i - 1] + " " + nodes.back().token_order[i]);
            for (const auto& key : unique_bigrams) bigrams[key].push_back(id);
        }
    }

    int count(const std::map<std::string, int>& m, const std::string& k) const {
        auto it = m.find(k); return it == m.end() ? 0 : it->second;
    }
    std::size_t count_posts(const std::map<std::string, std::vector<int>>& m, const std::string& k) const {
        auto it = m.find(k); return it == m.end() ? 0 : it->second.size();
    }
    const std::vector<int>& posts(const std::map<std::string, std::vector<int>>& m, const std::string& k) const {
        static const std::vector<int> empty;
        auto it = m.find(k); return it == m.end() ? empty : it->second;
    }
    bool name_like(const std::string& w) const {
        if (w.size() < 2 || sentence_starts().contains(w)) return false;
        const auto low = lower_ascii(w);
        return count(lower_df, low) <= count(cap_df, low) / 2.0;
    }
    std::vector<std::pair<std::string, char>> extract_values(const std::string& text) const {
        static const std::regex email_re(R"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})");
        static const std::regex name_re(R"(\b[A-Z][a-z]+(?:[ -][A-Z][a-z]+)+\b)");
        static const std::regex cap_re(R"(\b[A-Z][a-z]{2,}\b)");
        static const std::regex short_cap_re(R"(\b[A-Z][a-z]\b)");
        std::vector<std::pair<std::string, char>> out;
        std::set<std::string> seen, covered;
        auto add = [&](char kind, std::string value) {
            std::string key = std::string(1, kind) + ":" + value;
            if (seen.insert(key).second) out.emplace_back(std::move(key), kind);
        };
        if (text.find('@') != std::string::npos)
            for (std::sregex_iterator it(text.begin(), text.end(), email_re), end; it != end; ++it) {
                auto email = lower_ascii(it->str()); add('e', email);
                auto local = email.substr(0, email.find('@'));
                std::vector<std::string> bits; std::string bit;
                for (char c : local) {
                    if (c == '.' || c == '_' || c == '-') { if (bit.size() >= 2 && std::all_of(bit.begin(), bit.end(), [](unsigned char x) { return std::isalpha(x); })) bits.push_back(bit); bit.clear(); }
                    else bit.push_back(c);
                }
                if (bit.size() >= 2 && std::all_of(bit.begin(), bit.end(), [](unsigned char x) { return std::isalpha(x); })) bits.push_back(bit);
                if (bits.size() >= 2) {
                    std::string full;
                    for (const auto& b : bits) { if (!full.empty()) full += ' '; full += b; }
                    add('n', full);
                } else if (bits.size() == 1 && bits[0].size() >= 5) add('i', bits[0]);
            }
        for (const auto& code : codes(text)) add('c', code);
        const std::pair<std::string, std::string> delimiters[] = {{"“", "”"}, {"\"", "\""}, {"‘", "’"}};
        std::size_t quote_cursor = 0;
        while (quote_cursor < text.size()) {
            std::size_t opening = std::string::npos, kind = 0;
            for (std::size_t i = 0; i < 3; ++i) {
                auto found = text.find(delimiters[i].first, quote_cursor);
                if (found < opening) { opening = found; kind = i; }
            }
            if (opening == std::string::npos) break;
            const auto& [left, right] = delimiters[kind];
            auto end = text.find(right, opening + left.size());
            if (end == std::string::npos) { quote_cursor = opening + left.size(); continue; }
            auto raw = text.substr(opening + left.size(), end - opening - left.size());
            if (raw.find('\n') != std::string::npos || codepoints(raw) < 2 || codepoints(raw) > 60) {
                // Quote matching rejects this outer opener, then resumes at
                // the next character; it may still match a valid inner quote.
                quote_cursor = opening + left.size();
                continue;
            }
            quote_cursor = end + right.size();
            // Quoted-value keys use Unicode lowercase, including accented
            // letters and context-sensitive Unicode casing.
            auto quoted = lower_unicode(trim(raw));
            auto a = quoted.find_first_not_of(" .,;:!?");
            auto b = quoted.find_last_not_of(" .,;:!?");
            if (a != std::string::npos) quoted = quoted.substr(a, b - a + 1);
            else quoted.clear();
            int words = 0; std::istringstream in(quoted); std::string w;
            while (in >> w) ++words;
            if (codepoints(quoted) >= 2 && codepoints(quoted) <= 40 && words <= 5) add('q', quoted);
        }
        for (std::sregex_iterator it(text.begin(), text.end(), name_re), end; it != end; ++it) {
            std::string raw = it->str(), part; std::vector<std::string> parts;
            for (char c : raw) {
                if (c == ' ' || c == '-') { if (!part.empty()) parts.push_back(part); part.clear(); }
                else part.push_back(c);
            }
            if (!part.empty()) parts.push_back(part);
            while (!parts.empty() && !name_like(parts[0])) parts.erase(parts.begin());
            if (parts.size() >= 2) {
                std::string full;
                for (const auto& p : parts) { if (!full.empty()) full += ' '; full += lower_ascii(p); covered.insert(p); }
                add('n', full); add('i', lower_ascii(parts.front().substr(0, 1) + parts.back()));
            } else if (parts.size() == 1) { add('k', lower_ascii(parts[0])); covered.insert(parts[0]); }
        }
        for (std::sregex_iterator it(text.begin(), text.end(), cap_re), end; it != end; ++it)
            if (!covered.contains(it->str()) && name_like(it->str())) add('k', lower_ascii(it->str()));
        for (std::sregex_iterator it(text.begin(), text.end(), short_cap_re), end; it != end; ++it) {
            auto w = it->str(), low = lower_ascii(w);
            if (!covered.contains(w) && !sentence_starts().contains(w) && count(lower_df, low) == 0 && count(cap_df, low) <= fanout('k')) add('k', low);
        }
        return out;
    }
    std::string fix_typo(const std::string& w) const {
        if (count(df, w) || w.size() < 4 || !std::all_of(w.begin(), w.end(), [](unsigned char c) { return std::isalpha(c); })) return w;
        std::string best = w; int best_df = 0;
        for (int len : {static_cast<int>(w.size()) - 1, static_cast<int>(w.size()), static_cast<int>(w.size()) + 1}) {
            auto it = vocab_by_len.find(len); if (it == vocab_by_len.end()) continue;
            for (const auto& cand : it->second) if (count(df, cand) > best_df && one_edit(w, cand)) { best = cand; best_df = count(df, cand); }
        }
        return best;
    }
    double hub_factor(int id) const { return std::sqrt(std::min(1.0, 10.0 / std::max<std::size_t>(1, nodes[id].values.size()))); }
};

struct Anchor { std::string key; char kind; double weight; };

std::vector<Anchor> question_anchors(const Index& index, const std::string& question) {
    auto fixed = tokens(question);
    for (auto& w : fixed) w = index.fix_typo(w);
    std::set<int> claimed;
    std::set<std::string> already_anchored;
    std::vector<Anchor> anchors;
    auto put = [&](const std::string& key, char kind, int df, const std::vector<std::string>& words) {
        if (!df || df > 2 * fanout(kind) || words.empty() || words.size() > fixed.size()) return;
        for (std::size_t start = 0; start + words.size() <= fixed.size(); ++start) {
            bool match = true;
            for (std::size_t j = 0; j < words.size(); ++j) if (fixed[start + j] != words[j] || claimed.contains(static_cast<int>(start + j))) { match = false; break; }
            if (!match) continue;
            for (std::size_t j = 0; j < words.size(); ++j) claimed.insert(static_cast<int>(start + j));
            if (already_anchored.insert(key).second)
                anchors.push_back({key, kind, anchor_weight(kind) / (1.0 + std::log(std::max(1, df)))});
            return;
        }
    };
    const auto values = index.extract_values(question);
    for (char kind : {'e','c','q','n','i','k'})
        for (const auto& [key, actual] : values) if (actual == kind)
            put(key, kind, static_cast<int>(index.count_posts(index.postings, key)), tokens(key.substr(2)));
    for (std::size_t i = 1; i < fixed.size(); ++i) {
        const auto& a = fixed[i-1]; const auto& b = fixed[i];
        if (a.size() < 3 || b.size() < 3 || stopwords().contains(a) || stopwords().contains(b) ||
            std::all_of(a.begin(), a.end(), [](unsigned char c) { return std::isdigit(c); }) ||
            std::all_of(b.begin(), b.end(), [](unsigned char c) { return std::isdigit(c); })) continue;
        auto key = "b:" + a + " " + b;
        put(key, 'b', static_cast<int>(index.count_posts(index.bigrams, key)), {a,b});
    }
    return anchors;
}

double record_size(const Candidate& c) { return static_cast<double>(codepoints(c.pair.prompt) + codepoints(c.pair.response) + 64); }
bool chronological(const Candidate& a, const Candidate& b) { return std::tie(a.pair.timestamp, a.pair.pair_id) < std::tie(b.pair.timestamp, b.pair.pair_id); }

std::vector<Candidate> admit(const std::vector<Candidate>& ordered, double budget, std::vector<Candidate> admitted = {}) {
    double used = 0;
    for (const auto& c : admitted) used += record_size(c);
    std::set<std::string> ids;
    for (const auto& c : admitted) ids.insert(c.pair.pair_id);
    for (const auto& c : ordered) {
        if (admitted.size() >= kMaxRecords) break;
        if (ids.contains(c.pair.pair_id)) continue;
        auto size = record_size(c);
        if (used + size > budget && !admitted.empty()) continue;
        admitted.push_back(c); ids.insert(c.pair.pair_id); used += size;
    }
    return admitted;
}

std::vector<std::vector<Candidate>> code_components(const std::vector<Candidate>& records) {
    std::vector<int> parent(records.size()); std::iota(parent.begin(), parent.end(), 0);
    auto root = [&](int x) { while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; };
    std::map<std::string, int> holder;
    for (int i = 0; i < static_cast<int>(records.size()); ++i) {
        const auto record_codes = codes(records[i].pair.prompt + " " + records[i].pair.response, false);
        std::set<std::string> unique(record_codes.begin(), record_codes.end());
        for (const auto& code : unique) {
            auto [it, inserted] = holder.emplace(code, i);
            if (!inserted) parent[root(i)] = root(it->second);
        }
    }
    std::map<int, std::vector<Candidate>> groups;
    std::vector<int> order;
    for (int i = 0; i < static_cast<int>(records.size()); ++i) {
        int r = root(i);
        if (!groups.contains(r)) order.push_back(r);
        groups[r].push_back(records[i]);
    }
    std::vector<std::vector<Candidate>> out;
    for (int r : order) out.push_back(std::move(groups[r]));
    return out;
}

std::vector<Candidate> arc_order(const std::vector<Candidate>& admitted) {
    std::map<std::string, int> seat;
    for (int i = 0; i < static_cast<int>(admitted.size()); ++i) seat[admitted[i].pair.pair_id] = i;
    auto groups = code_components(admitted);
    std::vector<std::pair<int, std::vector<Candidate>>> blocks;
    for (auto& group : groups) {
        int first = static_cast<int>(admitted.size());
        for (const auto& c : group) first = std::min(first, seat[c.pair.pair_id]);
        std::sort(group.begin(), group.end(), chronological);
        blocks.emplace_back(first, std::move(group));
    }
    std::sort(blocks.begin(), blocks.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
    std::vector<Candidate> out;
    for (auto& [_, group] : blocks) out.insert(out.end(), group.begin(), group.end());
    return out;
}

std::vector<Candidate> strongest_group(const std::vector<Candidate>& ordered) {
    auto n = std::min<std::size_t>(40, ordered.size());
    auto groups = code_components(std::vector<Candidate>(ordered.begin(), ordered.begin() + n));
    std::vector<Candidate> best; double best_sum = -1;
    for (auto& group : groups) {
        double sum = 0; for (const auto& c : group) sum += c.score;
        if (sum > best_sum) { best = group; best_sum = sum; }
    }
    if (best.size() < 3 || best.size() > 12) return {};
    std::sort(best.begin(), best.end(), chronological); return best;
}

std::vector<Candidate> identifier_focus(const std::string& question, const std::vector<Candidate>& ordered) {
    for (const auto& token : identifiers(question)) {
        std::vector<Candidate> carrying;
        for (const auto& c : ordered)
            if (lower_ascii(c.pair.prompt + " " + c.pair.response).find(token) != std::string::npos) carrying.push_back(c);
        if (carrying.size() >= 3) { std::sort(carrying.begin(), carrying.end(), chronological); return carrying; }
    }
    return {};
}

std::vector<Candidate> value_closure(const std::vector<Candidate>& ordered,
                                     const std::vector<Candidate>& held, double budget,
                                     const Index& index) {
    std::map<std::string, std::set<std::string>> keys;
    for (const auto& node : index.nodes)
        for (const auto& [key, _] : node.values) keys[node.pair.pair_id].insert(key);
    std::set<std::string> shared, names;
    for (const auto& c : held) {
        names.insert(c.pair.pair_id);
        const auto& owned = keys[c.pair.pair_id];
        shared.insert(owned.begin(), owned.end());
    }
    const double top = ordered.empty() ? 0.0 : std::max_element(ordered.begin(), ordered.end(),
        [](const auto& a, const auto& b) { return a.score < b.score; })->score;
    std::vector<Candidate> asked, linked, band;
    for (const auto& c : ordered) {
        if (names.contains(c.pair.pair_id)) continue;
        if (c.pinned) { asked.push_back(c); continue; }
        const auto& owned = keys[c.pair.pair_id];
        bool overlaps = std::any_of(owned.begin(), owned.end(), [&](const auto& key) { return shared.contains(key); });
        if (overlaps && linked.size() < 8) linked.push_back(c);
        if (c.score >= .45 * top) band.push_back(c);
    }
    std::vector<Candidate> widened = asked;
    widened.insert(widened.end(), linked.begin(), linked.end());
    std::set<std::string> reached;
    for (const auto& c : widened) reached.insert(c.pair.pair_id);
    for (const auto& c : band) if (!reached.contains(c.pair.pair_id)) widened.push_back(c);
    return admit(widened, budget, held);
}

std::string py_string(const std::string& s) { return json(s).dump(-1, ' ', false, json::error_handler_t::replace); }

std::string render(const std::vector<Candidate>& records, const std::string& question,
                   const std::string& precursor = "",
                   const std::map<std::string, std::string>* labels = nullptr) {
    if (records.empty()) return question;
    std::string out = "Relevant memory context for this turn:\n{\"longTerm\": {\"memories\": [\n";
    for (std::size_t i = 0; i < records.size(); ++i) {
        if (i) out += ",\n";
        const auto& p = records[i].pair;
        const auto mark = labels ? labels->at(p.pair_id) : "M" + std::to_string(i + 1);
        out += "{\"mark\": " + py_string(mark);
        if (!p.pair_id.starts_with("saved-")) out += ", \"pairID\": " + py_string(p.pair_id);
        out += ", \"timestamp\": " + py_string(p.timestamp) + ", \"user\": " + py_string(trim(p.prompt));
        if (!trim(p.response).empty()) out += ", \"ditto\": " + py_string(trim(p.response));
        out += "}";
    }
    out += "\n]}}\n\n";
    if (!precursor.empty()) out += precursor + "\n\n";
    out += "Message:\n" + question;
    return out;
}

std::vector<Candidate> link_hop(const Index& index, const std::vector<Candidate>& held,
                                double budget) {
    std::set<int> holding, anchored;
    for (const auto& c : held) {
        auto it = index.by_id.find(c.pair.pair_id);
        if (it == index.by_id.end()) continue;
        holding.insert(it->second);
        if (c.anchored) anchored.insert(it->second);
    }
    if (!anchored.empty()) {
        std::set<std::string> keys;
        for (int id : anchored)
            for (const auto& [key, kind] : index.nodes[id].values)
                if (edge_weight(kind) > 0 && index.count_posts(index.postings, key) > 1 &&
                    index.count_posts(index.postings, key) <= kLinkFanout) keys.insert(key);
        for (int id : holding) {
            for (const auto& [key, _] : index.nodes[id].values)
                if (keys.contains(key)) { anchored.insert(id); break; }
        }
    }
    auto by_pair_id = [&](int a, int b) {
        return index.nodes[a].pair.pair_id < index.nodes[b].pair.pair_id;
    };
    std::set<int> seen = holding;
    const auto& starting = anchored.empty() ? holding : anchored;
    std::vector<int> frontier(starting.begin(), starting.end());
    std::sort(frontier.begin(), frontier.end(), by_pair_id);
    std::map<int, double> carried;
    for (int hop = 0; hop < kLinkHops; ++hop) {
        std::map<int, std::set<std::string>> reach;
        for (int id : frontier) {
            for (const auto& [key, kind] : index.nodes[id].values) {
                const auto& targets = index.posts(index.postings, key);
                if (edge_weight(kind) <= 0 || targets.size() <= 1 || targets.size() > kLinkFanout) continue;
                for (int target : targets)
                    if (!seen.contains(target) && index.nodes[target].size <= kLinkMaxChars)
                        reach[target].insert(key);
            }
        }
        std::vector<int> step;
        for (const auto& [id, _] : reach) step.push_back(id);
        std::sort(step.begin(), step.end(), [&](int a, int b) {
            if (reach[a].size() != reach[b].size()) return reach[a].size() > reach[b].size();
            if (index.nodes[a].size != index.nodes[b].size) return index.nodes[a].size < index.nodes[b].size;
            return by_pair_id(a, b);
        });
        if (step.size() > kLinkPerHop) step.resize(kLinkPerHop);
        if (step.empty()) break;
        for (int id : step) { seen.insert(id); carried[id] = static_cast<double>(reach[id].size()); }
        frontier = std::move(step);
    }
    std::vector<int> reached;
    for (const auto& [id, _] : carried) reached.push_back(id);
    std::sort(reached.begin(), reached.end(), [&](int a, int b) {
        if (carried[a] != carried[b]) return carried[a] > carried[b];
        if (index.nodes[a].size != index.nodes[b].size) return index.nodes[a].size < index.nodes[b].size;
        return by_pair_id(a, b);
    });
    double used = 0;
    for (const auto& c : held) used += record_size(c);
    std::vector<Candidate> out;
    for (int id : reached) {
        Candidate c; c.pair = index.nodes[id].pair;
        auto size = record_size(c);
        if (used + size > budget) continue;
        used += size; out.push_back(std::move(c));
    }
    return out;
}

}  // namespace

Ranking rank(const std::vector<MemoryPair>& pairs, const std::string& question) {
    Index index(pairs);
    Ranking result;
    result.corpus = pairs;
    if (index.nodes.empty()) return result;
    std::map<int, Candidate> found;
    std::set<int> pinned;
    auto add = [&](int id, double score, bool anchored = false) {
        auto [it, inserted] = found.try_emplace(id);
        if (inserted) it->second.pair = index.nodes[id].pair;
        it->second.score += score;
        it->second.anchored |= anchored;
    };
    for (const auto& token : identifiers(question)) {
        std::vector<int> carrying;
        for (int i = 0; i < static_cast<int>(index.nodes.size()); ++i)
            if (lower_ascii(index.nodes[i].pair.prompt + " " + index.nodes[i].pair.response).find(token) != std::string::npos) carrying.push_back(i);
        if (carrying.size() >= 3) {
            for (int id : carrying) { add(id, 1, true); pinned.insert(id); }
            break;
        }
    }
    auto anchors = question_anchors(index, question);
    result.anchored = !anchors.empty();
    for (const auto& anchor : anchors) result.anchor_kinds.insert(anchor.kind);
    for (const auto& anchor : anchors) {
        if (std::string("ecqnik").find(anchor.kind) != std::string::npos &&
            anchor.key.find("ditto") == std::string::npos)
            result.names_value = true;
    }
    for (const auto& [key, kind] : index.extract_values(question)) {
        if (std::string("ecqn").find(kind) != std::string::npos &&
            key.find("ditto") == std::string::npos)
            result.names_value = true;
    }
    std::map<int, int> anchor_hits;
    for (const auto& a : anchors) {
        const auto& targets = a.kind == 'b' ? index.posts(index.bigrams, a.key) : index.posts(index.postings, a.key);
        for (int id : targets) {
            add(id, a.weight * index.hub_factor(id), true);
            ++anchor_hits[id];
            if (a.kind == 'e' || a.kind == 'c') pinned.insert(id);
        }
    }
    for (const auto& [id, hits] : anchor_hits) if (hits > 1) add(id, found[id].score * .5 * (hits - 1));
    std::set<std::string> claimed;
    for (const auto& a : anchors) for (const auto& w : tokens(a.key.substr(2))) claimed.insert(w);
    auto words = content_words(question);
    std::map<std::string, double> idf;
    std::vector<std::string> idf_order;
    const double total = std::max<std::size_t>(1, index.nodes.size());
    for (const auto& raw : words) {
        const auto w = index.fix_typo(raw);
        const auto df = index.count(index.df, w);
        if (df > 0 && df <= 24) {
            if (!idf.contains(w)) idf_order.push_back(w);
            idf[w] = std::log(1.0 + total / df);
        }
    }
    double total_idf = 0; for (const auto& w : idf_order) total_idf += idf[w];
    std::vector<std::string> open;
    for (const auto& w : idf_order) if (!claimed.contains(w)) open.push_back(w);
    std::stable_sort(open.begin(), open.end(), [&](const auto& a, const auto& b) { return index.df.at(a) < index.df.at(b); });
    std::set<int> pool;
    for (std::size_t i = 0; i < std::min<std::size_t>(8, open.size()); ++i)
        for (int id : index.posts(index.word_postings, open[i])) pool.insert(id);
    std::vector<std::pair<double, int>> seeds;
    if (total_idf > 0) for (int id : pool) {
        double covered = 0;
        for (const auto& w : open) if (index.nodes[id].words.contains(w)) covered += idf[w];
        const double coverage = covered / total_idf / std::sqrt(1.0 + index.nodes[id].size / 3000.0);
        if (coverage > 0) seeds.emplace_back(coverage, id);
    }
    std::sort(seeds.begin(), seeds.end(), [&](const auto& a, const auto& b) {
        if (a.first != b.first) return a.first > b.first;
        return index.nodes[a.second].pair.pair_id < index.nodes[b.second].pair.pair_id;
    });
    for (std::size_t i = 0; i < seeds.size(); ++i) { add(seeds[i].second, .75 * seeds[i].first * seeds[i].first); if (i < 3) pinned.insert(seeds[i].second); }
    if (found.empty()) return result;
    double top_seed = 0; for (const auto& [_, c] : found) top_seed = std::max(top_seed, c.score);
    std::map<int, double> propagated, received;
    for (int hop = 1; hop <= 3; ++hop) {
        std::vector<int> frontier;
        for (const auto& [id, c] : found) if (c.score - propagated[id] >= .3 * top_seed) frontier.push_back(id);
        std::sort(frontier.begin(), frontier.end(), [&](int a, int b) {
            double sa = found.at(a).score - propagated[a], sb = found.at(b).score - propagated[b];
            return sa != sb ? sa > sb : index.nodes[a].pair.pair_id < index.nodes[b].pair.pair_id;
        });
        if (frontier.size() > kMaxExpansionsPerHop) frontier.resize(kMaxExpansionsPerHop);
        if (frontier.empty()) break;
        for (int id : frontier) {
            double origin = found[id].score - propagated[id];
            propagated[id] = found[id].score;
            std::vector<std::pair<std::string, char>> traversable;
            for (const auto& [key, kind] : index.nodes[id].values) {
                auto n = index.count_posts(index.postings, key);
                if (edge_weight(kind) > 0 && n > 1 && n <= static_cast<std::size_t>(fanout(kind)) &&
                    (index.nodes[id].size <= kLongPairChars || kind == 'e' || kind == 'c' || kind == 'q')) traversable.emplace_back(key, kind);
            }
            std::stable_sort(traversable.begin(), traversable.end(), [&](const auto& a, const auto& b) {
                auto ka = std::pair(edge_order(a.second), index.count_posts(index.postings, a.first));
                auto kb = std::pair(edge_order(b.second), index.count_posts(index.postings, b.first));
                return ka < kb;
            });
            if (traversable.size() > kMaxTraversedValues) traversable.resize(kMaxTraversedValues);
            std::map<char, int> kind_counts; for (const auto& [_, kind] : traversable) ++kind_counts[kind];
            std::map<int, std::vector<std::pair<double, std::string>>> gains;
            for (const auto& [key, kind] : traversable) {
                const auto& targets = index.posts(index.postings, key);
                for (int target : targets) if (target != id) {
                    double gain = std::min(origin, 1.5 * origin * edge_weight(kind) / kind_counts[kind] / (targets.size() - 1));
                    gains[target].emplace_back(gain, key);
                }
            }
            std::vector<int> targets; for (const auto& [target, _] : gains) targets.push_back(target);
            std::sort(targets.begin(), targets.end(), [&](int a, int b) { return index.nodes[a].pair.pair_id < index.nodes[b].pair.pair_id; });
            for (int target : targets) {
                double room = top_seed - received[target];
                std::set<std::string> distinct; for (const auto& [_, key] : gains[target]) distinct.insert(key);
                double hub = index.hub_factor(target) * distinct.size();
                for (const auto& [raw_gain, _] : gains[target]) {
                    double gain = std::min(raw_gain * hub, room);
                    if (gain <= 0) break;
                    room -= gain; received[target] += gain; add(target, gain);
                }
            }
        }
    }
    std::vector<int> confident, tail;
    for (const auto& [id, c] : found) {
        double threshold = .4 * top_seed * (index.nodes[id].size > kLongPairChars ? 1.5 : 1.);
        if (pinned.contains(id) || c.score >= threshold) confident.push_back(id);
        else if (index.nodes[id].size <= kLongPairChars || c.score >= .25 * top_seed) tail.push_back(id);
    }
    std::sort(confident.begin(), confident.end(), [&](int a, int b) {
        if (pinned.contains(a) != pinned.contains(b)) return pinned.contains(a);
        double sa = found[a].score / std::pow(index.nodes[a].size + 64, .25);
        double sb = found[b].score / std::pow(index.nodes[b].size + 64, .25);
        return sa != sb ? sa > sb : index.nodes[a].pair.pair_id < index.nodes[b].pair.pair_id;
    });
    std::set<int> admitted(confident.begin(), confident.end()); admitted.insert(tail.begin(), tail.end());
    std::set<std::string> arc_codes;
    for (int id : admitted) for (const auto& [key, kind] : index.nodes[id].values) if (kind == 'c') arc_codes.insert(key);
    for (const auto& [id, _] : found) if (!admitted.contains(id)) {
        bool match = false;
        for (const auto& [key, kind] : index.nodes[id].values) if (kind == 'c' && arc_codes.contains(key)) { match = true; break; }
        if (match) tail.push_back(id);
    }
    std::sort(tail.begin(), tail.end(), [&](int a, int b) {
        double sa = found[a].score / std::sqrt(index.nodes[a].size + 64.);
        double sb = found[b].score / std::sqrt(index.nodes[b].size + 64.);
        return sa != sb ? sa > sb : index.nodes[a].pair.pair_id < index.nodes[b].pair.pair_id;
    });
    for (int id : confident) result.ordered.push_back(found.at(id));
    for (int id : tail) result.ordered.push_back(found.at(id));
    return result;
}

bool has_identifier_focus(const std::string& question,
                          const std::vector<Candidate>& ordered) {
    return !identifier_focus(question, ordered).empty();
}

std::string asked_part(const std::string& text,
                       const std::vector<std::string>& keep_identifiers) {
    std::vector<std::string> sentences;
    std::size_t start = 0, cursor = 0;
    while (cursor < text.size()) {
        if (!std::isspace(static_cast<unsigned char>(text[cursor]))) { ++cursor; continue; }
        const auto whitespace = cursor;
        while (cursor < text.size() && std::isspace(static_cast<unsigned char>(text[cursor]))) ++cursor;
        const auto after = cursor;
        const auto prefix = text.substr(start, whitespace - start);
        bool punct = !prefix.empty() && (prefix.back() == '.' || prefix.back() == '?' || prefix.back() == '!');
        if (!punct && prefix.size() >= 2 &&
            (prefix.back() == '"' || prefix.back() == '\'' || prefix.back() == ')' || prefix.back() == ']')) {
            char previous = prefix[prefix.size() - 2];
            punct = previous == '.' || previous == '?' || previous == '!';
        }
        if (!punct && prefix.size() >= 4 && (prefix.ends_with("”") || prefix.ends_with("’"))) {
            char previous = prefix[prefix.size() - 4];
            punct = previous == '.' || previous == '?' || previous == '!';
        }
        bool colon = !prefix.empty() && (prefix.back() == ':' || prefix.back() == ';') &&
                     after < text.size() && std::isupper(static_cast<unsigned char>(text[after]));
        std::size_t next = after;
        bool dash = false;
        if (text.compare(after, 3, "—") == 0 || text.compare(after, 3, "–") == 0) {
            next = after + 3;
            if (next < text.size() && std::isspace(static_cast<unsigned char>(text[next]))) {
                while (next < text.size() && std::isspace(static_cast<unsigned char>(text[next]))) ++next;
                dash = next < text.size() && std::isupper(static_cast<unsigned char>(text[next]));
            }
        }
        if (!(punct || colon || dash)) continue;
        auto part = trim(text.substr(start, whitespace - start));
        if (!part.empty()) sentences.push_back(std::move(part));
        start = dash ? next : after;
        cursor = start;
    }
    auto rest = trim(text.substr(start));
    if (!rest.empty()) sentences.push_back(std::move(rest));
    if (sentences.empty()) return text;
    auto ends_question = [](std::string sentence) {
        while (!sentence.empty()) {
            if (sentence.ends_with("”") || sentence.ends_with("’")) { sentence.resize(sentence.size() - 3); continue; }
            char c = sentence.back();
            if (c == '"' || c == '\'' || c == ')' || c == ']') sentence.pop_back();
            else break;
        }
        return !sentence.empty() && sentence.back() == '?';
    };
    std::set<std::size_t> kept;
    for (std::size_t i = 0; i < sentences.size(); ++i) if (ends_question(sentences[i])) kept.insert(i);
    if (kept.empty()) {
        std::size_t best = 0;
        for (std::size_t i = 1; i < sentences.size(); ++i)
            if (codepoints(sentences[i]) > codepoints(sentences[best])) best = i;
        kept.insert(best);
    }
    std::set<std::string> needed;
    for (const auto& token : keep_identifiers) needed.insert(lower_ascii(token));
    if (!needed.empty())
        for (std::size_t i = 0; i < sentences.size(); ++i)
            for (const auto& token : identifiers(sentences[i]))
                if (needed.contains(token)) { kept.insert(i); break; }
    std::string out;
    for (std::size_t i : kept) { if (!out.empty()) out += ' '; out += sentences[i]; }
    return out;
}

std::vector<std::set<std::string>> closest_anchor_holders(
    const Ranking& ranking, const std::string& question) {
    std::vector<MemoryPair> corpus = ranking.corpus;
    if (corpus.empty()) for (const auto& c : ranking.ordered) corpus.push_back(c.pair);
    const Index index(corpus);
    std::vector<std::set<std::string>> out;
    for (const auto& anchor : question_anchors(index, question)) {
        if (std::string("ecqnikb").find(anchor.kind) == std::string::npos) continue;
        const auto& carrying = anchor.kind == 'b'
            ? index.posts(index.bigrams, anchor.key)
            : index.posts(index.postings, anchor.key);
        std::set<std::string> ids;
        for (int id : carrying) ids.insert(index.nodes[id].pair.pair_id);
        out.push_back(std::move(ids));
    }
    return out;
}

static Packet build_packet_impl(const Ranking& ranking, const std::string& question,
                                int char_budget, bool arc, bool thread_first,
                                bool closure, bool use_link_hop) {
    const auto& ordered = ranking.ordered;
    std::vector<MemoryPair> corpus = ranking.corpus;
    if (corpus.empty()) for (const auto& c : ordered) corpus.push_back(c.pair);
    const Index index(corpus);
    auto assemble = [&](int budget) -> std::pair<std::vector<Candidate>, bool> {
        auto focus = identifier_focus(question, ordered);
        if (!focus.empty()) {
            std::set<std::string> held; for (const auto& c : focus) held.insert(c.pair.pair_id);
            std::vector<Candidate> additional;
            for (const auto& c : ordered) if (c.pinned && !held.contains(c.pair.pair_id)) additional.push_back(c);
            auto selected = admit(additional, budget, focus);
            std::sort(selected.begin(), selected.end(), chronological);
            return {std::move(selected), true};
        }
        std::vector<Candidate> selected;
        bool focused = false;
        auto thread = thread_first ? strongest_group(ordered) : std::vector<Candidate>{};
        bool leads = false;
        if (!thread.empty()) {
            for (const auto& c : thread) if (!ordered.empty() && c.pair.pair_id == ordered[0].pair.pair_id) leads = true;
            double group_sum = 0, lead_max = 0;
            for (const auto& c : thread) group_sum += c.score;
            for (std::size_t i = 0; i < std::min<std::size_t>(5, ordered.size()); ++i) lead_max = std::max(lead_max, ordered[i].score);
            leads |= group_sum >= 2 * lead_max;
        }
        if (leads) {
            focused = true; selected = thread;
            std::set<std::string> held; for (const auto& c : selected) held.insert(c.pair.pair_id);
            for (const auto& c : ordered) if (!held.contains(c.pair.pair_id)) {
                selected.push_back(c); held.insert(c.pair.pair_id);
                if (selected.size() >= thread.size() + 2) break;
            }
            if (closure) {
                selected = value_closure(ordered, selected, budget, index);
                if (arc) selected = arc_order(selected);
            }
            return {std::move(selected), focused};
        } else if (!thread.empty() && std::count_if(thread.begin(), thread.end(), [](const auto& c) { return c.anchored; }) >= 2) {
            focused = true;
            std::set<std::string> names; for (const auto& c : thread) names.insert(c.pair.pair_id);
            std::vector<Candidate> more;
            const double floor = ordered.empty() ? 0 : .2 * ordered[0].score;
            for (const auto& c : ordered) if (!names.contains(c.pair.pair_id) && c.score >= floor) more.push_back(c);
            selected = admit(more, budget, thread);
            if (closure) {
                selected = value_closure(ordered, selected, budget, index);
                if (arc) selected = arc_order(selected);
            }
            return {std::move(selected), focused};
        } else {
            auto n = ranking.anchored ? ordered.size() : std::min<std::size_t>(3, ordered.size());
            selected = admit(std::vector<Candidate>(ordered.begin(), ordered.begin() + n), budget);
            double top = 0; for (const auto& c : selected) top = std::max(top, c.score);
            std::sort(selected.begin(), selected.end(), [&](const auto& a, const auto& b) {
                auto band = [&](const Candidate& c) { return top <= 0 || c.score >= .45 * top ? 0 : c.score >= .2 * top ? 1 : 2; };
                return std::make_tuple(band(a), a.pair.timestamp, a.pair.pair_id) <
                       std::make_tuple(band(b), b.pair.timestamp, b.pair.pair_id);
            });
        }
        return {arc ? arc_order(selected) : selected, focused};
    };
    auto [selected, focused] = assemble(use_link_hop ? char_budget - kLinkReserve : char_budget);
    if (use_link_hop) {
        auto reached = link_hop(index, selected, char_budget);
        if (reached.empty()) {
            auto full = assemble(char_budget);
            selected = std::move(full.first);
            focused = full.second;
        } else selected.insert(selected.end(), reached.begin(), reached.end());
    }
    if (use_link_hop && !ranking.fused_order.empty()) {
        if (ranking.meaning_records > 0 && ranking.anchored && identifier_focus(question, ordered).empty()) {
            std::set<std::string> held;
            for (const auto& c : selected) held.insert(c.pair.pair_id);
            int added = 0;
            double used = 0;
            double packet_chars = 0;
            for (const auto& c : selected) packet_chars += record_size(c);
            const double meaning_room = ranking.meaning_ceiling > 0
                ? std::min<double>(ranking.meaning_chars, ranking.meaning_ceiling - packet_chars)
                : ranking.meaning_chars;
            for (const auto& pair_id : ranking.fused_order) {
                if (added >= ranking.meaning_records) break;
                auto it = index.by_id.find(pair_id);
                if (it == index.by_id.end() || held.contains(pair_id)) continue;
                Candidate c; c.pair = index.nodes[it->second].pair;
                auto size = record_size(c);
                if (used + size > meaning_room) continue;
                selected.push_back(std::move(c));
                held.insert(pair_id); used += size; ++added;
            }
        }
        if (ranking.meaning_order) {
            std::map<std::string, std::size_t> seat;
            for (std::size_t i = 0; i < ranking.fused_order.size(); ++i) seat[ranking.fused_order[i]] = i;
            std::stable_sort(selected.begin(), selected.end(), [&](const auto& a, const auto& b) {
                auto as = seat.find(a.pair.pair_id), bs = seat.find(b.pair.pair_id);
                return (as == seat.end() ? seat.size() : as->second) <
                       (bs == seat.end() ? seat.size() : bs->second);
            });
            selected = arc_order(selected);
        }
    }
    Packet result; result.focused = focused;
    for (const auto& c : selected) result.records.push_back(c.pair);
    result.rendered = render(selected, question);
    return result;
}

Packet build_packet(const Ranking& ranking, const std::string& question, int char_budget) {
    return build_packet_impl(ranking, question, char_budget, true, true, true, true);
}

std::vector<std::string> quoted_spans(const std::string& message) {
    const std::pair<std::string, std::string> delimiters[] = {{"“", "”"}, {"\"", "\""}};
    std::vector<std::string> out;
    std::set<std::string> seen;
    std::size_t cursor = 0;
    while (cursor < message.size()) {
        std::size_t opening = std::string::npos, kind = 0;
        for (std::size_t i = 0; i < 2; ++i) {
            auto found = message.find(delimiters[i].first, cursor);
            if (found < opening) { opening = found; kind = i; }
        }
        if (opening == std::string::npos) break;
        const auto& [left, right] = delimiters[kind];
        auto ending = message.find(right, opening + left.size());
        if (ending == std::string::npos) { cursor = opening + left.size(); continue; }
        auto raw = message.substr(opening + left.size(), ending - opening - left.size());
        if (raw.find('\n') != std::string::npos) {
            // Quote matching rejects an outer span that crosses a newline
            // but can still find a valid quote inside it after that point.
            cursor = opening + left.size();
            continue;
        }
        cursor = ending + right.size();
        auto span = lower_ascii(trim(raw));
        if (codepoints(span) >= 3 && codepoints(span) <= 80 && seen.insert(span).second)
            out.push_back(std::move(span));
    }
    return out;
}

std::string action_focus_block(const Packet& packet, const std::string& message) {
    const auto spans = quoted_spans(message);
    if (spans.empty()) return {};
    std::vector<std::size_t> carrying;
    for (std::size_t i = 0; i < packet.records.size(); ++i) {
        const auto& pair = packet.records[i];
        if (codepoints(pair.prompt) + codepoints(pair.response) > 1500) continue;
        const auto text = lower_ascii(pair.prompt + " " + pair.response);
        if (std::any_of(spans.begin(), spans.end(), [&](const auto& span) {
                return text.find(span) != std::string::npos;
            })) carrying.push_back(i);
    }
    if (carrying.empty() || carrying.size() > 4) return {};
    std::sort(carrying.begin(), carrying.end(), [&](std::size_t a, std::size_t b) {
        return std::tie(packet.records[a].timestamp, a) < std::tie(packet.records[b].timestamp, b);
    });
    std::string out = "Every record above of up to 1500 characters that contains words the message quotes, repeated in date order:\n\n";
    for (std::size_t n = 0; n < carrying.size(); ++n) {
        const auto seat = carrying[n];
        const auto& pair = packet.records[seat];
        if (n) out += "\n\n";
        out += "[M" + std::to_string(seat + 1) + "]";
        if (!pair.pair_id.starts_with("saved-")) out += " pair_id=" + pair.pair_id;
        out += " time=" + pair.timestamp + "\nUser: " + trim(pair.prompt);
        if (!trim(pair.response).empty()) out += "\nAssistant: " + trim(pair.response);
    }
    return out;
}

std::string compose_action_packet(const Packet& packet, const std::string& message) {
    const auto block = action_focus_block(packet, message);
    if (block.empty() && !packet.rendered.empty()) return packet.rendered;
    std::vector<Candidate> selected;
    selected.reserve(packet.records.size());
    for (const auto& pair : packet.records) { Candidate c; c.pair = pair; selected.push_back(std::move(c)); }
    return render(selected, message, block);
}

std::string compose_subset(const std::vector<MemoryPair>& records,
                           const std::string& message,
                           const std::map<std::string, std::string>& labels,
                           const std::string& precursor) {
    std::vector<Candidate> selected;
    selected.reserve(records.size());
    for (const auto& pair : records) { Candidate c; c.pair = pair; selected.push_back(std::move(c)); }
    return render(selected, message, precursor, &labels);
}

namespace {

constexpr const char* kCoverageHeader = "Stored conversations that contain each distinctive term of the message, found by searching the whole store and not only the records shown above. A conversation shown above is named by its mark, any other by its pair id. This is a mechanical word search: a conversation may say the same thing in other words, and one named here may be unrelated to the message.";
constexpr const char* kSavedNote = "a note saved earlier, not shown above and without a pair id";
constexpr const char* kListCut = "(list cut)";

std::map<std::string, std::string> packet_labels(const Packet& packet) {
    std::map<std::string, std::string> labels;
    for (std::size_t i = 0; i < packet.records.size(); ++i)
        labels[packet.records[i].pair_id] = "M" + std::to_string(i + 1);
    return labels;
}

std::string named_holders(const Index& index, const std::vector<int>& holders,
                          const std::map<std::string, std::string>& labels) {
    std::set<int> unique(holders.begin(), holders.end());
    int unshown = 0;
    std::vector<int> shown, others;
    for (int id : unique) {
        const auto& pair_id = index.nodes[id].pair.pair_id;
        auto mark = labels.find(pair_id);
        if (mark != labels.end()) shown.push_back(id);
        else if (pair_id.starts_with("saved-")) ++unshown;
        else others.push_back(id);
    }
    if (shown.empty() && others.empty() && unshown == 0) return "none";
    std::sort(shown.begin(), shown.end(), [&](int a, int b) {
        return std::stoi(labels.at(index.nodes[a].pair.pair_id).substr(1)) <
               std::stoi(labels.at(index.nodes[b].pair.pair_id).substr(1));
    });
    std::sort(others.begin(), others.end(), [&](int a, int b) {
        return std::tie(index.nodes[a].pair.timestamp, index.nodes[a].pair.pair_id) <
               std::tie(index.nodes[b].pair.timestamp, index.nodes[b].pair.pair_id);
    });
    std::vector<std::string> names;
    for (int id : shown) names.push_back(labels.at(index.nodes[id].pair.pair_id));
    for (int id : others) names.push_back("pair_id=" + index.nodes[id].pair.pair_id);
    if (unshown == 1) names.emplace_back(kSavedNote);
    else if (unshown > 1) names.push_back(std::to_string(unshown) + " notes saved earlier, not shown above and without pair ids");
    std::string out;
    const auto n = std::min<std::size_t>(12, names.size());
    for (std::size_t i = 0; i < n; ++i) { if (i) out += ", "; out += names[i]; }
    if (names.size() > 12) out += " " + std::string(kListCut);
    return out;
}

std::string question_coverage(const Index& index, const std::string& question,
                              const std::map<std::string, std::string>& labels) {
    if (index.nodes.empty()) return {};
    static const std::regex sentence_head(R"((?:^|[.!?;:]\s+|\n)\s*$)");
    struct Term { std::string key, surface; std::vector<int> holders; int rank; };
    std::vector<Term> found;
    const std::string kinds = "necqik";
    for (const auto& [key, kind] : index.extract_values(question)) {
        const auto type = kinds.find(kind);
        if (type == std::string::npos) continue;
        auto term = key.substr(2);
        if (codepoints(term) < 3) continue;
        auto position = lower_ascii(question).find(lower_ascii(term));
        if (position == std::string::npos) continue;
        const auto prefix = question.substr(0, position);
        if (std::regex_search(prefix, sentence_head)) continue;
        auto holders = index.posts(index.postings, key);
        if (holders.empty() && term.find(' ') == std::string::npos) continue;
        found.push_back({key, question.substr(position, term.size()), holders, static_cast<int>(type)});
    }
    std::sort(found.begin(), found.end(), [](const Term& a, const Term& b) {
        return std::make_tuple(a.rank, a.holders.size(), a.key) <
               std::make_tuple(b.rank, b.holders.size(), b.key);
    });
    if (found.empty()) return {};
    if (found.size() > 10) found.resize(10);
    std::string out = kCoverageHeader;
    for (const auto& term : found) {
        out += "\n\"" + term.surface + "\" - " + named_holders(index, term.holders, labels);
        if (!term.holders.empty()) continue;
        std::vector<std::string> parts;
        for (const auto& word : tokens(term.key.substr(2))) if (word.size() > 1)
            parts.push_back(word + " - " + named_holders(index, index.posts(index.word_postings, word), labels));
        if (parts.size() >= 2) {
            out += " (as separate words: ";
            for (std::size_t i = 0; i < parts.size(); ++i) { if (i) out += "; "; out += parts[i]; }
            out += ")";
        }
    }
    return out;
}

constexpr const char* kWorksheetHeader = "Sentences that state a figure, from records grouped by shared identifiers, oldest first. This grouping is mechanical and may include rows unrelated to the message; the records are what count.";

std::vector<std::vector<int>> worksheet_groups(const Packet& packet) {
    std::vector<int> parents(packet.records.size());
    std::iota(parents.begin(), parents.end(), 0);
    auto root = [&](int x) { while (parents[x] != x) { parents[x] = parents[parents[x]]; x = parents[x]; } return x; };
    std::map<std::string, int> first_by_key;
    for (int i = 0; i < static_cast<int>(packet.records.size()); ++i) {
        const auto raw = codes(packet.records[i].prompt + " " + packet.records[i].response);
        std::set<std::string> keys(raw.begin(), raw.end());
        for (const auto& key : keys) {
            auto [it, inserted] = first_by_key.emplace(key, i);
            if (!inserted) parents[root(it->second)] = root(i);
        }
    }
    std::map<int, std::vector<int>> grouped;
    std::vector<int> order;
    for (int i = 0; i < static_cast<int>(packet.records.size()); ++i) {
        int id = root(i);
        if (!grouped.contains(id)) order.push_back(id);
        grouped[id].push_back(i);
    }
    std::vector<std::vector<int>> out;
    for (int id : order) {
        auto members = std::move(grouped[id]);
        if (members.size() < 2) continue;
        std::sort(members.begin(), members.end(), [&](int a, int b) {
            return std::tie(packet.records[a].timestamp, packet.records[a].pair_id) <
                   std::tie(packet.records[b].timestamp, packet.records[b].pair_id);
        });
        out.push_back(std::move(members));
    }
    return out;
}

std::vector<std::string> worksheet_sentences(const std::string& raw) {
    std::istringstream in(raw);
    std::string word, clean;
    while (in >> word) { if (!clean.empty()) clean += ' '; clean += word; }
    if (clean.empty()) return {};
    std::vector<std::string> sentences;
    std::size_t start = 0;
    for (std::size_t i = 0; i + 1 < clean.size(); ++i)
        if ((clean[i] == '.' || clean[i] == '!' || clean[i] == '?') && clean[i + 1] == ' ') {
            sentences.push_back(clean.substr(start, i - start + 1));
            start = i + 2;
        }
    if (start < clean.size()) sentences.push_back(clean.substr(start));
    return sentences;
}

bool has_figure(const std::string& sentence) {
    for (std::size_t start = 0; start < sentence.size(); ++start) {
        std::size_t i = start;
        if (sentence.compare(i, 3, "€") == 0) i += 3;
        else if (sentence.compare(i, 2, "£") == 0) i += 2;
        else if (sentence[i] == '$') ++i;
        if (i >= sentence.size() || !std::isdigit(static_cast<unsigned char>(sentence[i]))) continue;
        if (start > 0 && (std::isalnum(static_cast<unsigned char>(sentence[start - 1])) || sentence[start - 1] == '-')) continue;
        ++i;
        while (i < sentence.size() && (std::isdigit(static_cast<unsigned char>(sentence[i])) || sentence[i] == ',')) ++i;
        if (i + 1 < sentence.size() && sentence[i] == '.' && std::isdigit(static_cast<unsigned char>(sentence[i + 1]))) {
            i += 2;
            while (i < sentence.size() && std::isdigit(static_cast<unsigned char>(sentence[i]))) ++i;
        }
        if (i < sentence.size() && sentence[i] == '%') ++i;
        if (i < sentence.size() && (std::isalnum(static_cast<unsigned char>(sentence[i])) || sentence[i] == '-')) continue;
        return true;
    }
    return false;
}

std::string shared_codes(const Packet& packet, const std::vector<int>& members) {
    std::set<std::string> common, all;
    bool first = true;
    for (int id : members) {
        auto raw = codes(packet.records[id].prompt + " " + packet.records[id].response);
        std::set<std::string> keys(raw.begin(), raw.end());
        all.insert(keys.begin(), keys.end());
        if (first) { common = std::move(keys); first = false; }
        else {
            std::set<std::string> next;
            std::set_intersection(common.begin(), common.end(), keys.begin(), keys.end(),
                                  std::inserter(next, next.end()));
            common = std::move(next);
        }
    }
    const auto& keys = common.empty() ? all : common;
    std::string out;
    for (const auto& key : keys) { if (!out.empty()) out += ", "; out += key; }
    return out;
}

std::string render_worksheet(const Packet& packet,
                             const std::map<std::string, std::string>& labels) {
    const auto groups = worksheet_groups(packet);
    bool cut = groups.size() > 6;
    int used = 0;
    std::vector<std::string> blocks;
    for (std::size_t group = 0; group < std::min<std::size_t>(6, groups.size()); ++group) {
        const auto& members = groups[group];
        std::vector<std::string> marks, figures;
        for (int id : members) {
            const auto& pair = packet.records[id];
            const auto mark = labels.at(pair.pair_id);
            marks.push_back(mark);
            const auto opening = "[" + mark + "] " + pair.timestamp + " — ";
            for (const auto& sentence : worksheet_sentences(pair.prompt))
                if (has_figure(sentence)) figures.push_back(opening + sentence);
            for (const auto& sentence : worksheet_sentences(pair.response))
                if (has_figure(sentence)) figures.push_back(opening + sentence);
        }
        if (figures.empty()) continue;
        std::string title = "Records ";
        for (std::size_t i = 0; i < marks.size(); ++i) { if (i) title += ", "; title += marks[i]; }
        title += " sharing " + shared_codes(packet, members);
        std::vector<std::string> lines = {std::move(title)};
        lines.insert(lines.end(), figures.begin(), figures.end());
        if (used + static_cast<int>(lines.size()) > 60) { lines.resize(std::max(0, 60 - used)); cut = true; }
        if (!lines.empty()) {
            std::string block;
            for (const auto& line : lines) { if (!block.empty()) block += '\n'; block += line; }
            blocks.push_back(std::move(block));
        }
        if (used + static_cast<int>(1 + figures.size()) > 60) break;
        used += static_cast<int>(1 + figures.size());
    }
    if (blocks.empty()) return {};
    std::string out = kWorksheetHeader;
    for (const auto& block : blocks) out += "\n\n" + block;
    if (cut) out += "\n" + std::string(kListCut);
    return out;
}

}  // namespace

Packet build_records_packet(const Ranking& ranking, const std::string& question,
                            const RecordsPacketOptions& options) {
    Ranking pinned = ranking;
    if (pinned.corpus.empty()) for (const auto& c : pinned.ordered) pinned.corpus.push_back(c.pair);
    std::set<std::string> known;
    for (const auto& c : pinned.ordered) known.insert(c.pair.pair_id);
    for (const auto& pair_id : options.recall_pins) {
        if (known.contains(pair_id)) continue;
        auto it = std::find_if(pinned.corpus.begin(), pinned.corpus.end(), [&](const auto& p) {
            return p.pair_id == pair_id;
        });
        if (it == pinned.corpus.end()) continue;
        Candidate c; c.pair = *it; c.pinned = true;
        pinned.ordered.push_back(std::move(c));
        known.insert(pair_id);
    }
    pinned.anchored |= !options.recall_pins.empty();
    auto packet = build_packet_impl(pinned, question, options.char_budget,
                                    options.arc, options.thread_first,
                                    options.closure, options.link_hop);
    if (packet.records.empty() || (!options.coverage && (!options.worksheet || packet.focused)))
        return packet;
    const auto labels = packet_labels(packet);
    std::string block;
    if (options.coverage) {
        const Index index(pinned.corpus);
        block = question_coverage(index, question, labels);
    }
    if (options.worksheet && !packet.focused) {
        auto worksheet = render_worksheet(packet, labels);
        if (!worksheet.empty()) { if (!block.empty()) block += "\n\n"; block += worksheet; }
    }
    if (!block.empty()) {
        std::vector<Candidate> selected;
        selected.reserve(packet.records.size());
        for (const auto& pair : packet.records) { Candidate c; c.pair = pair; selected.push_back(std::move(c)); }
        packet.rendered = render(selected, question, block);
    }
    return packet;
}

}  // namespace ditto
