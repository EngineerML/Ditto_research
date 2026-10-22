#pragma once

#include <optional>
#include <string>
#include <utility>

namespace ditto {

// Normalise the two non-ASCII hyphen
// characters and remove ordinary Markdown bold while preserving code spans.
std::string plain_type(const std::string& text);

// Strip the whole completion and return the
// last ANSWER slot, if any. An empty slot is present and distinct from no slot.
std::pair<std::string, std::optional<std::string>> parse_slot(
    const std::string& text);

}  // namespace ditto
