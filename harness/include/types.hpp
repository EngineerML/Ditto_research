#pragma once

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

namespace ditto {

using json = nlohmann::json;

struct MemoryPair {
    std::string pair_id;
    std::string session_id;
    std::string timestamp;
    std::string prompt;
    std::string response;
    std::int64_t seq = 0;
};

struct Candidate {
    MemoryPair pair;
    double score = 0.0;
    bool anchored = false;
    bool pinned = false;
};

struct Packet {
    std::vector<MemoryPair> records;
    bool focused = false;
    std::string rendered;
};

struct ToolCall {
    std::string id;
    std::string name;
    std::string raw_args;
    json args = json::object();
    bool valid = true;
};

struct ModelResult {
    std::string content;
    std::vector<ToolCall> calls;
    std::string finish;
    json provider_error = json::object();
    int prompt_tokens = 0;
    int output_tokens = 0;
};

struct RunRequest {
    std::string case_id;
    std::string user_id;
    std::string system_prompt;
    std::string user_input;
    json tools = json::array();
    int bench_version = 9;
    std::string tool_endpoint;
    std::string inference_base_url;
    std::string tool_effect_protocol;
};

inline std::string normalize_user_id(const std::string& user_id) {
    // Blank input detection includes Unicode
    // separators as well as ASCII controls. Keep the original opaque ID when
    // any non-whitespace code point is present; never trim a nonblank ID.
    auto whitespace = [](std::uint32_t point) {
        return (point >= 0x09 && point <= 0x0d) ||
               (point >= 0x1c && point <= 0x20) || point == 0x85 ||
               point == 0xa0 || point == 0x1680 ||
               (point >= 0x2000 && point <= 0x200a) ||
               point == 0x2028 || point == 0x2029 || point == 0x202f ||
               point == 0x205f || point == 0x3000;
    };
    for (std::size_t at = 0; at < user_id.size();) {
        const auto first = static_cast<unsigned char>(user_id[at]);
        std::uint32_t point = first;
        std::size_t width = 1;
        if ((first & 0xe0u) == 0xc0u) { point = first & 0x1fu; width = 2; }
        else if ((first & 0xf0u) == 0xe0u) { point = first & 0x0fu; width = 3; }
        else if ((first & 0xf8u) == 0xf0u) { point = first & 0x07u; width = 4; }
        if (at + width > user_id.size()) return user_id;
        for (std::size_t part = 1; part < width; ++part) {
            const auto byte = static_cast<unsigned char>(user_id[at + part]);
            if ((byte & 0xc0u) != 0x80u) return user_id;
            point = (point << 6) | (byte & 0x3fu);
        }
        if (!whitespace(point)) return user_id;
        at += width;
    }
    return "default";
}

inline std::string json_string(const json& value, const char* key,
                               const std::string& fallback = "") {
    if (!value.is_object()) return fallback;
    auto it = value.find(key);
    return (it != value.end() && it->is_string()) ? it->get<std::string>() : fallback;
}

inline bool is_memory_read(const std::string& name) {
    return name == "search_memories" || name == "search_subjects" ||
           name == "fetch_memories" || name == "search_memories_in_subjects";
}

}  // namespace ditto
