#include "output.hpp"

#include <unicode/uchar.h>
#include <unicode/utf8.h>

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>

namespace ditto {
namespace {

struct Rune {
    UChar32 value;
    std::size_t next;
};

Rune rune_at(const std::string_view text, const std::size_t at) {
    if (at >= text.size()) return {U_SENTINEL, text.size()};
    int32_t cursor = static_cast<int32_t>(at);
    UChar32 value = U_SENTINEL;
    U8_NEXT(text.data(), cursor, static_cast<int32_t>(text.size()), value);
    if (value < 0) return {static_cast<unsigned char>(text[at]), at + 1};
    return {value, static_cast<std::size_t>(cursor)};
}

UChar32 rune_before(const std::string_view text, const std::size_t at) {
    if (at == 0) return U_SENTINEL;
    int32_t cursor = static_cast<int32_t>(at);
    UChar32 value = U_SENTINEL;
    U8_PREV(text.data(), 0, cursor, value);
    return value < 0 ? static_cast<unsigned char>(text[at - 1]) : value;
}

bool python_space(const UChar32 value) {
    return (value >= 0x09 && value <= 0x0d) ||
           (value >= 0x1c && value <= 0x20) || value == 0x85 ||
           value == 0xa0 || value == 0x1680 ||
           (value >= 0x2000 && value <= 0x200a) ||
           value == 0x2028 || value == 0x2029 || value == 0x202f ||
           value == 0x205f || value == 0x3000;
}

bool python_word(const UChar32 value) {
    if (value == '_') return true;
    const auto category = u_charType(value);
    return category == U_UPPERCASE_LETTER || category == U_LOWERCASE_LETTER ||
           category == U_TITLECASE_LETTER || category == U_MODIFIER_LETTER ||
           category == U_OTHER_LETTER || category == U_DECIMAL_DIGIT_NUMBER ||
           category == U_LETTER_NUMBER || category == U_OTHER_NUMBER;
}

bool decimal_digit(const UChar32 value) {
    return value >= 0 && u_charType(value) == U_DECIMAL_DIGIT_NUMBER;
}

bool ascii_alnum(const char value) {
    return (value >= 'a' && value <= 'z') ||
           (value >= 'A' && value <= 'Z') ||
           (value >= '0' && value <= '9');
}

bool ascii_alpha(const char value) {
    return (value >= 'a' && value <= 'z') ||
           (value >= 'A' && value <= 'Z');
}

std::string plain_hyphens(const std::string& text) {
    std::string result;
    result.reserve(text.size());
    for (std::size_t i = 0; i < text.size();) {
        if (i + 3 <= text.size() &&
            (text.compare(i, 3, "\xe2\x80\x90") == 0 ||
             text.compare(i, 3, "\xe2\x80\x91") == 0) &&
            ((i > 0 && ascii_alnum(text[i - 1])) ||
             (i + 3 < text.size() && ascii_alpha(text[i + 3])))) {
            result.push_back('-');
            i += 3;
        } else {
            result.push_back(text[i++]);
        }
    }
    return result;
}

bool has_nonspace_after(const std::string_view text, std::size_t at) {
    while (at < text.size()) {
        const auto current = rune_at(text, at);
        if (!python_space(current.value)) return true;
        at = current.next;
    }
    return false;
}

bool figure(const std::string_view text) {
    std::size_t at = 0;
    if (text.empty()) return false;
    auto current = rune_at(text, at);
    if (current.value == '$' || current.value == 0x20ac || current.value == 0xa3) {
        at = current.next;
        current = rune_at(text, at);
    }
    if (!decimal_digit(current.value)) return false;
    at = current.next;
    while (at < text.size()) {
        current = rune_at(text, at);
        if (decimal_digit(current.value) || current.value == ',')
            at = current.next;
        else
            break;
    }
    if (at < text.size() && text[at] == '.') {
        at++;
        current = rune_at(text, at);
        if (!decimal_digit(current.value)) return false;
        at = current.next;
        while (at < text.size()) {
            current = rune_at(text, at);
            if (!decimal_digit(current.value)) break;
            at = current.next;
        }
    }
    if (at < text.size() && text[at] == '%') at++;
    return at == text.size();
}

std::string unbold_segment(const std::string_view text) {
    std::string result;
    result.reserve(text.size());
    for (std::size_t at = 0; at < text.size();) {
        if (at + 2 <= text.size() && text.substr(at, 2) == "**" &&
            (at == 0 || (!python_word(rune_before(text, at)) &&
                         rune_before(text, at) != '*'))) {
            const std::size_t inner = at + 2;
            const auto first = rune_at(text, inner);
            if (first.value != U_SENTINEL && first.value != '*' &&
                !python_space(first.value)) {
                std::size_t close = inner;
                while (close < text.size() && text[close] != '\n') {
                    if (close > inner && close + 2 <= text.size() &&
                        text.substr(close, 2) == "**" &&
                        rune_before(text, close) != '*' &&
                        !python_space(rune_before(text, close)) &&
                        (close + 2 == text.size() ||
                         (rune_at(text, close + 2).value != '*' &&
                          !python_word(rune_at(text, close + 2).value)))) {
                        const auto value = text.substr(inner, close - inner);
                        const auto after = close + 2;
                        const bool protected_figure = figure(value) &&
                            after < text.size() &&
                            (text[after] == '.' || text[after] == ',') &&
                            has_nonspace_after(text, after + 1);
                        result.append(protected_figure ? text.substr(at, after - at) : value);
                        at = after;
                        break;
                    }
                    close++;
                }
                if (at != inner - 2) continue;
            }
        }
        result.push_back(text[at++]);
    }
    return result;
}

std::string plain_emphasis(const std::string& text) {
    std::string result;
    std::size_t last = 0;
    std::size_t cursor = 0;
    while (cursor < text.size()) {
        const auto begin = text.find('`', cursor);
        if (begin == std::string::npos) break;
        std::size_t end = std::string::npos;
        if (text.compare(begin, 3, "```") == 0) {
            const auto fence = text.find("```", begin + 3);
            if (fence != std::string::npos) end = fence + 3;
        }
        if (end == std::string::npos) {
            const auto next = text.find_first_of("`\n", begin + 1);
            if (next != std::string::npos && text[next] == '`') end = next + 1;
        }
        if (end == std::string::npos) {
            cursor = begin + 1;
            continue;
        }
        result += unbold_segment(std::string_view(text).substr(last, begin - last));
        result.append(text, begin, end - begin);
        last = end;
        cursor = end;
    }
    result += unbold_segment(std::string_view(text).substr(last));
    return result;
}

std::string trim_python(const std::string_view text) {
    std::size_t first = 0;
    std::size_t last_nonspace = 0;
    bool seen = false;
    while (first < text.size()) {
        const auto current = rune_at(text, first);
        if (!python_space(current.value)) {
            if (!seen) {
                seen = true;
                last_nonspace = first;
            }
            last_nonspace = current.next;
        } else if (!seen) {
            first = current.next;
            continue;
        }
        first = current.next;
    }
    if (!seen) return {};
    std::size_t begin = 0;
    while (begin < text.size() && python_space(rune_at(text, begin).value))
        begin = rune_at(text, begin).next;
    return std::string(text.substr(begin, last_nonspace - begin));
}

void skip_space(const std::string_view text, std::size_t& at) {
    while (at < text.size()) {
        const auto current = rune_at(text, at);
        if (!python_space(current.value)) break;
        at = current.next;
    }
}

bool consume_answer(const std::string_view text, std::size_t& at) {
    constexpr std::string_view word = "ANSWER";
    if (at + word.size() > text.size()) return false;
    for (std::size_t i = 0; i < word.size(); ++i) {
        char got = text[at + i];
        if (got >= 'a' && got <= 'z') got -= 'a' - 'A';
        if (got != word[i]) return false;
    }
    at += word.size();
    return true;
}

std::optional<std::string> match_slot(std::string_view line) {
    const auto stripped = trim_python(line);
    std::string unquoted;
    if (!stripped.empty() && stripped.front() == '`') {
        std::size_t first = 0;
        std::size_t last = stripped.size();
        while (first < last && stripped[first] == '`') first++;
        while (last > first && stripped[last - 1] == '`') last--;
        unquoted = stripped.substr(first, last - first);
        line = unquoted;
    }
    std::size_t at = 0;
    skip_space(line, at);
    std::string_view wrapper;
    if (at < line.size() && (line[at] == '*' || line[at] == '_')) {
        const auto begin = at;
        at++;
        if (at < line.size() && line[at] == line[begin]) at++;
        wrapper = line.substr(begin, at - begin);
    }
    if (!consume_answer(line, at)) return std::nullopt;
    skip_space(line, at);
    if (wrapper.empty()) {
        if (at >= line.size() || line[at] != ':') return std::nullopt;
        at++;
    } else if (line.substr(at, wrapper.size()) == wrapper) {
        at += wrapper.size();
        skip_space(line, at);
        if (at >= line.size() || line[at] != ':') return std::nullopt;
        at++;
    } else {
        if (at >= line.size() || line[at] != ':') return std::nullopt;
        at++;
        skip_space(line, at);
        if (line.substr(at, wrapper.size()) != wrapper) return std::nullopt;
        at += wrapper.size();
    }
    skip_space(line, at);
    std::string value = trim_python(line.substr(at));
    const auto first = value.find_first_not_of(" \t`*");
    if (first == std::string::npos) return std::string();
    const auto last = value.find_last_not_of(" \t`*");
    return value.substr(first, last - first + 1);
}

bool line_separator(const UChar32 value) {
    return value == '\n' || value == '\r' || value == '\v' || value == '\f' ||
           (value >= 0x1c && value <= 0x1e) || value == 0x85 ||
           value == 0x2028 || value == 0x2029;
}

}  // namespace

std::string plain_type(const std::string& text) {
    return plain_emphasis(plain_hyphens(text));
}

std::pair<std::string, std::optional<std::string>> parse_slot(
    const std::string& text) {
    std::optional<std::string> answer;
    std::size_t start = 0;
    for (std::size_t at = 0; at < text.size();) {
        const auto current = rune_at(text, at);
        if (line_separator(current.value)) {
            if (auto value = match_slot(std::string_view(text).substr(start, at - start)))
                answer = std::move(value);
            at = current.next;
            if (current.value == '\r' && at < text.size() && text[at] == '\n') at++;
            start = at;
        } else {
            at = current.next;
        }
    }
    if (start < text.size()) {
        if (auto value = match_slot(std::string_view(text).substr(start)))
            answer = std::move(value);
    }
    return {trim_python(text), std::move(answer)};
}

}  // namespace ditto
