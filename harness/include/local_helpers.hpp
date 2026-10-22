#pragma once

#include "types.hpp"

namespace ditto {

// Local model tools for the records lane. Textual results are JSON strings;
// calculator errors are JSON objects.
json calculate(const json& args);
json find_in_records(const Packet& packet, const json& args);

json calculate_tool_definition();
json find_tool_definition(bool ordering = true);

}  // namespace ditto
