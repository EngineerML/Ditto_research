#include "surface.hpp"

#include <algorithm>
#include <map>
#include <regex>
#include <set>
#include <sstream>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

#include "lane.hpp"

namespace ditto {
namespace {

using Words = std::set<std::string>;
using ConceptTable = std::map<std::string, Words>;

Words word_set(std::string_view words) {
    Words out;
    std::istringstream in{std::string(words)};
    for (std::string word; in >> word;) out.insert(word);
    return out;
}

const ConceptTable kActions = {
    {"create", word_set("create build make generate draw produce compose design")},
    {"edit", word_set("edit adjust modify revise update change fix")},
    {"delete", word_set("delete remove forget erase drop")},
    {"run", word_set("run start launch execute begin trigger")},
    {"compute", word_set("compute calculate sum average total percent percentage plus minus divide multiply")},
    {"search", word_set("search find look browse")},
    {"read", word_set("read open follow summarize summarise fetch retrieve get recall")},
    {"discover", word_set("check inspect discover")},
    {"list", word_set("list show display")},
    {"save", word_set("remember note save store")},
    {"send", word_set("send email forward mail message")},
    {"configure", word_set("set switch change use enable disable turn")},
    {"status", word_set("status progress state")},
};

const ConceptTable kResources = {
    {"image", word_set("image picture photo render illustration drawing")},
    {"link", word_set("link page url source result")},
    {"web", word_set("web online internet news")},
    {"memory", word_set("memory memories note")},
    {"subject", word_set("subject topic")},
    {"artifact", word_set("artifact app site dashboard")},
    {"job", word_set("job task queue script")},
    {"code", word_set("code javascript sandbox")},
    {"tool", word_set("tool")},
    {"feedback", word_set("feedback bug")},
    {"theme", word_set("theme mode")},
    {"model", word_set("model")},
    {"effort", word_set("reasoning effort thinking")},
    {"preferences", word_set("preference")},
    {"capability", word_set("capability feature ability option setting")},
    {"calendar", word_set("calendar")},
    {"email", word_set("email mail inbox")},
    {"accent", word_set("accent")},
    {"font", word_set("font typeface")},
    {"workflow", word_set("workflow routine automation")},
    {"schedule", word_set("schedule scheduled recurring")},
};

const Words kNameNoise = word_set("for chat main agent events event in");
const Words kCourtesy = word_set("please thanks thank you it one ok okay so the a an my and to on of at up now again this that these those them then just also");
const Words kDescriptors = word_set("new saved existing quick small little");
const Words kDeictic = word_set("it that this them those these one");
const Words kGenericName = word_set("search create set list run execute get file read main chat for team status in save update delete send discover");
const Words kReadSynonyms = word_set("task tasks queue queued automatic scheduled app feature features option options setting settings control switch help calendar web online internet");
const Words kLooseSynonyms = kReadSynonyms;

// Built from all concept words, courtesy terms, and regex-source
// words in NEGATION_LEAD / LEAD_INS. Keeping the exact sorted source set also
// preserves the ambiguous-spelling behavior of snap_word().
const Words kSpellingVocabulary = word_set(
    "a ability accent adjust again alone also an and app artifact at automation average begin browse bug build calculate calendar capability change check code compose compute create dashboard delete design disable discover display divide don' dont draw drawing drop edit effort email enable erase execute feature feedback fetch find fix follow font forget forward generate get hello illustration image inbox inspect internet it javascript job just launch leave link list look mail make memories memory message minus mode model modify multiply my need never news note now of ok okay on one online open option page percent percentage photo picture please plus preference produce progress queue read reasoning recall recurring remember remove render result retrieve revise right routine run sandbox save schedule scheduled script search send set setting show site skip so source start state status store subject sum summarise summarize sure switch task thank thanks that the them theme then these thinking this those to tool topic total trigger turn typeface up update url use web well without workflow you");

const std::regex kWord(R"rx([A-Za-z][A-Za-z'\-]*)rx");
const std::regex kClauseSplit(R"rx([;—–]|\s-\s|,\s*(?:and|but|then|so)\s+|\b(?:and then|then)\b|\.\s+|\?\s+)rx");
const std::regex kVerbInitial(R"rx(^\s*(?:(?:hey|hi|hello|ok|okay|so|well|thanks|also)[,:\-—\s]*)*(?:please\s+|kindly\s+|just\s+|go ahead and\s+|now\s+|actually\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?([a-z]+)\b)rx", std::regex::icase);
const std::regex kNegationLead(R"rx(^\s*(?:(?:hey|hi|hello|ok|okay|so|well)[,:\-—\s]*)*(?:please\s+)?(?:don'?t|do not|dont|no need to|no need for|never|skip|without|leave [a-z ]+ alone|no [a-z\- ]+ please)\b)rx", std::regex::icase);
const std::regex kLeadIns(R"rx(^\s*(?:(?:hey|hi|hello|ok|okay|so|well|right|sure)[,:\-—\s]+)+)rx", std::regex::icase);
const std::regex kQuestionWord(R"rx(^\s*(?:what|which|who|where|when|how|did|do|does|is|are|can|could)\b)rx", std::regex::icase);
const std::regex kQuestionAnywhere(R"rx(\?|\bwhat'?s\b|\bwhat is\b|\bwhat\b)rx", std::regex::icase);
const std::regex kQuoted(R"rx(["“”]([^"“”]{2,80})["“”])rx");
const std::regex kFigure(R"rx(\d[\d,]*(?:\.\d+)?)rx");

std::string lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

std::string strip(const std::string& text) {
    auto first = text.find_first_not_of(" \t\r\n\f\v");
    if (first == std::string::npos) return "";
    auto last = text.find_last_not_of(" \t\r\n\f\v");
    return text.substr(first, last - first + 1);
}

std::vector<std::string> split(const std::string& text, const std::regex& pattern) {
    std::vector<std::string> out;
    std::sregex_token_iterator it(text.begin(), text.end(), pattern, -1), end;
    for (; it != end; ++it) out.push_back(it->str());
    return out;
}

std::vector<std::string> tokens(const std::string& text) {
    std::vector<std::string> out;
    for (std::sregex_iterator it(text.begin(), text.end(), kWord), end; it != end; ++it) {
        auto word = lower(it->str());
        auto first = word.find_first_not_of('\'');
        if (first != std::string::npos)
            out.push_back(word.substr(first, word.find_last_not_of('\'') - first + 1));
        else out.push_back("");
    }
    return out;
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
        std::vector<size_t> diff;
        for (size_t i = 0; i < a.size(); ++i) if (a[i] != b[i]) diff.push_back(i);
        return diff.size() == 1 || (diff.size() == 2 && diff[1] == diff[0] + 1 &&
            a[diff[0]] == b[diff[1]] && a[diff[1]] == b[diff[0]]);
    }
    const auto& big = a.size() > b.size() ? a : b;
    const auto& small = a.size() > b.size() ? b : a;
    for (size_t i = 0; i < big.size(); ++i)
        if (big.substr(0, i) + big.substr(i + 1) == small) return true;
    return false;
}

Words forms(const std::string& word) {
    Words out{word, singular(word)};
    if (word.size() > 3 && word.ends_with('s') && !word.ends_with("ss"))
        out.insert(word.substr(0, word.size() - 1));
    return out;
}

Words concepts(const std::vector<std::string>& words, const ConceptTable& table) {
    Words found;
    for (const auto& word : words)
        for (const auto& [concept_name, vocabulary] : table)
            for (const auto& shape : forms(word))
                if (vocabulary.contains(shape)) found.insert(concept_name);
    return found;
}

bool contains_any(const Words& haystack, const Words& needles) {
    for (const auto& word : needles) if (haystack.contains(word)) return true;
    return false;
}

bool transposed(const std::string& a, const std::string& b) {
    if (a.size() != b.size()) return false;
    std::vector<size_t> diff;
    for (size_t i = 0; i < a.size(); ++i) if (a[i] != b[i]) diff.push_back(i);
    return diff.size() == 2 && diff[1] == diff[0] + 1 &&
        a[diff[0]] == b[diff[1]] && a[diff[1]] == b[diff[0]];
}

bool inflection_of(const std::string& word, const std::string& candidate) {
    if (!word.starts_with(candidate)) return false;
    const std::string suffix = word.substr(candidate.size());
    return suffix == "s" || suffix == "d" || suffix == "ed" || suffix == "ing";
}

std::string snap_word(const std::string& raw) {
    const auto word = lower(raw);
    if (word.size() < 4 || kSpellingVocabulary.contains(word) ||
        !std::all_of(word.begin(), word.end(), [](unsigned char c) { return std::isalpha(c); }))
        return raw;
    auto candidates = [&](size_t length, bool transpose_only) {
        std::vector<std::string> out;
        for (const auto& candidate : kSpellingVocabulary) {
            if (candidate.size() != length) continue;
            if (transpose_only ? transposed(word, candidate) :
                (within_one_edit(word, candidate) && !inflection_of(word, candidate)))
                out.push_back(candidate);
        }
        return out;
    };
    if (word.size() == 4) {
        auto near = candidates(4, true);
        return near.size() == 1 ? near[0] : raw;
    }
    for (auto length : {word.size(), word.size() - 1, word.size() + 1}) {
        auto near = candidates(length, false);
        if (!near.empty()) return near.size() == 1 ? near[0] : raw;
    }
    return raw;
}

std::string snap_spelling(const std::string& text) {
    std::string out;
    size_t previous = 0;
    for (std::sregex_iterator it(text.begin(), text.end(), kWord), end; it != end; ++it) {
        const auto& match = *it;
        auto position = static_cast<size_t>(match.position());
        out.append(text, previous, position - previous);
        out += snap_word(match.str());
        previous = position + static_cast<size_t>(match.length());
    }
    out.append(text, previous, std::string::npos);
    return out;
}

struct Capability {
    std::string name;
    Words actions;
    Words resources;
    Words named_resources;
    Words described_verbs;
};

std::vector<std::string> name_parts(const std::string& name) {
    std::vector<std::string> out;
    std::istringstream in{name};
    for (std::string part; std::getline(in, part, '_');) out.push_back(part);
    return out;
}

Capability capability_of(const json& tool) {
    Capability out;
    out.name = json_string(tool, "name");
    auto name_words = name_parts(lower(out.name));
    name_words.erase(std::remove_if(name_words.begin(), name_words.end(),
        [](const auto& word) { return kNameNoise.contains(word); }), name_words.end());
    auto description = json_string(tool, "description");
    description = description.substr(0, description.find('.'));
    const auto described = tokens(description);
    const auto named_actions = concepts(name_words, kActions);
    const auto described_actions = concepts(described, kActions);
    out.actions = named_actions.empty() ? described_actions : named_actions;
    if (!named_actions.empty() && described_actions.contains("compute")) out.actions.insert("compute");
    out.named_resources = concepts(name_words, kResources);
    out.resources = out.named_resources.empty() ? concepts(described, kResources) : out.named_resources;
    if (is_memory_read(out.name)) out.resources.insert("memory");
    for (const auto& word : described)
        for (const auto& [_, vocabulary] : kActions)
            if (vocabulary.contains(word)) out.described_verbs.insert(word);
    return out;
}

struct Catalog {
    std::vector<Capability> capabilities;

