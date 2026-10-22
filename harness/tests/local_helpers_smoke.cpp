#include "local_helpers.hpp"

#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
}

int main() {
    using ditto::json;
    const auto arithmetic = ditto::calculate({{"expression", "sum(3,100)"},
                                               {"terms", json::array({"3 from M1", "100 from M2"})}});
    require(arithmetic.is_string(), "calculate did not return a receipt");
    require(arithmetic.get<std::string>().find("sum(3,100) = 103\nRead as: sum(3, 100)\n") == 0,
            "grouped-number argument reading failed");
    const auto grouped = ditto::calculate({{"expression", "sum(2,050)"}});
    require(grouped.is_string() && grouped.get<std::string>().find("sum(2,050) = 2050\n") == 0,
            "leading-zero group reading failed");
    const auto invalid = ditto::calculate({{"expression", "10/0"}});
    require(invalid.is_object() && invalid.value("error", "") == "division by zero",
            "division-by-zero error text differs");

    ditto::Packet packet;
    packet.records.push_back({"p1", "", "", "b,a\none,needle\nthree,four\n\n{\"z\": \"needle\", \"a\": 1}", "", 1});
    const auto found = ditto::find_in_records(packet, {{"texts", json::array({"needle"})}});
    require(found.is_string(), "finder did not return text");
    const std::string body = found.get<std::string>();
    require(body.find("\"needle\" is in 2 parts") != std::string::npos,
            "finder did not split CSV and JSON records");
    require(body.find("[M1] {\"b\": \"one\", \"a\": \"needle\"}") != std::string::npos,
            "finder changed CSV key order or JSON spacing");
    require(body.find("[M1] {\"z\": \"needle\", \"a\": 1}") != std::string::npos,
            "finder changed JSON leaf order or spacing");
    require(ditto::find_tool_definition()["function"]["parameters"]["properties"].contains("order_by"),
            "default finder definition lacks order_by");
    require(!ditto::find_tool_definition(false)["function"]["parameters"]["properties"].contains("order_by"),
            "unordered finder definition contains order_by");

    ditto::Packet ordered_unicode;
    ordered_unicode.records.push_back({"currency", "", "", "rank €0", "", 1});
    ordered_unicode.records.push_back({"plain", "", "", "rank 1", "", 2});
    const auto ordered_result = ditto::find_in_records(
        ordered_unicode, {{"texts", json::array({"rank"})}, {"order_by", "rank"}});
    require(ordered_result.is_string(), "ordered Unicode finder did not return text");
    const std::string ordered_body = ordered_result.get<std::string>();
    require(ordered_body.find("[M1] rank €0") < ordered_body.find("[M2] rank 1"),
            "finder counted UTF-8 bytes instead of Unicode characters");

    ditto::Packet unicode_packet;
    unicode_packet.records.push_back({"u1", "", "", "Straße ＡＢＣ co‑operate café suite", "", 1});
    const auto unicode = ditto::find_in_records(unicode_packet,
        {{"texts", json::array({"STRASSE", "abc", "co-operate", "CAFÉ SUITE"})}});
    require(unicode.is_string(), "Unicode finder did not return text");
    const std::string unicode_body = unicode.get<std::string>();
    require(unicode_body.find("\"STRASSE\" is in 1 part") != std::string::npos &&
            unicode_body.find("\"abc\" is in 1 part") != std::string::npos &&
            unicode_body.find("\"co-operate\" is in 1 part") != std::string::npos &&
            unicode_body.find("\"CAFÉ SUITE\" is in 1 part") != std::string::npos,
            "finder NFKC, Unicode casefold, dash or whitespace handling failed");
    ditto::Packet expanded;
    expanded.records.push_back({"u2", "", "", "İstanbul ΣΙΓΜΑ Ⅳ", "", 2});
    const auto expanded_hits = ditto::find_in_records(expanded,
        {{"texts", json::array({"i̇stanbul", "σιγμα", "IV"})}});
    require(expanded_hits.is_string(), "expanded Unicode finder did not return text");
    const std::string expanded_body = expanded_hits.get<std::string>();
    require(expanded_body.find("\"i̇stanbul\" is in 1 part") != std::string::npos &&
            expanded_body.find("\"σιγμα\" is in 1 part") != std::string::npos &&
            expanded_body.find("\"IV\" is in 1 part") != std::string::npos,
            "finder full casefold or compatibility-form handling failed");
}
