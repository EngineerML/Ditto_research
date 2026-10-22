#pragma once

#include <string>

#include "types.hpp"

namespace ditto {

// Action-lane tool presentation preserves every supplied tool,
// puts catalog-routed tools first, applies presentation scoring to the rest,
// and wraps definitions as OpenAI function schemas.
json action_tools(const json& catalog, const std::string& message);

}  // namespace ditto