    explicit Catalog(const json& tools) {
        if (tools.is_array())
            for (const auto& tool : tools) capabilities.push_back(capability_of(tool));
    }

    std::string find(const std::string& action, const std::string& resource,
                     const std::string& extra = "") const {
        Words wanted{resource};
        if (!extra.empty()) wanted.insert(extra);
        const Capability* best = nullptr;
        std::tuple<size_t, size_t, std::string> best_key;
        for (const auto& cap : capabilities) {
            bool enough = true;
            for (const auto& word : wanted) if (!cap.resources.contains(word)) enough = false;
            if (!enough || !cap.actions.contains(action)) continue;
            size_t symmetric = 0;
            for (const auto& word : cap.named_resources) if (!wanted.contains(word)) ++symmetric;
            for (const auto& word : wanted) if (!cap.named_resources.contains(word)) ++symmetric;
            auto key = std::make_tuple(symmetric, cap.resources.size(), cap.name);
            if (!best || key < best_key) { best = &cap; best_key = key; }
        }
        return best ? best->name : "";
    }

    std::string resource_of_verb(const std::string& verb) const {
        const Capability* owner = nullptr;
        for (const auto& cap : capabilities) {
            if (!cap.described_verbs.contains(verb) || cap.named_resources.empty()) continue;
            if (owner) return "";
            owner = &cap;
        }
        return owner ? *owner->named_resources.begin() : "";
    }
};

struct Step { std::string action; std::string resource; std::string extra; };

std::vector<std::string> clauses_of(const std::string& text) {
    std::vector<std::string> out;
    for (const auto& clause : split(text, kClauseSplit))
        if (!strip(clause).empty()) out.push_back(strip(clause));
    if (out.empty()) out.push_back(text);
    return out;
}

std::string affirmative_text(const std::string& text) {
    std::string result;
    for (const auto& clause : clauses_of(text)) {
        if (std::regex_search(clause, kNegationLead)) continue;
        if (!result.empty()) result += ' ';
        result += clause;
    }
    return result;
}

Words prohibited_resources(const std::string& text) {
    Words banned;
    for (const auto& clause : clauses_of(text)) {
        if (!std::regex_search(clause, kNegationLead)) continue;
        const auto words = tokens(clause);
        auto resources = concepts(words, kResources);
        banned.insert(resources.begin(), resources.end());
        if (concepts(words, kActions).contains("search") && !resources.contains("memory"))
            banned.insert("web");
    }
    return banned;
}

bool question_shaped(const std::string& text) {
    return std::regex_search(std::regex_replace(text, kLeadIns, ""), kQuestionWord);
}

bool underspecified(const std::string& request, const std::vector<Step>& steps) {
    if (steps.empty()) return false;
    Words resource_words = word_set("color update reasoning effort");
    for (const auto& [_, vocabulary] : kResources)
        resource_words.insert(vocabulary.begin(), vocabulary.end());
    const auto words = tokens(request);
    std::vector<std::string> remaining;
    for (const auto& word : words) {
        const auto base = singular(word);
        if (kCourtesy.contains(word) || kCourtesy.contains(base) ||
            kDescriptors.contains(word) || kDescriptors.contains(base) ||
            resource_words.contains(word) || resource_words.contains(base)) continue;
        bool action_word = false;
        for (const auto& [_, vocab] : kActions)
            if (vocab.contains(word) || vocab.contains(base)) action_word = true;
        if (!action_word) remaining.push_back(word);
    }
    const bool deictic = std::any_of(words.begin(), words.end(), [](const auto& word) {
        return kDeictic.contains(word);
    });
    if (deictic && !std::regex_search(request, kQuoted) &&
        !std::regex_search(request, kFigure)) {
        auto count = std::count_if(remaining.begin(), remaining.end(), [](const auto& word) {
            return !kDeictic.contains(word);
        });
        return count <= 1;
    }
    return remaining.empty();
}

std::vector<Step> catalog_steps(const std::string& request, const Catalog& catalog) {
    const auto text = snap_spelling(affirmative_text(request));
    const auto banned = prohibited_resources(snap_spelling(request));
    const auto words = tokens(text);
    const auto actions = concepts(words, kActions);
    auto resources = concepts(words, kResources);
    for (const auto& word : banned) resources.erase(word);
    const bool computing = actions.contains("compute") && std::regex_search(text, kFigure) &&
        !banned.contains("code");
    const Words settings = word_set("effort accent font model theme");
    if (resources.contains("capability") && question_shaped(text) &&
        !(contains_any(resources, settings) && std::regex_search(text,
            std::regex(R"rx(^\s*(?:use|set|switch|make|change)\b)rx", std::regex::icase))))
        return {{"discover", "capability", ""}};
    if (resources.contains("feedback")) return {{"send", "feedback", ""}};
    if (resources.contains("preferences") && resources.contains("tool"))
        return {{"configure", "preferences", ""}};
    if (contains_any(actions, word_set("configure create edit"))) {
        for (const auto& resource : {"effort", "accent", "font", "model", "theme"})
            if (resources.contains(resource)) return {{"configure", resource, ""}};
    }
    if (computing) return {{"compute", "code", ""}};
    if (resources.contains("job") && actions.contains("run") && !resources.contains("workflow"))
        return {{"run", "job", ""}};
    if (resources.contains("calendar"))
        return {{contains_any(actions, word_set("search list")) ? "search" : "create", "calendar", ""}};
    if (resources.contains("memory") && (actions.contains("delete") ||
        std::find(words.begin(), words.end(), "bin") != words.end()))
        return {{"delete", "memory", ""}};
    if (resources.contains("memory") && actions.contains("edit"))
        return {{"edit", "memory", ""}};
    if (std::regex_search(text, std::regex(R"rx(\bremember that\b)rx", std::regex::icase)) &&
        !resources.contains("effort")) return {{"save", "memory", ""}};
    const bool scheduled = resources.contains("schedule") &&
        (resources.contains("workflow") || actions.contains("run"));
    if (resources.contains("workflow") || scheduled) {
        const bool listing = actions.contains("list") || std::regex_search(text,
            std::regex(R"rx(\b(?:what|which|how many)\b)rx", std::regex::icase));
        if (listing && !actions.contains("create"))
            return {{"list", scheduled ? "schedule" : "workflow", ""}};
        if (resources.contains("workflow") && (actions.contains("create") ||
            std::regex_search(text, std::regex(R"rx(\bset up\b)rx", std::regex::icase))))
            return {{"create", "workflow", ""}};
    }
    if (resources.contains("artifact") && actions.contains("create"))
        return {{"create", "artifact", ""}};
    const bool implied = std::any_of(words.begin(), words.end(), [&](const auto& word) {
        return catalog.resource_of_verb(word) == "image" || word == "draw" ||
            word == "sketch" || word == "paint";
    }) && (resources.empty() || resources == Words{"image"});
    if (resources.contains("image") || implied) {
        std::vector<Step> image;
        if (actions.contains("create") || implied) image.push_back({"create", "image", ""});
        if (std::regex_search(text,
                std::regex(R"rx(\b(?:brighten|adjust|crop|sharpen|darken)\b)rx", std::regex::icase)) ||
            (actions.contains("edit") && image.empty()))
            image.push_back({"edit", "image", ""});
        if (!image.empty()) return image;
    }
    const bool searching = contains_any(actions, word_set("search read"));
    const bool asks = std::regex_search(text, kQuestionAnywhere);
    if ((resources.contains("web") && (asks || !actions.empty())) ||
        (searching && resources.contains("link")))
        return {{"search", "web", ""}};
    return {};
}

std::vector<std::string> route_by_catalog(const std::string& request, const Catalog& catalog) {
    const auto steps = catalog_steps(request, catalog);
    if (underspecified(snap_spelling(request), steps)) return {};
    std::vector<std::string> route;
    for (const auto& step : steps) {
        auto name = catalog.find(step.action, step.resource, step.extra);
        if (!name.empty() && std::find(route.begin(), route.end(), name) == route.end())
            route.push_back(name);
    }
    return route;
}

Words tool_terms(const json& tool) {
    const std::string name = json_string(tool, "name");
    Words terms;
    for (const auto& word : name_parts(name)) {
        if (kGenericName.contains(word) || word.size() <= 2) continue;
        auto shapes = forms(word);
        terms.insert(shapes.begin(), shapes.end());
    }
    if (reads_state(name)) {
        const std::map<std::string, std::string> synonyms = {
            {"task", "job"}, {"tasks", "job"}, {"queue", "job"}, {"queued", "job"},
            {"automatic", "schedule"}, {"scheduled", "schedule"},
            {"app", "capabilities"}, {"feature", "capabilities"},
            {"features", "capabilities"}, {"option", "capabilities"},
            {"options", "capabilities"}, {"setting", "capabilities"},
            {"settings", "capabilities"}, {"control", "capabilities"},
            {"switch", "capabilities"}, {"help", "capabilities"},
            {"calendar", "calendar"}, {"web", "web"},
            {"online", "web"}, {"internet", "web"}};
        for (const auto& [word, capability] : synonyms)
            if (terms.contains(capability)) terms.insert(word);
    }
    return terms;
}

Words addressed_verbs(const std::string& request) {
    Words out;
    for (const auto& clause : split(request, kClauseSplit)) {
        if (strip(clause).empty()) continue;
        std::smatch lead;
        if (std::regex_search(clause, lead, kVerbInitial,
            std::regex_constants::match_continuous)) {
            auto word = lower(lead[1].str());
            if (kLooseSynonyms.contains(word)) out.insert(singular(word));
        }
    }
    return out;
}

}  // namespace

