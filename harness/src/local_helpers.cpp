#include "local_helpers.hpp"

#include <algorithm>
#include <cmath>
#include <cctype>
#include <cstdlib>
#include <iomanip>
#include <limits>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <unicode/normalizer2.h>
#include <unicode/uchar.h>
#include <unicode/unistr.h>
#include <unicode/utf16.h>
#include <unicode/utf8.h>

namespace ditto {
namespace {

constexpr std::size_t kMaxExpressionChars = 400;
constexpr std::size_t kMaxTerms = 24;
constexpr std::size_t kMaxTermChars = 240;
constexpr double kMaxAbsValue = 1e15;
constexpr int kMaxRoundPlaces = 15;
constexpr int kMaxFindTexts = 4;
constexpr std::size_t kMaxTextChars = 200;
constexpr std::size_t kMaxParts = 30;
constexpr std::size_t kMaxResultChars = 12000;

class CalcError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

std::string trim(const std::string& text) {
    std::size_t first = 0, last = text.size();
    while (first < last && std::isspace(static_cast<unsigned char>(text[first]))) ++first;
    while (last > first && std::isspace(static_cast<unsigned char>(text[last - 1]))) --last;
    return text.substr(first, last - first);
}

std::size_t char_count(const std::string& text) {
    std::size_t n = 0;
    for (unsigned char c : text) if ((c & 0xc0) != 0x80) ++n;
    return n;
}

std::string prefix_chars(const std::string& text, std::size_t limit) {
    std::size_t pos = 0, count = 0;
    while (pos < text.size() && count < limit) {
        unsigned char c = static_cast<unsigned char>(text[pos]);
        pos = std::min(text.size(), pos + ((c < 0x80) ? 1 : (c < 0xe0) ? 2 : (c < 0xf0) ? 3 : 4));
        ++count;
    }
    return text.substr(0, pos);
}

void replace_all(std::string& text, const std::string& from, const std::string& to) {
    if (from.empty()) return;
    std::size_t pos = 0;
    while ((pos = text.find(from, pos)) != std::string::npos) {
        text.replace(pos, from.size(), to);
        pos += to.size();
    }
}

std::string py_string(const json& value) {
    if (value.is_string()) return value.get<std::string>();
    if (value.is_null()) return "None";
    if (value.is_boolean()) return value.get<bool>() ? "True" : "False";
    return value.dump();
}

bool truthy(const json& value) {
    if (value.is_null()) return false;
    if (value.is_boolean()) return value.get<bool>();
    if (value.is_number()) return value.get<double>() != 0;
    if (value.is_string()) return !value.get_ref<const std::string&>().empty();
    if (value.is_array() || value.is_object()) return !value.empty();
    return false;
}

json first_truthy(const json& args, const char* a, const char* b = nullptr) {
    if (!args.is_object()) return "";
    auto it = args.find(a);
    if (it != args.end() && truthy(*it)) return *it;
    if (b) {
        it = args.find(b);
        if (it != args.end() && truthy(*it)) return *it;
    }
    return "";
}

bool digit(char c) { return c >= '0' && c <= '9'; }
bool letter(char c) { return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z'); }

bool currency_before(const std::string& text, std::size_t start) {
    while (start > 0 && text[start - 1] == ' ') --start;
    for (const std::string mark : {"$", "€", "£", "¥"}) {
        if (start >= mark.size() && text.compare(start - mark.size(), mark.size(), mark) == 0) return true;
    }
    return false;
}

bool list_call_without_spaced_separator(const std::string& text, std::size_t start) {
    std::size_t opener = std::string::npos;
    int depth = 0;
    for (std::size_t i = start; i-- > 0;) {
        if (text[i] == ')') ++depth;
        else if (text[i] == '(') {
            if (depth == 0) { opener = i; break; }
            --depth;
        }
    }
    if (opener == std::string::npos) return false;
    std::size_t end = opener;
    while (end > 0 && std::isspace(static_cast<unsigned char>(text[end - 1]))) --end;
    std::size_t begin = end;
    while (begin > 0 && letter(text[begin - 1])) --begin;
    const std::string name = text.substr(begin, end - begin);
    if (name != "sum" && name != "min" && name != "max") return false;
    if (begin > 0 && (letter(text[begin - 1]) || digit(text[begin - 1]) || text[begin - 1] == '_')) return false;
    int nested = 0;
    for (std::size_t i = opener + 1; i < text.size(); ++i) {
        if (text[i] == '(') ++nested;
        else if (text[i] == ')') {
            if (nested == 0) break;
            --nested;
        } else if (text[i] == ',' && nested == 0 && i + 1 < text.size() &&
                   std::isspace(static_cast<unsigned char>(text[i + 1]))) return false;
    }
    return true;
}

std::pair<std::string, bool> read_commas(const std::string& expression) {
    std::string out;
    bool split = false;
    std::size_t i = 0;
    while (i < expression.size()) {
        if (!digit(expression[i]) || (i && (digit(expression[i - 1]) || expression[i - 1] == '.'))) {
            out.push_back(expression[i++]);
            continue;
        }
        std::size_t first_end = i;
        while (first_end < expression.size() && digit(expression[first_end])) ++first_end;
        if (first_end - i > 3) { out.append(expression, i, first_end - i); i = first_end; continue; }
        std::size_t end = first_end;
        bool grouped = false;
        bool leading_zero_group = false;
        while (end + 4 <= expression.size() && expression[end] == ',' &&
               digit(expression[end + 1]) && digit(expression[end + 2]) && digit(expression[end + 3]) &&
               (end + 4 == expression.size() || !digit(expression[end + 4]))) {
            grouped = true;
            if (expression[end + 1] == '0') leading_zero_group = true;
            end += 4;
        }
        if (!grouped) { out.append(expression, i, first_end - i); i = first_end; continue; }
        bool decimal = false;
        if (end + 1 < expression.size() && expression[end] == '.' && digit(expression[end + 1])) {
            decimal = true;
            ++end;
            while (end < expression.size() && digit(expression[end])) ++end;
        }
        const bool as_arguments = !decimal && !leading_zero_group && !currency_before(expression, i) &&
                                  list_call_without_spaced_separator(expression, i);
        const std::string figure = expression.substr(i, end - i);
        for (char c : figure) {
            if (c != ',') out.push_back(c);
            else if (as_arguments) out += ", ";
        }
        split = split || as_arguments;
        i = end;
    }
    return {out, split};
}

std::string without_currency(std::string text) {
    std::string out;
    for (std::size_t i = 0; i < text.size();) {
        std::string mark;
        for (const std::string candidate : {"$", "€", "£", "¥"}) {
            if (text.compare(i, candidate.size(), candidate) == 0) { mark = candidate; break; }
        }
        if (mark.empty()) { out.push_back(text[i++]); continue; }
        std::size_t ahead = i + mark.size();
        while (ahead < text.size() && text[ahead] == ' ') ++ahead;
        if (ahead >= text.size() || !(digit(text[ahead]) || text[ahead] == '.' || text[ahead] == '(')) {
            out += mark;
            i += mark.size();
            continue;
        }
        std::size_t letters = 0;
        while (letters < 3 && out.size() > letters && letter(out[out.size() - 1 - letters])) ++letters;
        if (letters && !(out.size() > letters && letter(out[out.size() - 1 - letters]))) out.resize(out.size() - letters);
        i += mark.size();
    }
    replace_all(out, "×", "*");
    replace_all(out, "−", "-");
    replace_all(out, "^", "**");
    return trim(out);
}

class Parser {
public:
    explicit Parser(std::string text) : text_(std::move(text)) {}
    double parse() {
        const double value = expression();
        spaces();
        if (pos_ != text_.size()) throw CalcError("cannot parse expression: invalid syntax");
        if (!std::isfinite(value)) throw CalcError("result is not a finite number");
        if (std::abs(value) > kMaxAbsValue) throw CalcError("result is too large");
        return value;
    }
private:
    std::string text_;
    std::size_t pos_ = 0;
    int depth_ = 0;

    struct Guard {
        Parser& parser;
        explicit Guard(Parser& p) : parser(p) {
            if (++parser.depth_ > 64) throw CalcError("cannot evaluate expression: maximum recursion depth exceeded");
        }
        ~Guard() { --parser.depth_; }
    };
    void spaces() {
        while (pos_ < text_.size() && std::isspace(static_cast<unsigned char>(text_[pos_]))) ++pos_;
    }
    bool take(const std::string& token) {
        spaces();
        if (text_.compare(pos_, token.size(), token) != 0) return false;
        pos_ += token.size();
        return true;
    }
    double expression() {
        Guard guard(*this);
        double value = term();
        for (;;) {
            if (take("+")) value += term();
            else if (take("-")) value -= term();
            else break;
        }
        return value;
    }
    double term() {
        Guard guard(*this);
        double value = factor();
        for (;;) {
            spaces();
            if (text_.compare(pos_, 2, "**") == 0) break;
            if (take("//")) {
                double rhs = factor();
                if (rhs == 0) throw CalcError("division by zero");
                value = std::floor(value / rhs);
            } else if (take("*")) value *= factor();
            else if (take("/")) {
                double rhs = factor();
                if (rhs == 0) throw CalcError("division by zero");
                value /= rhs;
            } else if (take("%")) {
                double rhs = factor();
                if (rhs == 0) throw CalcError("division by zero");
                value -= std::floor(value / rhs) * rhs;
            } else break;
        }
        return value;
    }
    double factor() {
        Guard guard(*this);
        if (take("+")) return factor();
        if (take("-")) return -factor();
        return power();
    }
    double power() {
        Guard guard(*this);
        const double value = atom();
        if (!take("**")) return value;
        const double exponent = factor();
        if (std::abs(exponent) > 16) throw CalcError("exponent too large");
        if (std::abs(value) > 1 && exponent * std::log10(std::abs(value)) > 308) {
            throw CalcError("result is too large");
        }
        const double result = std::pow(value, exponent);
        if (std::isnan(result)) throw CalcError("result is not a real number");
        return result;
    }
    double atom() {
        Guard guard(*this);
        spaces();
        if (take("(")) {
            const double value = expression();
            if (!take(")")) throw CalcError("cannot parse expression: invalid syntax");
            return value;
        }
        if (pos_ < text_.size() && (text_[pos_] == '[' || text_[pos_] == '{')) {
            throw CalcError("lists are not supported; pass numbers directly");
        }
        if (pos_ < text_.size() && letter(text_[pos_])) {
            const std::size_t begin = pos_;
            while (pos_ < text_.size() && (letter(text_[pos_]) || digit(text_[pos_]) || text_[pos_] == '_')) ++pos_;
            const std::string name = text_.substr(begin, pos_ - begin);
            if (!take("(")) throw CalcError("unsupported expression element: Name");
            std::vector<double> args;
            if (!take(")")) {
                for (;;) {
                    args.push_back(expression());
                    if (take(")")) break;
                    if (!take(",")) throw CalcError("cannot parse expression: invalid syntax");
                }
            }
            if (name == "sum") {
                double total = 0;
                for (double item : args) total += item;
                return total;
            }
            if (name == "min" || name == "max") {
                if (args.empty()) throw CalcError("cannot evaluate expression: empty sequence");
                return name == "min" ? *std::min_element(args.begin(), args.end()) :
                                       *std::max_element(args.begin(), args.end());
            }
            if (name == "abs" && args.size() == 1) return std::abs(args[0]);
            if (name == "floor" && args.size() == 1) return std::floor(args[0]);
            if (name == "ceil" && args.size() == 1) return std::ceil(args[0]);
            if (name == "round" && (args.size() == 1 || args.size() == 2)) {
                if (args.size() == 1) return std::nearbyint(args[0]);
                if (std::abs(args[1]) > kMaxRoundPlaces) throw CalcError("rounding places out of range");
                if (std::floor(args[1]) != args[1]) {
                    throw CalcError("cannot evaluate expression: 'float' object cannot be interpreted as an integer");
                }
                const double scale = std::pow(10.0, args[1]);
                return std::nearbyint(args[0] * scale) / scale;
            }
            throw CalcError("unsupported expression element: Call");
        }
        if (pos_ >= text_.size() || !(digit(text_[pos_]) || text_[pos_] == '.')) {
            throw CalcError("cannot parse expression: invalid syntax");
        }
        char* end = nullptr;
        const double value = std::strtod(text_.c_str() + pos_, &end);
        if (end == text_.c_str() + pos_) throw CalcError("cannot parse expression: invalid syntax");
        pos_ = static_cast<std::size_t>(end - text_.c_str());
        return value;
    }
};

std::string formatted(double value) {
    if (std::floor(value) == value) return std::to_string(static_cast<long long>(value));
    std::ostringstream out;
    out << std::fixed << std::setprecision(6) << value;
    std::string text = out.str();
    while (!text.empty() && text.back() == '0') text.pop_back();
    if (!text.empty() && text.back() == '.') text.pop_back();
    return text;
}

std::vector<std::string> listed_terms(const json& args) {
    json raw = args.is_object() && args.contains("terms") ? args.at("terms") : json::array();
    if (raw.is_string()) raw = json::array({raw});
    std::vector<std::string> terms;
    if (!raw.is_array()) return terms;
    for (std::size_t i = 0; i < raw.size() && i < kMaxTerms; ++i) {
        const std::string value = trim(py_string(raw[i]));
        if (!value.empty()) terms.push_back(prefix_chars(value, kMaxTermChars));
    }
    return terms;
}

std::string join(const std::vector<std::string>& items, const std::string& sep) {
    std::string out;
    for (const auto& item : items) {
        if (!out.empty()) out += sep;
        out += item;
    }
    return out;
}

std::string fold(const std::string& text) {
    // Normalize with NFKC, ten dash variants, Unicode whitespace collapse/strip,
    // then full Unicode casefold (which can expand e.g. ß -> ss).
    UErrorCode status = U_ZERO_ERROR;
    const auto* normalizer = icu::Normalizer2::getNFKCInstance(status);
    if (U_FAILURE(status) || normalizer == nullptr)
        throw std::runtime_error("ICU NFKC normalizer unavailable");
    icu::UnicodeString normalized;
    normalizer->normalize(icu::UnicodeString::fromUTF8(text), normalized, status);
    if (U_FAILURE(status)) throw std::runtime_error("ICU NFKC normalization failed");
    icu::UnicodeString collapsed;
    bool gap = false;
    for (int32_t offset = 0; offset < normalized.length();) {
        UChar32 point = normalized.char32At(offset);
        offset += U16_LENGTH(point);
        if (point == 0x2010 || point == 0x2011 || point == 0x2012 ||
            point == 0x2013 || point == 0x2014 || point == 0x2015 ||
            point == 0x2212 || point == 0xfe58 || point == 0xfe63 ||
            point == 0xff0d) point = '-';
        if (u_isUWhiteSpace(point) || u_isWhitespace(point)) {
            gap = !collapsed.isEmpty();
            continue;
        }
        if (gap) collapsed.append(static_cast<UChar32>(' '));
        collapsed.append(point);
        gap = false;
    }
    collapsed.foldCase();
    std::string result;
    collapsed.toUTF8String(result);
    return result;
}

struct Part {
    std::string mark;
    std::string text;
};

std::vector<std::string> lines_of(const std::string& text) {
    std::vector<std::string> lines;
    std::size_t start = 0;
    for (;;) {
        const std::size_t end = text.find('\n', start);
        lines.push_back(text.substr(start, end == std::string::npos ? end : end - start));
        if (end == std::string::npos) break;
        start = end + 1;
    }
    return lines;
}

std::vector<std::string> paragraph_parts(const std::vector<std::string>& lines) {
    const std::string text = trim(join(lines, "\n"));
    if (text.empty()) return {};
    if (char_count(text) <= 1200) return {text};
    std::vector<std::string> out;
    for (const auto& line : lines) if (!trim(line).empty()) out.push_back(trim(line));
    return out;
}

std::vector<std::string> csv_fields(const std::string& line) {
    if (line.find(',') == std::string::npos) return {};
    std::vector<std::string> cells;
    std::string cell;
    bool quoted = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        const char c = line[i];
        if (c == '"') {
            if (quoted && i + 1 < line.size() && line[i + 1] == '"') { cell.push_back('"'); ++i; }
            else quoted = !quoted;
        } else if (c == ',' && !quoted) { cells.push_back(cell); cell.clear(); }
        else cell.push_back(c);
    }
    if (quoted) return {};
    cells.push_back(cell);
    return cells.size() >= 2 ? cells : std::vector<std::string>{};
}

std::vector<std::string> markdown_cells(std::string line) {
    line = trim(line);
    if (!line.empty() && line.front() == '|') line.erase(line.begin());
    if (!line.empty() && line.back() == '|') line.pop_back();
    std::vector<std::string> cells;
    std::size_t start = 0;
    for (;;) {
        const std::size_t end = line.find('|', start);
        cells.push_back(trim(line.substr(start, end == std::string::npos ? end : end - start)));
        if (end == std::string::npos) break;
        start = end + 1;
    }
    return cells;
}

bool usable_header(const std::vector<std::string>& cells) {
    std::set<std::string> unique;
    if (cells.empty()) return false;
    for (const auto& cell : cells) {
        if (trim(cell).empty() || char_count(trim(cell)) > 60 || !unique.insert(trim(cell)).second) return false;
    }
    return true;
}

bool markdown_rule(const std::string& line) {
    for (auto cell : markdown_cells(line)) {
        cell = trim(cell);
        if (!cell.empty() && cell.front() == ':') cell.erase(cell.begin());
        if (!cell.empty() && cell.back() == ':') cell.pop_back();
        if (cell.size() < 3 || !std::all_of(cell.begin(), cell.end(), [](char c) { return c == '-'; })) return false;
    }
    return true;
}

// JSON output preserves object insertion order and non-ASCII characters
// and separates members with comma-space and key/value with colon-space.
std::string py_json_dump(const nlohmann::ordered_json& value) {
    if (value.is_object()) {
        std::string out = "{";
        bool first = true;
        for (auto it = value.begin(); it != value.end(); ++it) {
            if (!first) out += ", ";
            first = false;
            out += nlohmann::ordered_json(it.key()).dump();
            out += ": ";
            out += py_json_dump(it.value());
        }
        return out + "}";
    }
    if (value.is_array()) {
        std::string out = "[";
        bool first = true;
        for (const auto& item : value) {
            if (!first) out += ", ";
            first = false;
            out += py_json_dump(item);
        }
        return out + "]";
    }
    return value.dump();
}

std::string table_row(const std::vector<std::string>& header,
                      const std::vector<std::string>& cells) {
    nlohmann::ordered_json row = nlohmann::ordered_json::object();
    for (std::size_t i = 0; i < header.size() && i < cells.size(); ++i) row[header[i]] = cells[i];
    return py_json_dump(row);
}

void leaf_objects(const nlohmann::ordered_json& value, std::vector<std::string>& out) {
    if (value.is_object()) {
        bool nested = false;
        nlohmann::ordered_json scalars = nlohmann::ordered_json::object();
        for (auto it = value.begin(); it != value.end(); ++it) {
            if (it.value().is_object() || it.value().is_array()) nested = true;
            else scalars[it.key()] = it.value();
        }
        if (!nested) { out.push_back(py_json_dump(value)); return; }
        if (!scalars.empty()) out.push_back(py_json_dump(scalars));
        for (auto it = value.begin(); it != value.end(); ++it) {
            if (it.value().is_object() || it.value().is_array()) leaf_objects(it.value(), out);
        }
    } else if (value.is_array()) {
        for (const auto& item : value) leaf_objects(item, out);
    }
}

std::vector<std::string> split_parts(const std::string& text) {
    const auto lines = lines_of(text);
    std::vector<std::string> parts;
    std::vector<std::string> pending;
    auto flush = [&] {
        auto paragraphs = paragraph_parts(pending);
        parts.insert(parts.end(), paragraphs.begin(), paragraphs.end());
        pending.clear();
    };
    std::size_t i = 0;
    while (i < lines.size()) {
        const std::string current = trim(lines[i]);
        if (current.empty()) { flush(); ++i; continue; }
        if (current.front() == '{' || current.front() == '[') {
            for (std::size_t end = i + 1; end <= lines.size(); ++end) {
                const std::string body = join(std::vector<std::string>(lines.begin() + i, lines.begin() + end), "\n");
                auto parsed = nlohmann::ordered_json::parse(body, nullptr, false);
                if (parsed.is_discarded()) {
                    if (end < lines.size() && !trim(lines[end]).empty()) continue;
                    break;
                }
                std::vector<std::string> leaves;
                leaf_objects(parsed, leaves);
                if (!leaves.empty()) {
                    flush();
                    parts.insert(parts.end(), leaves.begin(), leaves.end());
                    i = end;
                    goto next_line;
                }
                break;
            }
        }
        if (current.front() == '|' && i + 1 < lines.size() && markdown_rule(lines[i + 1])) {
            const auto header = markdown_cells(lines[i]);
            if (usable_header(header)) {
                flush();
                i += 2;
                while (i < lines.size() && !trim(lines[i]).empty() && trim(lines[i]).front() == '|') {
                    const auto cells = markdown_cells(lines[i]);
                    parts.push_back(cells.size() == header.size() ? table_row(header, cells) : trim(lines[i]));
                    ++i;
                }
                continue;
            }
        }
        if (auto header = csv_fields(lines[i]); usable_header(header)) {
            std::size_t end = i + 1;
            std::vector<std::vector<std::string>> rows;
            while (end < lines.size()) {
                auto cells = csv_fields(lines[end]);
                if (cells.size() != header.size()) break;
                rows.push_back(std::move(cells));
                ++end;
            }
            if (end - i >= 3) {
                flush();
                std::vector<std::string> clean_header;
                clean_header.reserve(header.size());
                for (const auto& cell : header) clean_header.push_back(trim(cell));
                for (const auto& row : rows) parts.push_back(table_row(clean_header, row));
                i = end;
                continue;
            }
        }
        pending.push_back(lines[i]);
        ++i;
        next_line: ;
    }
    flush();
    return parts;
}

std::vector<std::string> wanted_texts(const json& args) {
    if (!args.is_object() || !args.contains("texts")) return {};
    json raw = args.at("texts");
    if (raw.is_string()) raw = json::array({raw});
    if (!raw.is_array()) return {};
    std::vector<std::string> out;
    for (const auto& item : raw) {
        if (item.is_boolean() || !(item.is_string() || item.is_number())) continue;
        const std::string value = prefix_chars(trim(py_string(item)), kMaxTextChars);
        if (!value.empty() && std::find(out.begin(), out.end(), value) == out.end()) out.push_back(value);
        if (out.size() >= kMaxFindTexts) break;
    }
    return out;
}

std::string order_word(const json& args) {
    if (!args.is_object() || !args.contains("order_by")) return "";
    const json& raw = args.at("order_by");
    if (raw.is_boolean() || !(raw.is_string() || raw.is_number_integer())) return "";
    std::string value = py_string(raw);
    replace_all(value, "_", " ");
    return prefix_chars(fold(value), 60);
}

UChar32 codepoint_at(const std::string& text, std::size_t at, std::size_t& next) {
    int32_t offset = static_cast<int32_t>(at);
    UChar32 point = U_SENTINEL;
    U8_NEXT(text.data(), offset, static_cast<int32_t>(text.size()), point);
    if (point < 0) {
        next = at + 1;
        return static_cast<unsigned char>(text[at]);
    }
    next = static_cast<std::size_t>(offset);
    return point;
}

bool word_character(UChar32 point) {
    if (point == '_') return true;
    const auto category = u_charType(point);
    return category == U_UPPERCASE_LETTER || category == U_LOWERCASE_LETTER ||
           category == U_TITLECASE_LETTER || category == U_MODIFIER_LETTER ||
           category == U_OTHER_LETTER || category == U_DECIMAL_DIGIT_NUMBER ||
           category == U_LETTER_NUMBER || category == U_OTHER_NUMBER;
}

bool word_character_at(const std::string& text, std::size_t at) {
    if (at >= text.size()) return false;
    std::size_t next;
    return word_character(codepoint_at(text, at, next));
}

bool word_character_before(const std::string& text, std::size_t at) {
    if (at == 0) return false;
    int32_t offset = static_cast<int32_t>(at);
    UChar32 point = U_SENTINEL;
    U8_PREV(text.data(), 0, offset, point);
    return point >= 0 && word_character(point);
}

std::optional<long long> first_integer(const std::string& text) {
    static const std::regex number(R"(-?\d+)");
    std::smatch match;
    if (!std::regex_search(text, match, number)) return std::nullopt;
    try { return std::stoll(match.str()); } catch (...) { return std::nullopt; }
}

std::optional<long long> number_after_text(const std::string& text, const std::string& word) {
    std::vector<std::string> words{word};
    if (const auto split = word.rfind(' '); split != std::string::npos) words.push_back(word.substr(split + 1));
    const auto parsed = json::parse(text, nullptr, false);
    for (const auto& each : words) {
        if (parsed.is_object()) {
            for (auto it = parsed.begin(); it != parsed.end(); ++it) {
                std::string key = it.key();
                replace_all(key, "_", " ");
                const std::string named = " " + fold(key) + " ";
                if (named.find(" " + each + " ") != std::string::npos) {
                    if (auto value = first_integer(fold(py_string(it.value())))) return value;
                }
            }
        }
        const std::string haystack = fold(text);
        std::size_t pos = 0;
        while ((pos = haystack.find(each, pos)) != std::string::npos) {
            const std::size_t after = pos + each.size();
            if (!word_character_before(haystack, pos) &&
                !word_character_at(haystack, after)) {
                std::size_t cursor = after, skipped = 0;
                while (cursor < haystack.size() && !word_character_at(haystack, cursor) && skipped < 3) {
                    std::size_t next;
                    codepoint_at(haystack, cursor, next);
                    cursor = next;
                    ++skipped;
                }
                std::size_t start = cursor;
                if (cursor < haystack.size() && haystack[cursor] == '-') ++cursor;
                while (cursor < haystack.size() && digit(haystack[cursor])) ++cursor;
                if (cursor > start && (digit(haystack[cursor - 1]))) {
                    try { return std::stoll(haystack.substr(start, cursor - start)); } catch (...) {}
                }
            }
            pos = after;
        }
    }
    return std::nullopt;
}

}  // namespace

json calculate(const json& args) {
    const std::string expression = trim(py_string(first_truthy(args, "expression", "expr")));
    auto [reading, split] = char_count(expression) <= kMaxExpressionChars ?
        read_commas(expression) : std::pair<std::string, bool>{expression, false};
    double result = 0;
    try {
        if (expression.empty() || char_count(expression) > kMaxExpressionChars) {
            throw CalcError("expression is empty or too long");
        }
        const std::string normalized = without_currency(reading);
        if (normalized.empty()) throw CalcError("expression is empty or too long");
        result = Parser(normalized).parse();
    } catch (const CalcError& error) {
        json output = {{"error", error.what()}};
        if (split) output["read_as"] = reading;
        return output;
    }
    const auto terms = listed_terms(args);
    std::string receipt = expression + " = " + formatted(result) + "\n";
    if (split) receipt += "Read as: " + reading + "\n";
    receipt += "Terms as you listed them:\n" +
               (terms.empty() ? std::string("(none listed)") : join(terms, "\n")) +
               "\nThis receipt is arithmetic over what you supplied. Which figures belong and which sign each carries come from your reading of the records, and you may change either and calculate again.";
    return receipt;
}

json find_in_records(const Packet& packet, const json& args) {
    const auto texts = wanted_texts(args);
    if (texts.empty()) return "find_in_records needs at least one non-empty text in texts.";
    if (packet.records.empty()) return "No records are attached to this message, so there is nothing to look up.";
    std::vector<Part> parts;
    std::vector<std::string> marks;
    for (std::size_t i = 0; i < packet.records.size(); ++i) {
        const auto& pair = packet.records[i];
        const std::string mark = "M" + std::to_string(i + 1);
        marks.push_back(mark);
        for (const auto& part : split_parts(pair.prompt)) parts.push_back({mark, part});
        if (!trim(pair.response).empty()) {
            for (const auto& part : split_parts(pair.response)) parts.push_back({mark, part});
        }
    }
    const std::string word = order_word(args);
    std::vector<std::string> blocks;
    if (!word.empty()) blocks.push_back("Listed in the order of the number after " + json(word).dump() +
                                        ", from smallest to largest; parts without one come last.");
    std::size_t size = 0;
    for (const auto& text : texts) {
        const std::string label = json(text).dump();
        if (size >= kMaxResultChars) {
            blocks.push_back(label + " was not looked up in this reply because the reply is full; look it up again.");
            continue;
        }
        std::vector<std::pair<std::size_t, Part>> hits;
        const std::string needle = fold(text);
        for (std::size_t i = 0; i < parts.size(); ++i) {
            if (fold(parts[i].text).find(needle) != std::string::npos) hits.emplace_back(i, parts[i]);
        }
        if (!word.empty()) {
            std::stable_sort(hits.begin(), hits.end(), [&](const auto& a, const auto& b) {
                const auto x = number_after_text(a.second.text, word);
                const auto y = number_after_text(b.second.text, word);
                if (x.has_value() != y.has_value()) return x.has_value();
                if (x && y && *x != *y) return *x < *y;
                return a.first < b.first;
            });
        }
        std::vector<std::string> block;
        if (hits.empty()) {
            block.push_back(label + " is in no part of the attached records (" + join(marks, ", ") +
                            "). A shorter text, such as a single identifier or name, may find what you are after.");
        } else {
            block.push_back(label + " is in " + std::to_string(hits.size()) + " part" +
                            (hits.size() == 1 ? "" : "s") + " of the attached records:");
            std::size_t shown = 0;
            for (const auto& [position, part] : hits) {
                (void)position;
                const std::string line = "[" + part.mark + "] " + part.text;
                if (shown >= kMaxParts || (shown && size + char_count(line) + 1 > kMaxResultChars)) break;
                block.push_back(line);
                size += char_count(line) + 1;
                ++shown;
            }
            if (hits.size() > shown) {
                const std::size_t hidden = hits.size() - shown;
                block.push_back(std::to_string(hidden) + " more part" + (hidden == 1 ? "" : "s") +
                                " with " + label + " are not shown; look it up on its own or with a longer text.");
            }
        }
        size += char_count(block.front()) + 1;
        blocks.push_back(join(block, "\n"));
    }
    return join(blocks, "\n\n");
}

json calculate_tool_definition() {
    return {{"type", "function"}, {"function", {
        {"name", "calculate"},
        {"description", "Arithmetic over figures you take from the attached records: + - * / parentheses, min, max, sum, abs, round, and also floor, ceil, //, % and ** (^ is read as **). Inside the brackets of sum, min or max, a comma with no space after it between whole digit groups separates arguments, so sum(3,100) is 103, unless the group after it starts with 0, so sum(2,050) is 2050; anywhere else a comma inside a figure groups thousands. The receipt shows how the expression was read. Returns the result of the expression you supply, nothing more."},
        {"parameters", {{"type", "object"},
            {"properties", {{"expression", {{"type", "string"}, {"description", "Numbers, operators and currency marks, for example (1200 - 350) * 2"}}},
                            {"terms", {{"type", "array"}, {"items", {{"type", "string"}}},
                                       {"description", "One entry per figure in the expression: the figure with its sign, then the record label and the words around it, for example \"-350: M2, the words the record puts around it\"."}}}}},
            {"required", json::array({"expression", "terms"})}}}
    }}};
}

json find_tool_definition(bool ordering) {
    json definition = {{"type", "function"}, {"function", {
        {"name", "find_in_records"},
        {"description", "Looks up texts in the records attached to this message. Each text is looked up on its own: every part of the records that holds it comes back whole, under the mark of its record and in the order the records show them, or, with order_by, in the order of the whole number each part gives for the word or column you name, from smallest to largest - a table row as an object of its column names and cells, a JSON object, or a paragraph. Letter case and the kind of dash or space do not matter. Use it to follow an identifier or a name through long records, one lookup after another, instead of reading them end to end."},
        {"parameters", {{"type", "object"},
            {"properties", {{"texts", {{"type", "array"}, {"items", {{"type", "string"}}},
                                  {"description", "One to four texts to look up, for example identifiers or names from the message or from parts found earlier."}}},
                            {"order_by", {{"type", "string"},
                                          {"description", "Optional: a word or column name. The parts found are then listed in the order of the whole number that comes right after that word in each part, or in that column, from smallest to largest; parts without one come last."}}}}},
            {"required", json::array({"texts"})}}}
    }}};
    if (!ordering) {
        definition["function"]["description"] =
            "Looks up texts in the records attached to this message. Each text is looked up on its own: every part of the records that holds it comes back whole, under the mark of its record and in the order the records show them - a table row as an object of its column names and cells, a JSON object, or a paragraph. Letter case and the kind of dash or space do not matter. Use it to follow an identifier or a name through long records, one lookup after another, instead of reading them end to end.";
        definition["function"]["parameters"]["properties"].erase("order_by");
    }
    return definition;
}

}  // namespace ditto
