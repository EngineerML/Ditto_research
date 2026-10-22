#pragma once

#include <set>
#include <string>
#include <vector>

#include "types.hpp"

namespace ditto {

struct Lane {
    std::string name;
    std::string reason;
};

// Runtime defaults from Levers.from_env(), not classify()'s standalone defaults.
struct LaneLevers {
    bool typo_cues = true;
    bool route_preamble = true;
    bool route_asking = true;
    bool route_anchor = true;
    bool route_lexicon = true;
    bool route_operands = true;
    bool route_save = true;
    bool short_route = true;
};

bool reads_state(const std::string& tool_name);
Lane classify_lane(const std::string& request, const json& tool_catalog,
                   const LaneLevers& levers = {});
bool own_records_question(const std::string& request, const json& tool_catalog);

// `pairs` must contain only the current user's records. Supplying the
// retrieval index's exact question-anchor kinds preserves the
// about-own-records decision. An empty set means no question anchors.
bool about_own_records(const std::string& request, const json& tool_catalog,
                       const Lane& lane, const std::vector<MemoryPair>& pairs,
                       const std::set<char>& anchor_kinds = {});

// Apply the three post-classification overrides in CaseRunner.run, in order.
Lane refine_lane(const Lane& initial, const std::string& request,
                 const json& tool_catalog, bool identifier_focus,
                 const std::vector<MemoryPair>& pairs,
                 const std::set<char>& anchor_kinds = {},
                 bool short_route = true);

}  // namespace ditto
