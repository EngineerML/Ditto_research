#pragma once

#include <optional>
#include <string>
#include <vector>

#include "types.hpp"

namespace ditto {

inline constexpr const char* kDraftToolChoice = "none";
inline constexpr double kDeliberationMinSeconds = 60.0;
inline constexpr double kDraftBudgetShare = 0.5;

struct DeliberationPolicy {
    int drafts = 3;
    double temperature = 0.7;
    std::optional<int> seed;

    std::string shape_skip(int records, bool names_identifier, bool statement,
                           bool names_value) const;
    std::string skip_reason(int records, double seconds_left, int turns_left,
                            bool names_identifier, bool statement,
                            bool names_value) const;
    std::optional<int> draft_seed(int index) const;
    std::vector<int> indexes() const;
    double draft_deadline(double now, double deadline) const;
};

std::string reply_shape(const ModelResult& result);
std::string draft_slot(int index, const ModelResult& reply);
std::string failed_draft_slot(int index);
// `slots` are already ordered, beginning with opening draft 1. A failed draft
// should be represented with failed_draft_slot(). This only formats the model
// brief; scheduling, usage/event accounting, and cancellation remain in agent.
std::string deliberation_brief(const std::vector<std::string>& slots);

}  // namespace ditto
