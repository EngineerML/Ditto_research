#include "retrieval.hpp"
#include "lane.hpp"

#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
}

int main() {
    using ditto::MemoryPair;
    const std::vector<MemoryPair> pairs = {
        {"p1", "", "2026-01-01", "abc123def456: planned for May", "Not shipped yet.", 1},
        {"p2", "", "2026-01-02", "abc123def456: planned for May", "Still planned.", 2},
        {"p3", "", "2026-01-03", "abc123def456: shipped in June", "Done.", 3},
    };
    const std::string question = "What changed in abc123def456's delivery?";
    const auto ranking = ditto::rank(pairs, question);
    require(ranking.ordered.size() == 3,
            "possessive identifier did not retrieve all three records");
    require(ditto::has_identifier_focus(question, ranking.ordered),
            "possessive identifier did not trigger focused routing");
    const auto packet = ditto::build_packet(ranking, question);
    require(packet.focused && packet.records.size() == 3,
            "possessive identifier did not focus the packet");
    require(ditto::asked_part("Earlier abc123def456's note. What changed?",
                              {"abc123def456"}) ==
                "Earlier abc123def456's note. What changed?",
            "asked_part dropped the sentence carrying a possessive identifier");

    const std::vector<MemoryPair> substring_pairs = {
        {"sub1", "", "2026-01-01", "The opal pathway progressed", "", 1},
    };
    const std::string substring_question =
        "What is the current status of \"opal path\"?";
    const auto substring_rank = ditto::rank(substring_pairs, substring_question);
    require(substring_rank.anchor_kinds.empty(),
            "quoted substring unexpectedly became an exact retrieval anchor");
    require(!ditto::about_own_records(substring_question, ditto::json::array(),
                                      {"action", "live"}, substring_pairs,
                                      substring_rank.anchor_kinds),
            "a quoted substring fabricated an own-records route");

    const std::vector<MemoryPair> nested_quote_pairs = {
        {"quoted", "", "2026-01-01",
         "“" + std::string(61, 'x') + " \"cobalt plan\" ”", "", 1},
    };
    const auto nested_quote_rank =
        ditto::rank(nested_quote_pairs, "What did \"cobalt plan\" decide?");
    require(nested_quote_rank.anchor_kinds.contains('q'),
            "an overlong outer quote hid a valid inner quote anchor");

    const std::string newline_quote =
        "Send one message to Ada about “broken\n\"cobalt plan\"”.";
    require(ditto::quoted_spans(newline_quote) ==
                std::vector<std::string>{"cobalt plan"},
            "an invalid outer action quote hid a valid inner quote");
    ditto::Packet action_packet;
    action_packet.records.push_back(
        {"quoted-1", "", "2026-01-01", "Discussed cobalt plan with Ada.",
         "The plan was agreed.", 1});
    require(ditto::action_focus_block(action_packet, newline_quote).find(
                "[M1] pair_id=quoted-1") != std::string::npos,
            "action focus block omitted the inner quoted record");

    const std::vector<MemoryPair> unicode_quote_pairs = {
        {"unicode-quote", "", "2026-01-01",
         "The project is “MÜNCHEN”.", "", 1},
    };
    const auto unicode_quote_rank =
        ditto::rank(unicode_quote_pairs, "What happened to “münchen”?");
    require(unicode_quote_rank.anchor_kinds.contains('q') &&
                unicode_quote_rank.ordered.size() == 1 &&
                unicode_quote_rank.ordered[0].pair.pair_id == "unicode-quote",
            "Unicode case difference lost the quoted-value anchor");
}
