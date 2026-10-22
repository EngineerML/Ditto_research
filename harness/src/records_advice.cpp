#include "records_advice.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <iterator>
#include <map>
#include <regex>
#include <sstream>
#include <utility>

#include "local_helpers.hpp"
#include "retrieval.hpp"

namespace ditto {
namespace {

constexpr double kSearchBudgetShare = 0.35;
constexpr double kSearchMinSeconds = 20.0;
constexpr int kSearchFirstLineChars = 160;
constexpr int kIdentifierSearchPasses = 6;
constexpr int kClosestMinTerms = 2;
constexpr int kClosestMinRecords = 2;
constexpr int kClosestMaxRecords = 8;
constexpr int kClosestLongChars = 1500;
constexpr int kClosestLongRecords = 2;

std::string strip(const std::string& text) {
    auto first = text.find_first_not_of(" \t\r\n\f\v");
    if (first == std::string::npos) return "";
    auto last = text.find_last_not_of(" \t\r\n\f\v");
    return text.substr(first, last - first + 1);
}

size_t codepoints(const std::string& text) {
    return static_cast<size_t>(std::count_if(text.begin(), text.end(), [](unsigned char c) {
        return (c & 0xc0u) != 0x80u;
    }));
}

std::string first_codepoints(const std::string& text, size_t limit) {
    size_t seen = 0;
    size_t end = 0;
    while (end < text.size()) {
        if ((static_cast<unsigned char>(text[end]) & 0xc0u) != 0x80u) {
            if (seen == limit) break;
            ++seen;
        }
        ++end;
    }
    return text.substr(0, end);
}

std::string first_line(const std::string& text) {
    std::istringstream in{text};
    std::string line;
    while (std::getline(in, line)) {
        line = strip(line);
        if (line.empty()) continue;
        if (codepoints(line) <= kSearchFirstLineChars) return line;
        return strip(first_codepoints(line, kSearchFirstLineChars)) + "...";
    }
    return "";
}

std::string prompt(const json& prompts, const char* group, const char* name) {
    if (!prompts.is_object() || !prompts.contains(group)) return "";
    return json_string(prompts[group], name);
}

std::string records_system(const RunRequest& request, const json& prompts,
                           const SearchOptions& options, bool search) {
    std::string system;
    if (search) system = prompt(prompts, "records", "SEARCH_SYSTEM") + "\n";
    system += prompt(prompts, "records", "MEMORY_LANE_SYSTEM");
    if (options.subject_discipline)
        system += "\n" + prompt(prompts, "records", "SUBJECT_DISCIPLINE");
    if (options.thread_reading)
        system += "\n" + prompt(prompts, "records", "THREAD_READING");
    const auto op = strip(request.system_prompt);
    if (!op.empty())
        system += "\n\n" + prompt(prompts, "action", "OPERATOR_SEAM") + "\n" + op;
    return system;
}

std::string search_brief(const json& prompts, const std::string& index,
                         const std::string& question) {
    const std::string pattern = prompt(prompts, "records", "SEARCH_BRIEF");
    std::string brief;
    for (size_t i = 0; i < pattern.size();) {
        if (pattern.compare(i, 7, "{index}") == 0) {
            brief += index;
            i += 7;
        } else if (pattern.compare(i, 9, "{message}") == 0) {
            brief += question;
            i += 9;
        } else {
            brief += pattern[i++];
        }
    }
    return brief;
}

std::vector<std::string> identifier_tokens(const std::string& text) {
    std::vector<std::string> found;
    std::string lower = text;
    std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    static const std::regex identifier(
        R"rx(\b(?=[0-9a-z]*[0-9])(?=[0-9a-z]*[a-z])[0-9a-z]{12,}\b)rx");
    for (std::sregex_iterator it(lower.begin(), lower.end(), identifier), end;
         it != end; ++it) found.push_back(it->str());
    return found;
}

bool focused_on_identifier(const RunRequest& request, const Packet& packet) {
    for (const auto& token : identifier_tokens(request.user_input)) {
        int carrying = 0;
        for (const auto& pair : packet.records) {
            std::string text = pair.prompt + " " + pair.response;
            std::transform(text.begin(), text.end(), text.begin(), [](unsigned char c) {
                return static_cast<char>(std::tolower(c));
            });
            if (text.find(token) != std::string::npos && ++carrying >= 3) return true;
        }
    }
    return false;
}

}  // namespace

SearchPlan plan_records_search(const RunRequest& request, const Packet& packet,
                               const json& prompts, double seconds_left,
                               const SearchOptions& options) {
    SearchPlan plan;
    const int long_records = static_cast<int>(std::count_if(
        packet.records.begin(), packet.records.end(), [&](const auto& pair) {
            return codepoints(pair.prompt) + codepoints(pair.response) >=
                static_cast<size_t>(std::max(0, options.search_record_chars));
        }));
    plan.holds_long = options.search_long_records >= 1 &&
        long_records >= options.search_long_records;
    const bool focus = focused_on_identifier(request, packet);
    plan.short_identifier = !plan.holds_long && focus;
    plan.searchable = plan.holds_long || focus;
    const bool finder_supplied = request.tools.is_array() &&
        std::any_of(request.tools.begin(), request.tools.end(), [](const auto& tool) {
            return json_string(tool, "name") == "find_in_records";
        });
    plan.finder = (plan.searchable || packet.focused) && !finder_supplied;
    plan.budget_seconds = kSearchBudgetShare * seconds_left;
    plan.should_run = plan.finder && plan.budget_seconds >= kSearchMinSeconds;
    if (!plan.finder) return plan;
    for (size_t i = 0; i < packet.records.size(); ++i) {
        const auto& pair = packet.records[i];
        if (i) plan.index += '\n';
        plan.index += "[M" + std::to_string(i + 1) + "] " + first_line(pair.prompt) +
            " (" + std::to_string(codepoints(pair.prompt) + codepoints(pair.response)) +
            " characters)";
    }
    plan.question = plan.short_identifier ?
        asked_part(request.user_input, identifier_tokens(request.user_input)) :
        request.user_input;
    plan.messages = json::array({{{"role", "system"},
                                  {"content", records_system(request, prompts, options, true)}},
                                 {{"role", "user"},
                                  {"content", search_brief(prompts, plan.index, plan.question)}}});
    plan.tools = json::array({find_tool_definition(options.finder_order),
                              calculate_tool_definition()});
    const int count = plan.short_identifier ?
        std::max(options.search_passes, kIdentifierSearchPasses) :
        options.search_passes;
    for (int which = 1; which <= std::max(1, count); ++which) {
        SearchPass pass;
        pass.which = which;
        if (which > 1) {
            if (!plan.short_identifier) pass.temperature = options.search_temperature;
            if (options.search_seed) pass.seed = *options.search_seed + which - 1;
        }
        plan.passes.push_back(pass);
    }
    return plan;
}

json search_note_messages(const std::string& first_note,
                          const std::vector<SearchNote>& later_notes) {
    json messages = json::array();
    const auto first = strip(first_note);
    if (!first.empty()) {
        messages.push_back({{"role", "user"},
            {"content", "Before this reply, a search pass that saw only the message and the searches above wrote the note below. It has not been checked, and the records decide wherever they differ from it:\n" + first}});
    }
    std::string more;
    for (const auto& item : later_notes) {
        const auto note = strip(item.note);
        if (note.empty()) continue;
        if (!more.empty()) more += "\n\n";
        more += "Note of search pass " + std::to_string(item.which) + ":\n" + note;
    }
    if (!more.empty()) {
        messages.push_back({{"role", "user"},
            {"content", "Separate search passes over the same message and the same records wrote the notes below. They have not been checked, and the records decide wherever they differ from them.\n\n" + more}});
    }
    return messages;
}

Packet closest_records(const Packet& packet,
                       const std::vector<std::set<std::string>>& term_holders) {
    Packet closest;
    if (term_holders.size() < kClosestMinTerms) return closest;
    std::set<std::string> common = term_holders.front();
    for (size_t i = 1; i < term_holders.size(); ++i) {
        std::set<std::string> next;
        std::set_intersection(common.begin(), common.end(),
                              term_holders[i].begin(), term_holders[i].end(),
                              std::inserter(next, next.begin()));
        common = std::move(next);
    }
    for (const auto& pair : packet.records)
        if (common.contains(pair.pair_id)) closest.records.push_back(pair);
    if (closest.records.size() < kClosestMinRecords ||
        closest.records.size() > kClosestMaxRecords) return {};
    const int long_count = static_cast<int>(std::count_if(
        closest.records.begin(), closest.records.end(), [](const auto& pair) {
            return codepoints(pair.prompt) + codepoints(pair.response) >=
                kClosestLongChars;
        }));
    if (long_count < kClosestLongRecords) return {};
    return closest;
}

bool records_timeline_shape(const RunRequest& request, const Packet& packet,
                            bool statement, bool names_value, int drafts) {
    return drafts >= 2 && !packet.records.empty() &&
        !focused_on_identifier(request, packet) && !statement && names_value;
}

bool records_timeline_ready(const RunRequest& request, const Packet& packet,
                            bool statement, bool names_value,
                            double seconds_left, int drafts) {
    return records_timeline_shape(request, packet, statement, names_value, drafts) &&
        seconds_left >= kSearchMinSeconds;
}

json timeline_note_message(const std::string& note) {
    const auto clean = strip(note);
    if (clean.empty()) return json::array();
    return json::array({{{"role", "user"},
        {"content", "A separate reading pass over the same records listed what they say about the subject of the message, below. It has not been checked, and the records decide wherever they differ from it:\n" + clean}}});
}

json closest_reading_messages(const RunRequest& request, const Packet& closest,
                              const Packet& full, const json& prompts,
                              const SearchOptions& options) {
    if (closest.records.empty()) return json::array();
    std::map<std::string, std::string> labels;
    for (size_t i = 0; i < full.records.size(); ++i)
        labels[full.records[i].pair_id] = "M" + std::to_string(i + 1);
    return json::array({{{"role", "system"},
                         {"content", records_system(request, prompts, options, false)}},
                        {{"role", "user"},
                         {"content", compose_subset(closest.records, request.user_input, labels)}}});
}

json closest_reading_note(const Packet& closest, const Packet& full,
                          const std::string& note) {
    const auto clean = strip(note);
    if (closest.records.empty() || clean.empty()) return json::array();
    std::map<std::string, std::string> labels;
    for (size_t i = 0; i < full.records.size(); ++i)
        labels[full.records[i].pair_id] = "M" + std::to_string(i + 1);
    std::string marks;
    for (const auto& pair : closest.records) {
        auto it = labels.find(pair.pair_id);
        if (it == labels.end()) continue;
        if (!marks.empty()) marks += ", ";
        marks += it->second;
    }
    return json::array({{{"role", "user"},
        {"content", "A separate reading pass saw only the records " + marks +
            ", the ones that hold every distinctive word of the message, and wrote the note below. It has not been checked, and the records decide wherever they differ from it:\n" + clean}}});
}

json timeline_messages(const RunRequest& request, const std::string& composed,
                       const json& prompts, const SearchOptions& options) {
    return json::array({{{"role", "system"},
                         {"content", records_system(request, prompts, options, false)}},
                        {{"role", "user"}, {"content", composed}},
                        {{"role", "user"},
                         {"content", prompt(prompts, "records", "TIMELINE_BRIEF")}}});
}

}  // namespace ditto
