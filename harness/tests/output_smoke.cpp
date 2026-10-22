#include "output.hpp"

#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(const bool condition, const std::string& detail) {
    if (!condition) throw std::runtime_error("output check failed: " + detail);
}
}

int main() {
    using ditto::parse_slot;
    using ditto::plain_type;

    // Exercise typography normalization across Markdown and Unicode boundaries.
    const std::vector<std::pair<std::string, std::string>> typography = {
        {"**hello** world", "hello world"},
        {"The **value** is **42**. Next step", "The value is **42**. Next step"},
        {"The **value** is **42**.", "The value is 42."},
        {"`**code**` then **text**", "`**code**` then text"},
        {"```\n**code**\n``` **text**", "```\n**code**\n``` text"},
        {"foo**bold** bar", "foo**bold** bar"},
        {"é**bold** z", "é**bold** z"},
        {"_**bold**_", "_**bold**_"},
        {"A‐B A‑B ‐A 7‑9 ‐7", "A-B A-B -A 7-9 ‐7"},
        {"`A‑B **code**` **42**. next", "`A-B **code**` **42**. next"},
        {"**€42**. next", "**€42**. next"},
        {"**€42**. ", "€42. "},
        {"**a b** ok", "a b ok"},
        {"**a\nb**", "**a\nb**"},
        {"```unclosed **bold**", "```unclosed bold"},
        {"`` **hi**", "`` hi"},
    };
    for (const auto& [input, expected] : typography)
        require(plain_type(input) == expected, "typography: " + input);

    // Exercise completion trimming and final answer-slot extraction.
    struct SlotCase {
        std::string input;
        std::string stripped;
        std::optional<std::string> answer;
    };
    const std::vector<SlotCase> slots = {
        {"ANSWER: **42**", "ANSWER: **42**", "42"},
        {"**ANSWER:** *foo*", "**ANSWER:** *foo*", "foo"},
        {"**ANSWER**: foo", "**ANSWER**: foo", "foo"},
        {"`ANSWER: `42``", "`ANSWER: `42``", "42"},
        {"answer :  x  \nANSWER: y", "answer :  x  \nANSWER: y", "y"},
        {"ANSWER: ", "ANSWER:", ""},
        {"ANSWER: a\u2028ANSWER: b", "ANSWER: a\u2028ANSWER: b", "b"},
        {"x\n`ANSWER: foo`\n", "x\n`ANSWER: foo`", "foo"},
        {"ANSWER: __foo__", "ANSWER: __foo__", "__foo__"},
        {"__ANSWER__: 42", "__ANSWER__: 42", "42"},
        {"ANSWER: \u00a042\u00a0", "ANSWER: \u00a042", "42"},
        {"No answer slot here", "No answer slot here", std::nullopt},
    };
    for (const auto& item : slots) {
        const auto [stripped, answer] = parse_slot(item.input);
        require(stripped == item.stripped, "completion trim: " + item.input);
        require(answer == item.answer, "answer slot: " + item.input);
    }
}
