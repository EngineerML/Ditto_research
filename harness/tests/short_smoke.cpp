#include "short.hpp"

#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(bool yes, const std::string& message) {
    if (!yes) throw std::runtime_error(message);
}
}

int main() {
    std::vector<ditto::Candidate> focus;
    focus.push_back({{"p1", "", "2026-01-01", "abc123def456: planned for May", "", 1}});
    focus.push_back({{"p2", "", "2026-01-02", "abc123def456: planned for May", "", 2}});
    focus.push_back({{"p3", "", "2026-01-03", "abc123def456: shipped in June", "", 3}});
    const std::string question = "When did abc123def456 ship?";
    require(ditto::short_identifier_focus(question, focus).size() == 3, "identifier focus missed thread");
    require(ditto::short_records(focus, 1000), "short-record budget incorrectly rejected");
    require(!ditto::short_records(focus, 10), "short-record budget incorrectly admitted");
    const auto program = ditto::plan_short_program(question, focus, 1000);
    require(program && program->token == "abc123def456" && program->groups.size() == 2,
            "short program groups mismatch");
    require(program->needs_order(), "short program did not request ordering");
    require(program->order_messages().size() == 2, "short program order prompt missing");
    ditto::RunRequest request;
    request.user_input = question;
    request.system_prompt = "Be precise.";
    require(!program->answer_messages(request, std::nullopt), "program should wait for order reply");
    const auto answer = program->answer_messages(request, "M2, M1", true);
    require(answer && answer->size() == 2, "program answer messages missing");
    const std::string answer_user = (*answer)[1]["content"].get<std::string>();
    require(answer_user.find("1. shipped in June\n2. planned for May") != std::string::npos,
            "program lead did not follow ordered statements");
    require(answer_user.find("[M1] 2026-01-03\nUser: abc123def456: shipped in June") != std::string::npos,
            "program record marks did not follow ordered groups");
    require((*answer)[0]["content"].get<std::string>().find("even when the message asks for less") != std::string::npos,
            "full-date prompt missing");
    const auto default_date_answer = program->answer_messages(request, "M2, M1", false);
    require(default_date_answer &&
            (*default_date_answer)[0]["content"].get<std::string>().find(
                "even when the message asks for less") == std::string::npos,
            "non-full-date short prompt retained the full-date addition");

    std::vector<ditto::MemoryPair> corpus = {
        {"t1", "", "2026-02-01", "Orchid Delta launch\n\nOrchid Delta owner Alice Smith\n\nOrchid Delta phase one", "", 1},
        {"t2", "", "2026-02-02", "Orchid Delta revision\n\nOrchid Delta owner Alice Smith\n\nOrchid Delta phase two", "", 2},
        {"t3", "", "2026-02-03", "Orchid Delta final\n\nOrchid Delta owner Alice Smith\n\nOrchid Delta phase three", "", 3},
        {"card", "", "2026-02-04", "Alice Smith is called “Ally”.", "", 4},
        {"alias", "", "2026-02-05", "Ally has a contact address.", "", 5}
    };
    const auto found = ditto::find_topic("What changed in orchid delta?", corpus, 3, 30000);
    require(found && found->phrase == "orchid delta" && found->densest == 3,
            "topic phrase or density mismatch");
    require(found->notes.size() == 3 && ditto::topic_fits(*found, 30000),
            "topic note selection mismatch");
    require(!ditto::topic_fits(*found, 5), "topic fit incorrectly admitted notes");
    request.user_input = "What changed in orchid delta?";
    const auto topic = ditto::topic_messages(request, *found, corpus);
    require(topic.size() == 2 && topic[1]["content"].get<std::string>().find("Passages that name “orchid delta”") == 0,
            "topic prompt lacks passage lead");
    require(ditto::topic_latest_messages(request, *found, corpus).size() == 2,
            "topic latest-draft prompt missing");
    request.system_prompt = "Do not disclose private notes.\nAnswer in the required format.";
    const auto latest = ditto::topic_latest_messages(request, *found, corpus);
    const std::string latest_system = latest[0]["content"].get<std::string>();
    require(latest_system.find("Below are the latest passages") != std::string::npos &&
                latest_system.find("Operator instructions (from the product operator") != std::string::npos &&
                latest_system.find(request.system_prompt) != std::string::npos,
            "topic draft omitted the applicable trusted system instruction");
    require(ditto::topic_messages(request, *found, corpus)[0]["content"].get<std::string>().find(
                request.system_prompt) != std::string::npos,
            "topic deciding prompt omitted the applicable trusted system instruction");
    ditto::RunRequest no_operator = request;
    no_operator.system_prompt.clear();
    const auto plain_latest = ditto::topic_latest_messages(no_operator, *found, corpus);
    require(plain_latest[0]["content"].get<std::string>().find(
                "Operator instructions (from the product operator") == std::string::npos,
            "topic draft invented operator instructions for an empty system prompt");
    const std::string latest_user = latest[1]["content"].get<std::string>();
    require(latest_user.find("Orchid Delta phase three") != std::string::npos &&
                latest_user.find("Orchid Delta owner Alice Smith") == std::string::npos,
            "latest passage picked a second person line when the last passage itself names a full name");
    require(ditto::topic_named_messages(request, *found, corpus).size() == 3,
            "topic named-person prompt missing");
    require(ditto::topic_names_from_reading("Alice  Smith", corpus) == std::vector<std::string>({"Alice Smith"}),
            "topic person-reading name extraction differs");
    require(ditto::topic_draft_usable("Draft\nANSWER: June"), "valid topic draft not recognized");
    require(ditto::topic_draft_usable("Draft\u2028**ANSWER:** June"),
            "Unicode line-separated topic draft not recognized");
    require(!ditto::topic_draft_usable("These passages do not settle it."),
            "invalid topic draft accepted");
    const auto with_cards = ditto::topic_with_cards(*found, corpus, 30000);
    require(with_cards.notes.size() == 5, "contact person cards not added");
    ditto::Packet packet;
    packet.rendered = "old render";
    const auto lead = ditto::topic_lead(request.user_input, packet, corpus, 3, 30000);
    require(lead.packet.records.size() == 3 && lead.packet.rendered.empty(),
            "topic lead packet was not expanded and invalidated");
    require(lead.lead.find("[M1]") != std::string::npos,
            "topic lead labels missing");

    // Topic density counts matching excerpt paragraphs, not unrelated
    // paragraphs elsewhere in the original record. Only one of these three
    // notes has two or more matching passages, so there is no dense thread.
    const std::vector<ditto::MemoryPair> sparse_excerpts = {
        {"d1", "", "2026-03-01", "Orchid Delta one\n\nOrchid Delta two\n\nOrchid Delta three", "", 1},
        {"d2", "", "2026-03-02", "Orchid Delta four\n\nMisc unrelated context", "", 2},
        {"d3", "", "2026-03-03", "Orchid Delta five\n\nOther unrelated context", "", 3},
    };
    require(!ditto::find_topic("What changed in orchid delta?", sparse_excerpts, 3, 30000),
            "single matching paragraph per note incorrectly triggered topic path");
}
