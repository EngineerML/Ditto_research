#pragma once

#include <optional>
#include <set>
#include <string>
#include <vector>

#include "types.hpp"

namespace ditto {

struct SearchOptions {
    int search_record_chars = 7000;
    int search_long_records = 2;
    int search_passes = 5;
    double search_temperature = 0.7;
    std::optional<int> search_seed = 42;
    bool finder_order = true;
    bool subject_discipline = true;
    bool thread_reading = true;
};

struct SearchPass {
    int which = 1;
    std::optional<double> temperature;
    std::optional<int> seed;
};

struct SearchPlan {
    bool holds_long = false;
    bool short_identifier = false;
    bool searchable = false;
    bool finder = false;
    bool should_run = false;
    double budget_seconds = 0.0;
    std::string index;
    std::string question;
    json messages = json::array();
    json tools = json::array();
    std::vector<SearchPass> passes;
};

// Pure selection/prompt planner for records.py searchable(), finder_for(),
// searches() and search_pass(). `seconds_left` is deadline-now at entry.
// `prompts` is the submitted prompts.json asset; no network is called.
SearchPlan plan_records_search(const RunRequest& request, const Packet& packet,
                               const json& prompts, double seconds_left,
                               const SearchOptions& options = {});

struct SearchNote {
    int which = 1;
    std::string note;
};

// The search passes' assistant/tool messages are supplied separately by caller.
// This returns the advisory user messages appended after the first pass.
json search_note_messages(const std::string& first_note,
                          const std::vector<SearchNote>& later_notes);

// Find the closest records given holder-id sets for already selected anchor
// terms of kinds e,c,q,n,i,k,b. The caller supplies these from its index.
Packet closest_records(const Packet& packet,
                       const std::vector<std::set<std::string>>& term_holders);

// Timeline-shape and timeline entry gates. The caller supplies
// names_value from its full anchor/value index.
bool records_timeline_shape(const RunRequest& request, const Packet& packet,
                            bool statement, bool names_value,
                            int drafts = 3);
bool records_timeline_ready(const RunRequest& request, const Packet& packet,
                            bool statement, bool names_value,
                            double seconds_left, int drafts = 3);
json timeline_note_message(const std::string& note);

// Model-message construction for the optional closest reading / timeline
// passes. `full` supplies original M1.. marks for a closest subset.
json closest_reading_messages(const RunRequest& request, const Packet& closest,
                              const Packet& full, const json& prompts,
                              const SearchOptions& options = {});
json closest_reading_note(const Packet& closest, const Packet& full,
                          const std::string& note);
json timeline_messages(const RunRequest& request, const std::string& composed,
                       const json& prompts, const SearchOptions& options = {});

}  // namespace ditto
