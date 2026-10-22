#pragma once

#include <future>
#include <cstdint>
#include <list>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "store.hpp"
#include "types.hpp"

namespace ditto {

// JSON serialization must keep the insertion order of decoded tool arguments and
// use spaced separators. Keep that presentation in model-visible receipts
// and prompts; nlohmann::json's sorted object map would reorder the keys.
inline std::string python_json_dumps(const nlohmann::ordered_json& value) {
    if (value.is_object()) {
        std::string output = "{";
        bool first = true;
        for (auto it = value.begin(); it != value.end(); ++it) {
            if (!first) output += ", ";
            first = false;
            output += nlohmann::ordered_json(it.key()).dump() + ": " + python_json_dumps(it.value());
        }
        return output + "}";
    }
    if (value.is_array()) {
        std::string output = "[";
        bool first = true;
        for (const auto& item : value) {
            if (!first) output += ", ";
            first = false;
            output += python_json_dumps(item);
        }
        return output + "]";
    }
    return value.dump();
}

inline std::string tool_args_for_prompt(const ToolCall& call, bool omit_empty_keys = false) {
    nlohmann::ordered_json args = nlohmann::ordered_json::parse(call.raw_args, nullptr, false);
    if (!call.valid || !args.is_object())
        args = nlohmann::ordered_json::parse(call.args.dump(), nullptr, false);
    if (!args.is_object()) args = nlohmann::ordered_json::object();
    if (omit_empty_keys) args.erase("");
    return python_json_dumps(args);
}

inline std::string tool_args_for_assistant(const ToolCall& call) {
    return call.valid ? tool_args_for_prompt(call, true) : call.raw_args;
}

inline std::string model_strip(const std::string& value) {
    auto python_space = [](std::uint32_t point) {
        return (point >= 0x09 && point <= 0x0d) ||
               (point >= 0x1c && point <= 0x20) || point == 0x85 ||
               point == 0xa0 || point == 0x1680 ||
               (point >= 0x2000 && point <= 0x200a) ||
               point == 0x2028 || point == 0x2029 || point == 0x202f ||
               point == 0x205f || point == 0x3000;
    };
    std::size_t first = std::string::npos;
    std::size_t last = 0;
    for (std::size_t at = 0; at < value.size();) {
        const auto lead = static_cast<unsigned char>(value[at]);
        std::uint32_t point = lead;
        std::size_t width = 1;
        if ((lead & 0xe0u) == 0xc0u) { point = lead & 0x1fu; width = 2; }
        else if ((lead & 0xf0u) == 0xe0u) { point = lead & 0x0fu; width = 3; }
        else if ((lead & 0xf8u) == 0xf0u) { point = lead & 0x07u; width = 4; }
        if (at + width > value.size()) { point = lead; width = 1; }
        else for (std::size_t part = 1; part < width; ++part) {
            const auto byte = static_cast<unsigned char>(value[at + part]);
            if ((byte & 0xc0u) != 0x80u) { point = lead; width = 1; break; }
            point = (point << 6) | (byte & 0x3fu);
        }
        if (!python_space(point)) {
            if (first == std::string::npos) first = at;
            last = at + width;
        }
        at += width;
    }
    return first == std::string::npos ? "" : value.substr(first, last - first);
}

inline bool retry_empty_follow_up(const ModelResult& result) {
    // A nonblank reply ends the retry loop even when finish=length or it
    // carries tool calls; those properties are checked only after the loop.
    return model_strip(result.content).empty();
}

inline nlohmann::ordered_json ordered_fields(
    const json& value, std::initializer_list<const char*> keys) {
    nlohmann::ordered_json out = nlohmann::ordered_json::object();
    if (!value.is_object()) return out;
    for (const char* key : keys)
        if (value.contains(key)) out[key] = value.at(key);
    for (auto it = value.begin(); it != value.end(); ++it)
        if (!out.contains(it.key())) out[it.key()] = it.value();
    return out;
}

inline std::string memory_tool_content(const std::string& name, const json& output) {
    if (output.is_string()) return output.get<std::string>();
    if (!output.is_object()) return output.dump();
    nlohmann::ordered_json ordered = nlohmann::ordered_json::object();
    const char* array_key = name == "search_subjects" ? "subjects" : "memories";
    if (output.contains(array_key) && output.at(array_key).is_array()) {
        nlohmann::ordered_json entries = nlohmann::ordered_json::array();
        for (const auto& item : output.at(array_key)) {
            if (name == "search_subjects")
                entries.push_back(ordered_fields(item, {"id", "name", "description"}));
            else if (name == "search_memories")
                entries.push_back(ordered_fields(item, {"pair_id", "timestamp", "session_id", "text"}));
            else if (name == "fetch_memories")
                entries.push_back(ordered_fields(item,
                    {"pair_id", "timestamp", "session_id", "prompt", "response"}));
            else
                entries.push_back(ordered_fields(item, {"pair_id", "timestamp", "summary"}));
        }
        ordered[array_key] = std::move(entries);
    }
    if (output.contains("served_by")) ordered["served_by"] = output.at("served_by");
    if (output.contains("note")) ordered["note"] = output.at("note");
    for (auto it = output.begin(); it != output.end(); ++it)
        if (!ordered.contains(it.key())) ordered[it.key()] = it.value();
    return python_json_dumps(ordered);
}

// The short order pass is shared between cases. A future makes concurrent
// cases with the same notes wait for the same read.
class ShortOrderCache {
public:
    template<class Reader>
    std::optional<std::string> get_or_read(const std::string& key, Reader&& read) {
        std::shared_ptr<Entry> entry;
        bool owner = false;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            const auto held = readings_.find(key);
            if (held != readings_.end()) {
                entry = held->second.entry;
            } else {
                owner = true;
                entry = std::make_shared<Entry>();
                order_.push_back(key);
                readings_.emplace(key, Held{entry, std::prev(order_.end())});
                while (readings_.size() > 512) {
                    readings_.erase(order_.front());
                    order_.pop_front();
                }
            }
        }
        if (!owner) return entry->future.get();
        std::optional<std::string> reply;
        try {
            reply = read();
        } catch (...) {
            entry->promise.set_value(std::nullopt);
            remove_failed(key, entry);
            throw;
        }
        entry->promise.set_value(reply);
        if (!reply) remove_failed(key, entry);
        return reply;
    }

