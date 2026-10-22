#include "deliberation.hpp"

#include <algorithm>
#include <cctype>

namespace ditto {
namespace {

std::string strip(const std::string& s) {
    auto first = s.find_first_not_of(" \t\r\n\f\v");
    if (first == std::string::npos) return {};
    return s.substr(first, s.find_last_not_of(" \t\r\n\f\v") - first + 1);
}

std::string utf8_prefix(const std::string& s, std::size_t codepoints) {
    std::size_t offset = 0, count = 0;
    while (offset < s.size() && count < codepoints) {
        const auto byte = static_cast<unsigned char>(s[offset]);
        std::size_t width = (byte & 0x80) == 0 ? 1 : (byte & 0xe0) == 0xc0 ? 2 :
                            (byte & 0xf0) == 0xe0 ? 3 : (byte & 0xf8) == 0xf0 ? 4 : 1;
        offset = std::min(s.size(), offset + width);
        ++count;
    }
    return s.substr(0, offset);
}

std::string python_json(const json& value) {
    const auto compact = value.dump(-1, ' ', false, json::error_handler_t::replace);
    std::string out;
    out.reserve(compact.size() + compact.size() / 8);
    bool quoted = false, escaped = false;
    for (char c : compact) {
        out.push_back(c);
        if (escaped) { escaped = false; continue; }
        if (quoted && c == '\\') { escaped = true; continue; }
        if (c == '"') { quoted = !quoted; continue; }
        if (!quoted && (c == ',' || c == ':')) out.push_back(' ');
    }
    return out;
}

}  // namespace

std::string DeliberationPolicy::shape_skip(int records, bool names_identifier,
                                           bool statement, bool names_value) const {
    if (drafts < 2) return "fewer than two drafts configured";
    if (records < 1) return "no records to check against";
    if (names_identifier) return "the message names an identifier its records carry";
    if (statement) return "the message states something and asks nothing";
    if (!names_value) return "the message names no value its records hold, and no full name, address, code or quoted words";
    return {};
}

std::string DeliberationPolicy::skip_reason(int records, double seconds_left,
                                            int turns_left, bool names_identifier,
                                            bool statement, bool names_value) const {
    if (auto reason = shape_skip(records, names_identifier, statement, names_value);
        !reason.empty()) return reason;
    if (seconds_left < kDeliberationMinSeconds)
        return std::to_string(static_cast<int>(seconds_left)) + " s left";
    if (turns_left < 1) return "no turn left";
    return {};
}

std::optional<int> DeliberationPolicy::draft_seed(int index) const {
    return seed ? std::optional<int>(*seed + index - 1) : std::nullopt;
}

std::vector<int> DeliberationPolicy::indexes() const {
    std::vector<int> out;
    for (int index = 2; index <= drafts; ++index) out.push_back(index);
    return out;
}

double DeliberationPolicy::draft_deadline(double now, double deadline) const {
    return now + kDraftBudgetShare * (deadline - now);
}

std::string reply_shape(const ModelResult& result) {
    if (!result.calls.empty()) {
        std::string out = "call ";
        for (std::size_t i = 0; i < result.calls.size(); ++i) {
            if (i) out += ", ";
            out += result.calls[i].name + utf8_prefix(python_json(result.calls[i].args), 120);
        }
        return out;
    }
    if (result.finish == "length") return "length";
    return strip(result.content).empty() ? "empty" : "text";
}

std::string draft_slot(int index, const ModelResult& reply) {
    const auto number = std::to_string(index);
    if (reply.finish == "length") return "Draft " + number + ": cut off at the length limit.";
    auto content = strip(reply.content);
    if (content.empty()) return "Draft " + number + ": came back without text.";
    return "Draft " + number + ":\n" + content;
}

std::string failed_draft_slot(int index) {
    return "Draft " + std::to_string(index) + ": no reply (the request failed).";
}

std::string deliberation_brief(const std::vector<std::string>& slots) {
    std::string out = "Before you reply, here are " + std::to_string(slots.size()) +
        " drafts of a reply to the message above, each written separately from the same records. They have not been checked, and any of them may be wrong.\n\n";
    for (std::size_t i = 0; i < slots.size(); ++i) {
        if (i) out += "\n\n";
        out += slots[i];
    }
    out += "\n\nNow write the reply the user will get. Where drafts disagree, or a record says otherwise, the records decide. If none of the records states what was asked, say plainly that you have no record of it, and say which records you did check by naming who or what each one is about — not by its label, and without repeating its contents or figures. Do the checking before you reply, not in the reply. When you do answer, state no other value than the one you answer with. You may keep a refusal or say you are unsure, you may set aside anything a draft suggests, and you may call a tool or reply without calling anything, as the message needs. Write to the user, not about the drafts.";
    return out;
}

}  // namespace ditto