json action_tools(const json& catalog, const std::string& message) {
    if (!catalog.is_array()) return json::array();
    const Catalog route_catalog(catalog);
    const auto route = route_by_catalog(message, route_catalog);
    Words message_words;
    for (const auto& word : tokens(message)) message_words.insert(singular(word));
    for (const auto& word : addressed_verbs(message)) message_words.erase(word);
    std::vector<std::pair<size_t, json>> ordered;
    for (size_t i = 0; i < catalog.size(); ++i) ordered.emplace_back(i, catalog[i]);
    std::stable_sort(ordered.begin(), ordered.end(), [&](const auto& left, const auto& right) {
        auto key = [&](const auto& item) {
            const auto name = json_string(item.second, "name");
            auto route_it = std::find(route.begin(), route.end(), name);
            const size_t route_rank = route_it == route.end() ? route.size() :
                static_cast<size_t>(std::distance(route.begin(), route_it));
            size_t matches = 0;
            for (const auto& term : tool_terms(item.second))
                if (message_words.contains(term)) ++matches;
            return std::make_tuple(route_rank, matches ? 0 : 1,
                -static_cast<int>(matches), matches && reads_state(name) ? 0 : 1,
                item.first);
        };
        return key(left) < key(right);
    });
    json output = json::array();
    for (const auto& [_, tool] : ordered) {
        const auto name = json_string(tool, "name");
        const auto description = json_string(tool, "description");
        json parameters = json::object();
        if (tool.is_object() && tool.contains("parameters") &&
            tool["parameters"].is_object() && !tool["parameters"].empty())
            parameters = tool["parameters"];
        else parameters = {{"type", "object"}, {"properties", json::object()}};
        output.push_back({{"type", "function"},
            {"function", {{"name", name},
                          {"description", description.empty() ? name : description},
                          {"parameters", parameters}}}});
    }
    return output;
}

}  // namespace ditto