    std::size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return readings_.size();
    }

private:
    struct Entry {
        std::promise<std::optional<std::string>> promise;
        std::shared_future<std::optional<std::string>> future = promise.get_future().share();
    };
    struct Held {
        std::shared_ptr<Entry> entry;
        std::list<std::string>::iterator position;
    };
    void remove_failed(const std::string& key, const std::shared_ptr<Entry>& entry) {
        std::lock_guard<std::mutex> lock(mutex_);
        const auto held = readings_.find(key);
        if (held != readings_.end() && held->second.entry == entry) {
            order_.erase(held->second.position);
            readings_.erase(held);
        }
    }

    mutable std::mutex mutex_;
    std::list<std::string> order_;
    std::unordered_map<std::string, Held> readings_;
};

struct AgentConfig {
    std::string db_path = "/tmp/dittobench.db";
    std::string model = "openai/gpt-oss-20b";
    std::string provider = "openrouter";
    std::string inference_base_url;
    std::string ollama_base_url = "http://localhost:11434";
    std::string token = "ticket";
    bool openrouter_style = false;
    std::string prompts_path = "/app/assets/prompts.json";
    int case_budget_seconds = 285;
    int llm_timeout_seconds = 100;
    int llm_max_attempts = 2;
    int tool_timeout_seconds = 20;
    int embed_timeout_seconds = 30;
    int action_max_turns = 8;
    int records_max_turns = 12;
    int packet_char_budget = 24000;
    int long_packet_chars = 30000;
    int meaning_records = 5;
    int meaning_chars = 6000;
    int max_output_tokens = 6000;
    int action_max_tokens = 6000;
    int recall_max_tokens = 2000;
    std::string action_effort = "medium";
    std::string records_effort = "medium";
    std::string recall_effort = "low";
    std::string short_effort = "medium";
    bool records_effort_high = false;
    int short_max_chars = 30000;
    int short_max_tokens = 12000;
    int story_max_chars = 30000;
    int story_min_density = 3;
    int order_max_tokens = 16000;
    int search_record_chars = 7000;
    int search_long_records = 2;
    int search_passes = 5;
    int drafts = 3;
    int sampling_seed = 42;
    double sampling_temperature = 0.0;
    std::optional<double> sampling_top_p;
    double draft_temperature = 0.7;
    double search_temperature = 0.7;
    bool mock_model = false;
    bool embeddings = true;
    bool meaning_order = true;
    bool short_programs = true;
    bool short_story = true;
    bool topic_draft = true;
    bool action_topic = true;
    bool deliberation = true;
    bool follow_up = true;
    bool follow_up_retry = true;
    bool finder_order = true;
    bool program_full_dates = true;
    bool result_read = true;
    bool result_suffix = true;
    bool short_order_cache = true;

    static AgentConfig from_env();
};

RunRequest parse_run_request(const json& body);

class Agent {
public:
    Agent(AgentConfig config, Store& store);
    json seed(const json& body);
    json run(const RunRequest& request);

private:
    AgentConfig config_;
    Store& store_;
    json prompts_;
    ShortOrderCache order_readings_;
};

}  // namespace ditto
