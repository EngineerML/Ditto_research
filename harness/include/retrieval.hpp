#pragma once

#include <map>
#include <set>
#include <string>
#include <vector>

#include "types.hpp"

namespace ditto {

struct Ranking {
    std::vector<Candidate> ordered;
    bool anchored = false;
    std::set<char> anchor_kinds;
    // records.py::names_a_value: a subject/value anchor or a stated value in
    // the question, excluding references to the assistant itself.
    bool names_value = false;
    // Kept for packet link-hop expansion into records not selected by rank.
    std::vector<MemoryPair> corpus;
    // Optional records-lane embedding fusion supplied by the caller.
    std::vector<std::string> fused_order;
    bool meaning_order = false;
    int meaning_records = 5;
    int meaning_chars = 6000;
    int meaning_ceiling = 30000;
};

// Deterministic, user-local retrieval over a snapshot of already scoped pairs.
// The caller must not mix users in `pairs`.
Ranking rank(const std::vector<MemoryPair>& pairs, const std::string& question);

// Records-lane focus and query reduction to the asked part.
bool has_identifier_focus(const std::string& question,
                          const std::vector<Candidate>& ordered);
std::string asked_part(const std::string& text,
                       const std::vector<std::string>& keep_identifiers = {});

// The holder set for each recognized closest-record anchor, in anchor
// insertion order. Includes e/c/q/n/i/k and adjacent-word b anchors only.
std::vector<std::set<std::string>> closest_anchor_holders(
    const Ranking& ranking, const std::string& question);

// Builds the action-lane packet with arc, thread-first, evidence closure,
// and full-corpus link-hop enabled, then renders the composed string.
// Fused order/additions are available when the caller sets Ranking::fused_order.
// Topic lead and the records lane's focus/worksheet paths are outside this API.
Packet build_packet(const Ranking& ranking, const std::string& question,
                    int char_budget = 24000);

// Action-lane quoted-value reminder; compose_action_packet inserts it between
// memory context and Message, matching action.py's focus_block precursor.
std::vector<std::string> quoted_spans(const std::string& message);
std::string action_focus_block(const Packet& packet, const std::string& message);
std::string compose_action_packet(const Packet& packet, const std::string& message);
std::string compose_subset(const std::vector<MemoryPair>& records,
                           const std::string& message,
                           const std::map<std::string, std::string>& labels,
                           const std::string& precursor = "");

struct RecordsPacketOptions {
    int char_budget = 24000;
    std::vector<std::string> recall_pins;
    bool coverage = true;
    bool worksheet = true;
    bool arc = true;
    bool thread_first = true;
    bool closure = true;
    bool link_hop = true;
};

// Records-lane equivalent of pin() + build_packet() + compose() precursor.
// The caller remains responsible for recall, worksheet/finder model passes,
// and any early short-answer route.
Packet build_records_packet(const Ranking& ranking, const std::string& question,
                            const RecordsPacketOptions& options = {});

}  // namespace ditto
