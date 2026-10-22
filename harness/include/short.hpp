#pragma once

#include <map>
#include <optional>
#include <string>
#include <vector>

#include "types.hpp"

namespace ditto {

// The packet's identifier focus is the input to the direct short-program path.
std::vector<Candidate> short_identifier_focus(const std::string& question,
                                               const std::vector<Candidate>& ordered);
bool short_records(const std::vector<Candidate>& focus, int max_chars);
std::string focus_token(const std::string& question,
                        const std::vector<Candidate>& focus);

struct ShortProgram {
    std::string token;
    std::vector<std::vector<MemoryPair>> groups;

    bool needs_order() const;
    json order_messages() const;
    // A missing order reply when needs_order() is true means fall back to the
    // normal records lane.
    std::optional<json> answer_messages(const RunRequest& request,
                                        const std::optional<std::string>& order_reply,
                                        bool full_dates = true) const;
};

std::optional<ShortProgram> plan_short_program(const std::string& question,
                                                const std::vector<Candidate>& focus,
                                                int max_chars = 30000);

struct TopicNotes {
    std::string phrase;
    int densest = 0;
    std::vector<MemoryPair> notes;
    std::map<std::string, std::string> excerpts;
};

std::optional<TopicNotes> find_topic(const std::string& question,
                                    const std::vector<MemoryPair>& pairs,
                                    int min_density = 3, int max_chars = 30000);
bool topic_fits(const TopicNotes& found, int max_chars);
// For contact questions, add short person cards after an optional model name
// reading. Empty `named` falls back to names found in the selected notes.
TopicNotes topic_with_cards(const TopicNotes& found,
                           const std::vector<MemoryPair>& corpus, int max_chars,
                           const std::vector<std::string>& named = {});
std::vector<std::string> topic_names_from_reading(const std::string& reply,
                                                  const std::vector<MemoryPair>& corpus);
json topic_messages(const RunRequest& request, const TopicNotes& found,
                    const std::vector<MemoryPair>& corpus,
                    const std::string& draft = "");
json topic_latest_messages(const RunRequest& request, const TopicNotes& found,
                           const std::vector<MemoryPair>& corpus);
json topic_named_messages(const RunRequest& request, const TopicNotes& found,
                          const std::vector<MemoryPair>& corpus);
bool topic_draft_usable(const std::string& reply);

struct TopicLead {
    Packet packet;
    std::string lead;
};

// The returned packet has updated records; its rendered string is deliberately
// cleared when records were added, so the caller must re-compose the packet.
TopicLead topic_lead(const std::string& question, const Packet& packet,
                     const std::vector<MemoryPair>& corpus,
                     int min_density = 3, int max_chars = 30000);

}  // namespace ditto
