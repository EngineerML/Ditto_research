#include "agent.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <future>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <optional>
#include <regex>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

#include <openssl/sha.h>

#include "embedding.hpp"
#include "deliberation.hpp"
#include "local_helpers.hpp"
#include "lane.hpp"
#include "network.hpp"
#include "output.hpp"
#include "retrieval.hpp"
#include "records_advice.hpp"
#include "short.hpp"
#include "surface.hpp"

namespace ditto {
namespace {

using Clock = std::chrono::steady_clock;
using TimePoint = Clock::time_point;

std::string env(const char* key, const std::string& fallback = "") {
    const char* raw = std::getenv(key);
    if (!raw || !*raw) return fallback;
    std::string value(raw);
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return fallback;
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

int env_int(const char* key, int fallback, int minimum, int maximum) {
    try {
        const auto value = env(key);
        if (value.empty()) return fallback;
        const int parsed = std::stoi(value);
        return std::clamp(parsed, minimum, maximum);
    } catch (...) {
        return fallback;
    }
}

bool env_flag(const char* key, bool fallback) {
    auto value = env(key);
    if (value.empty()) return fallback;
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value == "1" || value == "true" || value == "yes" || value == "on";
}

double env_double(const char* key, double fallback, double minimum, double maximum) {
    try {
        const auto raw = env(key);
        if (raw.empty()) return fallback;
        const double number = std::stod(raw);
        return std::isfinite(number) ? std::clamp(number, minimum, maximum) : fallback;
    } catch (...) {
        return fallback;
    }
}

std::string trim(std::string value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

void replace_all(std::string& text, const std::string& needle, const std::string& value) {
    if (needle.empty()) return;
    std::size_t position = 0;
    while ((position = text.find(needle, position)) != std::string::npos) {
        text.replace(position, needle.size(), value);
        position += value.size();
    }
}

std::string format(std::string text, const std::vector<std::pair<std::string, std::string>>& values) {
    for (const auto& [key, value] : values) replace_all(text, "{" + key + "}", value);
    return text;
}

std::string prompt(const json& prompts, const std::string& section,
                   const std::string& key, const std::string& fallback = "") {
    if (!prompts.is_object() || !prompts.contains(section)) return fallback;
    return json_string(prompts[section], key.c_str(), fallback);
}

std::string with_operator(const std::string& base, const std::string& operator_prompt,
                          const std::string& seam) {
    const std::string operator_text = trim(operator_prompt);
    return operator_text.empty() ? base : base + "\n\n" + seam + "\n" + operator_text;
}

int remaining(TimePoint deadline, int ceiling) {
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - Clock::now()).count();
    if (ms <= 0) return 0;
    return std::min(ceiling, static_cast<int>((ms + 999) / 1000));
}

double remaining_seconds(TimePoint deadline) {
    return std::chrono::duration<double>(deadline - Clock::now()).count();
}

bool has_tool(const RunRequest& request, const std::string& name) {
    for (const auto& item : request.tools) {
        if (json_string(item, "name") == name) return true;
    }
    return false;
}

json tool_spec(const RunRequest& request, const std::string& name) {
    for (const auto& item : request.tools) {
        if (json_string(item, "name") == name) return item;
    }
    return json::object();
}

json openai_tools(const RunRequest& request) {
    json result = json::array();
    for (const auto& item : request.tools) {
        if (!item.is_object()) continue;
        const std::string name = json_string(item, "name");
        if (name.empty()) continue;
        const json parameters = item.contains("parameters") && item["parameters"].is_object() &&
                                        !item["parameters"].empty()
                                    ? item["parameters"]
                                    : json{{"type", "object"}, {"properties", json::object()}};
        const std::string description = json_string(item, "description", name);
        result.push_back({{"type", "function"},
                          {"function", {{"name", name},
                                        {"description", description.empty() ? name : description},
                                        {"parameters", parameters}}}});
    }
    return result;
}

std::optional<std::string> answer_slot(const std::string& text) {
    return parse_slot(text).second;
}

json assistant_message(const ModelResult& result) {
    json calls = json::array();
    for (const auto& call : result.calls) {
        calls.push_back({{"id", call.id}, {"type", "function"},
                         {"function", {{"name", call.name},
                                       {"arguments", tool_args_for_assistant(call)}}}});
    }
    return {{"role", "assistant"}, {"content", result.content.empty() ? json() : json(result.content)},
            {"tool_calls", calls}};
}

bool unfilled(const json& value) {
    if (value.is_null()) return true;
    if (value.is_string()) return value.get<std::string>().empty();
    if (value.is_array() && !value.empty()) {
        return std::all_of(value.begin(), value.end(), [](const json& item) {
            return item.is_string() && item.get<std::string>().empty();
        });
    }
    return false;
}

std::string schema_issue(const json& args, const json& spec) {
    if (!args.is_object()) return "arguments must be a JSON object";
    const json schema = spec.is_object() && spec.contains("parameters") &&
                                spec["parameters"].is_object() ? spec["parameters"] : json::object();
    if (schema.contains("required") && schema["required"].is_array()) {
        std::vector<std::string> missing;
        for (const auto& name : schema["required"]) {
            if (!name.is_string()) continue;
            const std::string key = name.get<std::string>();
            if (!args.contains(key) || unfilled(args[key])) missing.push_back(key);
        }
        if (!missing.empty()) {
            std::string names;
            for (const auto& name : missing) names += (names.empty() ? "" : ", ") + name;
            return "needs " + names;
        }
    }
    const json properties = schema.contains("properties") && schema["properties"].is_object()
                                ? schema["properties"] : json::object();
    std::vector<std::string> problems;
    for (auto it = args.begin(); it != args.end(); ++it) {
        if (!properties.contains(it.key()) || !properties[it.key()].is_object() || it.value().is_null()) continue;
        const json& property = properties[it.key()];
        const std::string expected = json_string(property, "type");
        const json& value = it.value();
        const bool okay = expected == "string" ? value.is_string() :
                          expected == "integer" ? value.is_number_integer() :
                          expected == "number" ? value.is_number() || value.is_boolean() :
                          expected == "boolean" ? value.is_boolean() :
                          expected == "array" ? value.is_array() :
                          expected == "object" ? value.is_object() : true;
        if (!okay) {
            problems.push_back(it.key() + " must be " + expected);
            continue;
        }
        if (expected == "array" && property.contains("items") && property["items"].is_object()) {
            const std::string item_type = json_string(property["items"], "type");
            for (const auto& item : value) {
                const bool item_okay = item_type == "string" ? item.is_string() :
                                       item_type == "integer" ? item.is_number_integer() || item.is_boolean() :
                                       item_type == "number" ? item.is_number() || item.is_boolean() :
                                       item_type == "boolean" ? item.is_boolean() :
                                       item_type == "object" ? item.is_object() : true;
                if (!item_okay) {
                    problems.push_back(it.key() + " must be an array of " + item_type + " values");
                    break;
                }
            }
        }
    }
    std::string issue;
    for (const auto& problem : problems) issue += (issue.empty() ? "" : "; ") + problem;
    return issue;
}

std::string text_key(const std::string& value) {
    std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
    SHA256(reinterpret_cast<const unsigned char*>(value.data()), value.size(), digest.data());
    static constexpr char hex[] = "0123456789abcdef";
    std::string key;
    key.reserve(digest.size() * 2);
    for (unsigned char byte : digest) {
        key.push_back(hex[byte >> 4]);
        key.push_back(hex[byte & 15]);
    }
    return key;
}

std::string record_text(const MemoryPair& pair) {
    return pair.prompt + "\n" + pair.response;
}

std::size_t codepoints(const std::string& value) {
    return static_cast<std::size_t>(std::count_if(value.begin(), value.end(),
        [](unsigned char c) { return (c & 0xc0u) != 0x80u; }));
}

std::string ledger_text(const std::vector<std::string>& entries) {
    std::string out;
    for (std::size_t index = 0; index < entries.size(); ++index) {
        if (!out.empty()) out += '\n';
        out += std::to_string(index + 1) + ". " + entries[index];
    }
    return out;
}

}  // namespace

AgentConfig AgentConfig::from_env() {
    AgentConfig value;
    value.db_path = env("DITTOBENCH_DB", value.db_path);
    value.model = env("DITTOBENCH_MODEL", value.model);
    value.provider = lower(env("DITTOBENCH_PROVIDER", value.provider));
    const std::string bench_base_url = env("DITTOBENCH_INFERENCE_BASE_URL");
    value.ollama_base_url = env("OLLAMA_BASE_URL", value.ollama_base_url);
    if (value.provider == "platform" || value.provider == "chutes" ||
        (value.provider != "openrouter" && value.provider != "openai" &&
         value.provider != "ollama")) {
        value.inference_base_url = bench_base_url;
        if (value.inference_base_url.empty()) value.inference_base_url = env("CHUTES_BASE_URL");
        if (value.inference_base_url.empty()) value.inference_base_url = env("OPENAI_BASE_URL");
        if (value.inference_base_url.empty()) value.inference_base_url = env("OPENROUTER_BASE_URL");
    } else if (value.provider == "ollama") {
        value.inference_base_url = value.ollama_base_url;
        while (!value.inference_base_url.empty() && value.inference_base_url.back() == '/')
            value.inference_base_url.pop_back();
        value.inference_base_url += "/v1";
        value.token = "ollama";
    } else if (value.provider == "openai") {
        value.inference_base_url = env("OPENAI_BASE_URL");
        value.token = env("OPENAI_API_KEY");
    } else {
        value.token = env("OPENROUTER_API_KEY");
        if (!value.token.empty()) {
            value.inference_base_url = env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1");
            value.openrouter_style = true;
        } else {
            value.inference_base_url = bench_base_url;
            value.token = "ticket";
        }
    }
    value.prompts_path = env("DITTO_PROMPTS_PATH", value.prompts_path);
    value.case_budget_seconds = env_int("HARNESS_CASE_BUDGET_SECONDS", 285, 1, 3600);
    value.llm_timeout_seconds = env_int("HARNESS_LLM_TIMEOUT_SECONDS", 100, 1, 600);
    value.llm_max_attempts = env_int("HARNESS_LLM_MAX_ATTEMPTS", 2, 1, 20);
    value.tool_timeout_seconds = env_int("HARNESS_TOOL_TIMEOUT_SECONDS", 20, 1, 600);
    value.embed_timeout_seconds = env_int("HARNESS_EMBED_TIMEOUT_SECONDS", 30, 1, 600);
    value.action_max_turns = env_int("HARNESS_ACTION_MAX_TURNS", 8, 1, 100);
    value.records_max_turns = env_int("HARNESS_MAX_MODEL_TURNS", 12, 1, 100);
    value.packet_char_budget = env_int("HARNESS_PACKET_CHAR_BUDGET", 24000, 100, 1000000);
    value.long_packet_chars = env_int("HARNESS_LONG_PACKET_CHARS", 30000, 100, 1000000);
    value.meaning_records = env_int("HARNESS_MEANING_RECORDS", 5, 0, 1000);
    value.meaning_chars = env_int("HARNESS_MEANING_CHARS", 6000, 0, 1000000);
    value.max_output_tokens = env_int("HARNESS_MAX_OUTPUT_TOKENS", 6000, 1, 64000);
    value.action_max_tokens = env_int("HARNESS_ACTION_MAX_TOKENS", 6000, 1, 64000);
    value.recall_max_tokens = env_int("HARNESS_RECALL_MAX_TOKENS", 2000, 1, 64000);
    value.action_effort = lower(env("HARNESS_ACTION_REASONING_EFFORT", value.action_effort));
    value.records_effort = lower(env("HARNESS_RECORDS_REASONING_EFFORT", value.records_effort));
    value.recall_effort = lower(env("HARNESS_RECALL_REASONING_EFFORT", value.recall_effort));
    value.short_effort = lower(env("HARNESS_SHORT_EFFORT", value.short_effort));
    value.records_effort_high = env_flag("HARNESS_RECORDS_EFFORT_HIGH", false);
    value.short_max_chars = env_int("HARNESS_SHORT_MAX_CHARS", 30000, 100, 1000000);
    value.short_max_tokens = env_int("HARNESS_SHORT_MAX_TOKENS", 12000, 1, 64000);
    value.story_max_chars = env_int("HARNESS_STORY_MAX_CHARS", 30000, 100, 1000000);
    value.story_min_density = env_int("HARNESS_STORY_MIN_DENSITY", 3, 1, 1000);
    value.order_max_tokens = env_int("HARNESS_ORDER_MAX_TOKENS", 16000, 1, 64000);
    value.search_record_chars = env_int("HARNESS_SEARCH_RECORD_CHARS", 7000, 1, 1000000);
    value.search_long_records = env_int("HARNESS_SEARCH_LONG_RECORDS", 2, 0, 1000);
    value.search_passes = env_int("HARNESS_SEARCH_PASSES", 5, 1, 20);
    value.drafts = env_int("HARNESS_DRAFTS", 3, 0, 20);
    value.sampling_seed = env_int("HARNESS_SAMPLING_SEED", 42, 0, 2147483647);
    value.sampling_temperature = env_double("HARNESS_SAMPLING_TEMPERATURE", 0.0, 0.0, 2.0);
    if (const std::string raw_top_p = env("HARNESS_SAMPLING_TOP_P"); !raw_top_p.empty()) {
        try {
            std::size_t consumed = 0;
            const double parsed = std::stod(raw_top_p, &consumed);
            if (consumed == raw_top_p.size() && std::isfinite(parsed))
                value.sampling_top_p = parsed;
        } catch (const std::exception&) {
        }
    }
    value.draft_temperature = env_double("HARNESS_DRAFT_TEMPERATURE", 0.7, 0.0, 2.0);
    value.search_temperature = env_double("HARNESS_SEARCH_TEMPERATURE", 0.7, 0.0, 2.0);
    value.mock_model = env_flag("HARNESS_MOCK_MODEL", false);
    value.embeddings = env_flag("HARNESS_EMBEDDINGS", true);
    value.meaning_order = env_flag("HARNESS_MEANING_ORDER", true);
    value.short_programs = env_flag("HARNESS_SHORT_PROGRAMS", true);
    value.short_story = env_flag("HARNESS_SHORT_STORY", true);
    value.topic_draft = env_flag("HARNESS_TOPIC_DRAFT", true);
    value.action_topic = env_flag("HARNESS_ACTION_TOPIC", true);
    value.deliberation = env_flag("HARNESS_DELIBERATION", true);
    value.follow_up = env_flag("HARNESS_FOLLOW_UP", true);
    value.follow_up_retry = env_flag("HARNESS_FOLLOW_UP_RETRY", true);
    value.finder_order = env_flag("HARNESS_FINDER_ORDER", true);
    value.program_full_dates = env_flag("HARNESS_PROGRAM_FULL_DATES", true);
    value.result_read = env_flag("HARNESS_RESULT_READ", true);
    value.result_suffix = env_flag("HARNESS_RESULT_SUFFIX", true);
    return value;
}

RunRequest parse_run_request(const json& body) {
    if (!body.is_object()) throw std::invalid_argument("run body must be an object");
    if (!body.contains("case_id") || !body["case_id"].is_string() ||
        !body.contains("user_input") || !body["user_input"].is_string()) {
        throw std::invalid_argument("case_id and user_input are required strings");
    }
    RunRequest request;
    request.case_id = body["case_id"].get<std::string>();
    request.user_id = json_string(body, "user_id");
    request.system_prompt = json_string(body, "system_prompt");
    request.user_input = body["user_input"].get<std::string>();
    if (body.contains("tools") && body["tools"].is_array()) request.tools = body["tools"];
    if (body.contains("bench_version") && body["bench_version"].is_number_integer())
        request.bench_version = body["bench_version"].get<int>();
    request.tool_endpoint = json_string(body, "tool_endpoint");
    request.inference_base_url = trim(json_string(body, "inference_base_url"));
    request.tool_effect_protocol = json_string(body, "tool_effect_protocol");
    return request;
}

Agent::Agent(AgentConfig config, Store& store) : config_(std::move(config)), store_(store) {
    std::ifstream file(config_.prompts_path);
    if (!file) file.open("assets/prompts.json");
    if (!file) throw std::runtime_error("prompts.json is missing");
    file >> prompts_;
    std::string extra_path = config_.prompts_path;
    const auto slash = extra_path.find_last_of('/');
    extra_path = (slash == std::string::npos ? "" : extra_path.substr(0, slash + 1)) + "action_extra.json";
    std::ifstream extra(extra_path);
    if (!extra) extra.open("assets/action_extra.json");
    if (extra) extra >> prompts_["action_extra"];
}

json Agent::seed(const json& body) {
    json result = store_.seed(body);
    if (!config_.embeddings || !body.contains("pairs") || !body["pairs"].is_array()) return result;
    std::vector<std::string> hashes;
    std::vector<std::string> texts;
    std::set<std::string> seen;
    for (const auto& item : body["pairs"]) {
        if (!item.is_object()) continue;
        const std::string text = json_string(item, "prompt") + "\n" + json_string(item, "response");
        const std::string key = text_key(text);
        if (seen.insert(key).second) { hashes.push_back(key); texts.push_back(text); }
    }
    if (hashes.empty()) return result;
    const std::string uid = normalize_user_id(json_string(body, "user_id"));
    const auto held = store_.vectors(uid, hashes);
    std::vector<std::string> missing_hashes, missing_texts;
    for (std::size_t i = 0; i < hashes.size(); ++i) {
        if (!held.contains(hashes[i])) { missing_hashes.push_back(hashes[i]); missing_texts.push_back(texts[i]); }
    }
    if (missing_hashes.empty()) return result;
    try {
        Embedder embedder(config_.ollama_base_url, config_.embed_timeout_seconds);
        const auto vectors = embedder.embed(missing_texts);
        if (vectors.size() != missing_hashes.size())
            throw EmbeddingError("embedding vector count mismatch");
        std::unordered_map<std::string, std::vector<float>> writes;
        for (std::size_t i = 0; i < vectors.size() && i < missing_hashes.size(); ++i)
            writes.emplace(missing_hashes[i], vectors[i]);
        store_.put_vectors(uid, writes);
    } catch (const EmbeddingError& error) {
        std::cerr << "seed embedding unavailable user=" << uid << ": " << error.what() << '\n';
        // The v13 /seed 2xx is an ingest acknowledgement for every pair.
        // SQLite storage is already committed and a retry is idempotent, but
        // do not acknowledge while required vectors remain unavailable.
        throw std::runtime_error("seed embedding incomplete");
    }
    return result;
}

json Agent::run(const RunRequest& request) {
    const auto started = Clock::now();
    const auto deadline = started + std::chrono::seconds(config_.case_budget_seconds);
    const std::string user_id = normalize_user_id(request.user_id);
    const auto pairs = store_.all_pairs(user_id);
    Ranking ranking = rank(pairs, request.user_input);
    const Lane route = refine_lane(classify_lane(request.user_input, request.tools),
                                   request.user_input, request.tools,
                                   has_identifier_focus(request.user_input, ranking.ordered),
                                   pairs, ranking.anchor_kinds);
    const std::string lane = route.name;
    std::optional<ShortProgram> short_program;
    std::optional<TopicNotes> short_topic;
    if (lane == "records" && route.reason != "statement" &&
        own_records_question(request.user_input, request.tools)) {
        const auto focus = short_identifier_focus(request.user_input, ranking.ordered);
        if (!focus.empty() && config_.short_programs)
            short_program = plan_short_program(request.user_input, focus, config_.short_max_chars);
        else if (focus.empty() && config_.short_story) {
            auto found = find_topic(request.user_input, pairs,
                                    config_.story_min_density, config_.story_max_chars);
            if (found && topic_fits(*found, config_.story_max_chars))
                short_topic = std::move(found);
        }
    }
    ranking.meaning_records = config_.meaning_records;
    ranking.meaning_chars = config_.meaning_chars;
    ranking.meaning_order = config_.meaning_order;
    ranking.meaning_ceiling = config_.long_packet_chars;
    bool meaning_order_attempted = false;
    auto compute_meaning_order = [&]() {
        if (meaning_order_attempted || lane != "records" || !config_.embeddings || pairs.empty())
            return;
        meaning_order_attempted = true;
        try {
            // UserIndex.nodes follows (timestamp, pair_id) order,
            // independently of the store's (timestamp, seq) order.
            std::vector<MemoryPair> meaning_pairs = pairs;
            std::sort(meaning_pairs.begin(), meaning_pairs.end(), [](const auto& a, const auto& b) {
                return std::tie(a.timestamp, a.pair_id) < std::tie(b.timestamp, b.pair_id);
            });
            const std::string semantic_query = has_identifier_focus(request.user_input, ranking.ordered)
                                                   ? asked_part(request.user_input) : request.user_input;
            const Ranking semantic_rank = semantic_query == request.user_input
                                              ? ranking : rank(pairs, semantic_query);
            std::vector<std::string> missing_hashes;
            std::vector<std::string> missing_texts;
            const auto all_hashes = [&]() {
                std::vector<std::string> keys;
                keys.reserve(meaning_pairs.size());
                for (const auto& pair : meaning_pairs) keys.push_back(text_key(record_text(pair)));
                return keys;
            }();
            auto held = store_.vectors(user_id, all_hashes);
            for (std::size_t i = 0; i < meaning_pairs.size(); ++i) {
                if (held.contains(all_hashes[i])) continue;
                missing_hashes.push_back(all_hashes[i]);
                missing_texts.push_back(record_text(meaning_pairs[i]));
            }
            std::vector<std::string> embed_texts{semantic_query};
            embed_texts.insert(embed_texts.end(), missing_texts.begin(), missing_texts.end());
            Embedder embedder(config_.ollama_base_url, config_.embed_timeout_seconds);
            const auto vectors = embedder.embed(embed_texts);
            if (vectors.size() != embed_texts.size()) throw EmbeddingError("embedding vector count mismatch");
            std::unordered_map<std::string, std::vector<float>> fresh;
            for (std::size_t i = 0; i < missing_hashes.size(); ++i)
                fresh[missing_hashes[i]] = vectors[i + 1];
            store_.put_vectors(user_id, fresh);
            held.insert(fresh.begin(), fresh.end());
            std::vector<std::pair<double, std::string>> dense;
            for (std::size_t i = 0; i < meaning_pairs.size(); ++i) {
                const auto it = held.find(all_hashes[i]);
                if (it == held.end() || it->second.size() != vectors[0].size()) continue;
                double score = 0.0;
                for (std::size_t j = 0; j < vectors[0].size(); ++j)
                    score += static_cast<double>(vectors[0][j]) *
                             static_cast<double>(it->second[j]);
                dense.emplace_back(score, meaning_pairs[i].pair_id);
            }
            std::sort(dense.begin(), dense.end(), [](const auto& a, const auto& b) {
                return a.first != b.first ? a.first > b.first : a.second < b.second;
            });
            std::map<std::string, double> scores;
            std::vector<std::string> insertion;
            auto absorb = [&](const std::string& id, std::size_t rank) {
                if (!scores.contains(id)) insertion.push_back(id);
                scores[id] += 1.0 / static_cast<double>(60 + rank);
            };
            for (std::size_t i = 0; i < semantic_rank.ordered.size(); ++i)
                absorb(semantic_rank.ordered[i].pair.pair_id, i + 1);
            for (std::size_t i = 0; i < dense.size(); ++i)
                absorb(dense[i].second, i + 1);
            std::stable_sort(insertion.begin(), insertion.end(), [&](const auto& a, const auto& b) {
                return scores.at(a) > scores.at(b);
            });
            ranking.fused_order = std::move(insertion);
        } catch (const EmbeddingError& error) {
            std::cerr << "case=" << request.case_id << " embedding unavailable: " << error.what() << '\n';
        }
    };
    if (!short_program && !short_topic) compute_meaning_order();
    const std::string base_url = request.inference_base_url.empty()
                                     ? config_.inference_base_url : request.inference_base_url;
    std::optional<ModelClient> model;
    if (!config_.mock_model)
        model.emplace(base_url, config_.model,
                      request.inference_base_url.empty() ? config_.token : "ticket",
                      request.inference_base_url.empty() && config_.openrouter_style,
                      config_.llm_max_attempts, config_.sampling_top_p);
    ToolEndpoint endpoint;
    json observed = json::array();
    int prompt_tokens = 0;
    int output_tokens = 0;
    std::string final_text;
    std::unordered_map<std::string, DeliveryState> sent;
    std::unordered_map<std::string, int> sent_count;
    std::vector<std::string> ledger;
    int changes = 0;
    std::unordered_map<std::string, int> read_after;
    const json offered = lane == "action" ? action_tools(request.tools, request.user_input)
                                          : openai_tools(request);
    auto call_model = [&](const json& messages, const json& tools, int max_tokens,
                          const std::string& effort, int timeout, const std::string& tool_choice = "auto",
                          bool once = false,
                          double temperature = std::numeric_limits<double>::quiet_NaN(),
                          int seed_offset = 0,
                          std::optional<TimePoint> local_deadline = std::nullopt) -> ModelResult {
        if (config_.mock_model) return ModelResult{"Mock reply.\nANSWER: mock", {}, "stop", json::object(), 0, 0};
        const TimePoint effective_deadline = local_deadline ?
            std::min(deadline, *local_deadline) : deadline;
        const int window = remaining(effective_deadline, timeout);
        if (window < 1) throw ModelError("case deadline exhausted");
        try {
            ModelResult result = model->complete(messages, tools, max_tokens, effort,
                                                 std::isnan(temperature) ? config_.sampling_temperature : temperature,
                                                 std::to_string(config_.sampling_seed + seed_offset),
                                                 timeout, tool_choice, once,
                                                 remaining_seconds(effective_deadline));
            prompt_tokens += result.prompt_tokens;
            output_tokens += result.output_tokens;
            return result;
        } catch (const ModelError& error) {
            prompt_tokens += error.prompt_tokens;
            output_tokens += error.output_tokens;
            throw;
        }
    };
    const std::string base_records_effort = config_.records_effort_high ?
        "high" : config_.records_effort;
    auto authorize_repeat = [&](const ToolCall& call, const std::string& outcome,
                                int done, const std::string& deciding_message,
                                int max_tokens, const std::string& effort) -> std::string {
        if (remaining(deadline, 30) < 2) return "";
        const std::string seam = prompt(prompts_, "action", "OPERATOR_SEAM");
        const std::string system = with_operator(
            prompt(prompts_, "action_extra", "REPEAT_AUTHORIZER_SYSTEM"), request.system_prompt, seam);
        const std::string question = format(prompt(prompts_, "action_extra", "REPEAT_QUESTION"),
            {{"message", deciding_message}, {"calls", ledger_text(ledger)},
             {"call", call.name + " " + tool_args_for_prompt(call)}, {"outcome", outcome},
             {"done", std::to_string(done)}});
        json messages = json::array({{{"role", "system"}, {"content", system}},
                                     {{"role", "user"}, {"content", question}}});
        const TimePoint authorization_deadline = std::min(
            deadline, Clock::now() + std::chrono::seconds(30));
        for (int attempt = 0; attempt < 2; ++attempt) {
            try {
                const auto result = call_model(messages, json::array(), max_tokens,
                                               effort, 30, "auto", false,
                                               std::numeric_limits<double>::quiet_NaN(), 0,
                                               authorization_deadline);
                std::smatch word;
                if (std::regex_search(result.content, word, std::regex(R"([A-Za-z]+)"))) {
                    const std::string verdict = lower(word.str());
                    if (verdict == "send") return "SEND";
                    if (verdict == "hold") return "HOLD";
                }
                messages.push_back({{"role", "user"},
                                    {"content", prompt(prompts_, "action_extra", "REPEAT_WORD_REMINDER")}});
            } catch (const ModelError&) { return ""; }
        }
        return "";
    };
    auto execute_call = [&](const ToolCall& call, bool allow_local, const Packet& packet,
                            bool result_suffix, const std::string& deciding_message,
                            int repeat_max_tokens, const std::string& repeat_effort,
                            bool finder_offered) -> std::pair<std::string, bool> {
        if (!call.valid) return {format(prompt(prompts_, "action", "UNREADABLE_ARGS_NOTE"),
                                        {{"name", call.name}}), false};
        if (allow_local && is_memory_read(call.name) && has_tool(request, call.name)) {
            if (lane == "records") {
                const auto unheld = store_.unheld_ids(user_id, call.name, call.args);
                if (!unheld.empty()) {
                    std::string quoted;
                    for (const auto& id : unheld)
                        quoted += (quoted.empty() ? "" : ", ") + json(id).dump();
                    return {"Call not sent: " + call.name + " names " + quoted +
                            ", and no stored conversation or subject of this user has that identifier. "
                            "Identifiers are the pair_id and subject id values printed with the records or "
                            "returned by a search; the mark a record is shown with, such as M4, is not one. "
                            "Send it again with those identifiers, or search by words.", false};
                }
                const int hop = static_cast<int>(observed.size());
                const ToolResult endpoint_result = endpoint.execute(
                    request, call, hop, config_.tool_timeout_seconds, remaining_seconds(deadline));
                if (endpoint_result.observed)
                    observed.push_back({{"name", call.name}, {"args", call.args}, {"hop", hop}});
                const std::string state = endpoint_result.state == DeliveryState::completed ? "completed" :
                                          endpoint_result.state == DeliveryState::delivery_unknown ? "delivery_unknown" :
                                          endpoint_result.state == DeliveryState::delivered_failed ? "delivered_failed" :
                                          endpoint_result.state == DeliveryState::blocked_before_execution ? "blocked_before_execution" : "not_delivered";
                ledger.push_back(call.name + " " + tool_args_for_prompt(call) + " -> " + state + ": " + endpoint_result.output);
                return {memory_tool_content(
                    call.name, store_.local_tool(user_id, call.name, call.args)), false};
            }
            return {memory_tool_content(
                call.name, store_.local_tool(user_id, call.name, call.args)), false};
        }
        if (allow_local && lane == "records" && call.name == "calculate" && !has_tool(request, call.name)) {
            return {calculate(call.args).dump(), false};
        }
        if (allow_local && lane == "records" && finder_offered &&
            call.name == "find_in_records" && !has_tool(request, call.name)) {
            return {find_in_records(packet, call.args).dump(), false};
        }
        if (!has_tool(request, call.name)) {
            return {format(prompt(prompts_, "action", "UNKNOWN_TOOL_NOTE"), {{"name", call.name}}), false};
        }
        const std::string issue = schema_issue(call.args, tool_spec(request, call.name));
        if (!issue.empty()) {
            const std::string note_key = issue.rfind("needs ", 0) == 0 ? "MISSING_ARGS_NOTE" : "BAD_TYPE_NOTE";
            return {format(prompt(prompts_, "action", note_key),
                           {{"name", call.name}, {"missing", issue.rfind("needs ", 0) == 0 ? issue.substr(6) : issue},
                            {"problems", issue}}), false};
        }
        const std::string identity = call.name + call.args.dump();
        auto previous = sent.find(identity);
        if (previous != sent.end() && reads_state(call.name) && read_after[identity] != changes)
            previous = sent.end();
        if (previous != sent.end()) {
            const int done = sent_count[identity];
            const std::string earlier = previous->second == DeliveryState::completed
                                            ? "already ran (its result is above)"
                                            : "was already sent and no result came back (whether it ran is unknown)";
            const std::string verdict = authorize_repeat(
                call, earlier, done, deciding_message, repeat_max_tokens, repeat_effort);
            if (verdict != "SEND") {
                const std::string note = verdict == "HOLD" ?
                    "Not sent: an identical " + call.name +
                    " call, with exactly these arguments, " + earlier +
                    " earlier in this request, and the check made before sending found that the user's message does not ask for this exact call more times than it was already sent, so this one was held and nothing was sent." :
                    "Not sent: an identical " + call.name +
                    " call, with exactly these arguments, " + earlier +
                    " earlier in this request, and the check made before sending could not be completed, so this one was held and nothing was sent. If the user's message asks for this exact call more times than it was already sent, sending it again puts it to that check again.";
                ledger.push_back(call.name + " " + tool_args_for_prompt(call) +
                                 " -> blocked_before_execution");
                return {note, false};
            }
        }
        const int hop = static_cast<int>(observed.size());
        ToolResult result = endpoint.execute(request, call, hop, config_.tool_timeout_seconds,
                                             remaining_seconds(deadline));
        if (result.observed) observed.push_back({{"name", call.name}, {"args", call.args}, {"hop", hop}});
        const std::string state = result.state == DeliveryState::completed ? "completed" :
                                  result.state == DeliveryState::delivery_unknown ? "delivery_unknown" :
                                  result.state == DeliveryState::delivered_failed ? "delivered_failed" :
                                  result.state == DeliveryState::blocked_before_execution ? "blocked_before_execution" : "not_delivered";
        ledger.push_back(call.name + " " + tool_args_for_prompt(call) + " -> " + state + ": " + result.output);
        if (result.state == DeliveryState::completed || result.state == DeliveryState::delivery_unknown) {
            ++sent_count[identity];
            if (reads_state(call.name)) {
                if (result.state == DeliveryState::completed) {
                    sent[identity] = result.state;
                    read_after[identity] = changes;
                }
            } else {
                sent[identity] = result.state;
                ++changes;
            }
        }
        if (result.state == DeliveryState::completed) {
            const std::string content = json_string(call.args, "content");
            if (!content.empty() && call.name == "save_memory") store_.mirror_save(user_id, content);
            if (!content.empty() && call.name == "update_memory")
                store_.mirror_update(user_id, json_string(call.args, "pair_id"), content);
        }
        std::string output = result.output;
        if (result_suffix && result.state == DeliveryState::completed && result.observed)
            output += prompt(prompts_, "action", "TOOL_RESULT_SUFFIX");
        return {output, result.state == DeliveryState::completed && result.observed};
    };

    {
        std::optional<json> short_messages;
        auto short_consult = [&](const json& consult_messages, int max_tokens,
                                 const char* label) -> std::optional<std::string> {
            for (const std::string& effort : {config_.short_effort, std::string("low")}) {
                if (remaining(deadline, config_.llm_timeout_seconds) < 8) break;
                try {
                    const auto answer = call_model(consult_messages, json::array(), max_tokens,
                                                   effort, config_.llm_timeout_seconds);
                    if (!model_strip(answer.content).empty()) return answer.content;
                } catch (const ModelError& error) {
                    std::cerr << label << " failed case=" << request.case_id << ": " << error.what() << '\n';
                    break;
                }
            }
            return std::nullopt;
        };
        if (short_program && remaining(deadline, config_.llm_timeout_seconds) >= 8) {
            std::optional<std::string> ordered;
            if (short_program->needs_order()) {
                const json order_messages = short_program->order_messages();
                auto read_order = [&] {
                    return short_consult(order_messages, config_.order_max_tokens,
                                         "short order");
                };
                ordered = config_.short_order_cache ?
                    order_readings_.get_or_read(text_key(order_messages.dump()), read_order) :
                    read_order();
            }
            if (!short_program->needs_order() || ordered)
                short_messages = short_program->answer_messages(request, ordered,
                                                                 config_.program_full_dates);
        }
        if (!short_messages && short_topic && remaining(deadline, config_.llm_timeout_seconds) >= 8) {
            TopicNotes topic = *short_topic;
            static const std::regex contact(R"(\b(?:e-?mail|address)\b)", std::regex::icase);
            if (std::regex_search(request.user_input, contact)) {
                const auto reading = short_consult(topic_named_messages(request, topic, pairs),
                                                   config_.short_max_tokens, "topic person reading");
                const auto named = reading ? topic_names_from_reading(*reading, pairs) :
                                             std::vector<std::string>{};
                topic = topic_with_cards(topic, pairs, config_.story_max_chars, named);
            }
            std::string draft;
            if (config_.topic_draft) {
                const json latest_messages = topic_latest_messages(request, topic, pairs);
                if (!latest_messages.empty()) {
                    const auto reading = short_consult(latest_messages, config_.short_max_tokens,
                                                       "topic latest passages");
                    if (reading && topic_draft_usable(*reading)) draft = model_strip(*reading);
                }
            }
            short_messages = topic_messages(request, topic, pairs, draft);
        }
        while (true) {
        if (!short_messages) compute_meaning_order();
        std::vector<std::string> recall_pins;
        std::vector<ToolCall> recall_served_calls;
        std::vector<std::string> recall_served_outputs;
        if (lane == "records" && !short_messages) {
            if (std::any_of(request.tools.begin(), request.tools.end(), [](const json& item) {
                    return is_memory_read(json_string(item, "name"));
                })) {
                const std::string system = with_operator(
                    prompt(prompts_, "records", "MEMORY_LANE_SYSTEM") + "\n" +
                    prompt(prompts_, "records", "SUBJECT_DISCIPLINE") + "\n" +
                    prompt(prompts_, "records", "THREAD_READING"),
                    request.system_prompt, prompt(prompts_, "action", "OPERATOR_SEAM"));
                json recall_tools = offered;
                if (!has_tool(request, "calculate")) recall_tools.push_back(calculate_tool_definition());
                json recall_messages = json::array({{{"role", "system"}, {"content", system}},
                    {{"role", "user"}, {"content", format(prompt(prompts_, "records", "RECALL_BRIEF"),
                                                    {{"message", request.user_input}})}}});
                const std::string recall_deciding_message =
                    json_string(recall_messages[1], "content");
                try {
                    const auto recall = call_model(recall_messages, recall_tools,
                        config_.recall_max_tokens, config_.recall_effort,
                        config_.llm_timeout_seconds);
                    Packet empty_packet;
                    for (const auto& call : recall.calls) {
                        if (!call.valid) continue;
                        if (is_memory_read(call.name) && has_tool(request, call.name)) {
                            const bool pin_allowed = call.valid &&
                                store_.unheld_ids(user_id, call.name, call.args).empty();
                            execute_call(call, true, empty_packet, false,
                                         recall_deciding_message, config_.recall_max_tokens,
                                         config_.recall_effort, false);
                            if (pin_allowed)
                                for (const auto& id : store_.memory_hits(user_id, call.name, call.args))
                                    if (std::find(recall_pins.begin(), recall_pins.end(), id) == recall_pins.end())
                                        recall_pins.push_back(id);
                        } else if (call.name == "calculate" || has_tool(request, call.name)) {
                            const auto [output, _] = execute_call(
                                call, true, empty_packet, false, recall_deciding_message,
                                config_.recall_max_tokens, config_.recall_effort, false);
                            recall_served_calls.push_back(call);
                            recall_served_outputs.push_back(output);
                        }
                    }
                } catch (const ModelError& error) {
                    std::cerr << "recall model failed case=" << request.case_id << ": " << error.what() << '\n';
                }
            }
        }

        RecordsPacketOptions records_options;
        records_options.char_budget = config_.packet_char_budget;
        records_options.recall_pins = recall_pins;
        Packet packet;
        if (!short_messages)
            packet = lane == "records" ?
                         build_records_packet(ranking, request.user_input, records_options) :
                         build_packet(ranking, request.user_input, config_.packet_char_budget);
        std::string action_lead;
        if (lane == "action" && config_.action_topic &&
            !has_identifier_focus(request.user_input, ranking.ordered) &&
            own_records_question(request.user_input, request.tools)) {
            auto lead = topic_lead(request.user_input, packet, pairs,
                                   config_.story_min_density, config_.story_max_chars);
            packet = std::move(lead.packet);
            action_lead = std::move(lead.lead);
        }
        SearchPlan search_plan;
        json advisory_messages = json::array();
        json timeline_messages_note = json::array();
        json reading_messages_note = json::array();
        bool search_note_written = false;
        if (lane == "records" && !short_messages) {
            SearchOptions options;
            options.search_record_chars = config_.search_record_chars;
            options.search_long_records = config_.search_long_records;
            options.search_passes = config_.search_passes;
            options.search_temperature = config_.search_temperature;
            options.search_seed = config_.sampling_seed;
            options.finder_order = config_.finder_order;
            const double seconds_left = std::chrono::duration<double>(deadline - Clock::now()).count();
            if (config_.deliberation && records_timeline_ready(
                    request, packet, route.reason == "statement", ranking.names_value,
                    seconds_left, config_.drafts)) {
                try {
                    const auto timeline = call_model(timeline_messages(
                        request, packet.rendered, prompts_, options), json::array(), 16000,
                                                     base_records_effort, config_.llm_timeout_seconds);
                    if (timeline.finish != "length" && timeline.calls.empty() &&
                        !model_strip(timeline.content).empty())
                        timeline_messages_note = timeline_note_message(model_strip(timeline.content));
                } catch (const ModelError& error) {
                    std::cerr << "timeline failed case=" << request.case_id << ": " << error.what() << '\n';
                }
            }
            search_plan = plan_records_search(request, packet, prompts_,
                std::chrono::duration<double>(deadline - Clock::now()).count(), options);
            if (timeline_messages_note.empty() && search_plan.should_run) {
                struct SearchPassOutcome {
                    json kept = json::array();
                    std::string note;
                    int prompt_tokens = 0;
                    int output_tokens = 0;
                };
                const auto pass_started = Clock::now();
                const auto pass_deadline = pass_started + std::chrono::duration_cast<Clock::duration>(
                    std::chrono::duration<double>(search_plan.budget_seconds));
                auto run_search_pass = [&](const SearchPass& pass) -> SearchPassOutcome {
                    SearchPassOutcome outcome;
                    json search_messages = search_plan.messages;
                    for (int turn = 0; turn < 8; ++turn) {
                        const int window = remaining(pass_deadline, config_.llm_timeout_seconds);
                        if (window < 5) break;
                        ModelResult result;
                        try {
                            result = config_.mock_model ?
                                ModelResult{"Mock reply.\nANSWER: mock", {}, "stop", json::object(), 0, 0} :
                                model->complete(search_messages, search_plan.tools, 16000,
                                                base_records_effort,
                                                pass.temperature.value_or(config_.sampling_temperature),
                                                std::to_string(pass.seed.value_or(config_.sampling_seed)),
                                                config_.llm_timeout_seconds, "auto", false,
                                                std::min(remaining_seconds(pass_deadline),
                                                         remaining_seconds(deadline)));
                            outcome.prompt_tokens += result.prompt_tokens;
                            outcome.output_tokens += result.output_tokens;
                        } catch (const ModelError& error) {
                            outcome.prompt_tokens += error.prompt_tokens;
                            outcome.output_tokens += error.output_tokens;
                            break;
                        } catch (const std::exception&) { break; }
                        if (result.calls.empty()) {
                            if (result.finish != "length") outcome.note = model_strip(result.content);
                            break;
                        }
                        const json assistant = assistant_message(result);
                        search_messages.push_back(assistant);
                        outcome.kept.push_back(assistant);
                        for (const auto& call : result.calls) {
                            std::string output;
                            if (!call.valid)
                                output = format(prompt(prompts_, "action", "UNREADABLE_ARGS_NOTE"),
                                                {{"name", call.name}});
                            else if (call.name == "find_in_records")
                                output = find_in_records(packet, call.args).dump();
                            else if (call.name == "calculate")
                                output = calculate(call.args).dump();
                            else
                                output = "Not run: this search pass runs only find_in_records and calculate; "
                                         "the reply after it can call " + call.name + ".";
                            json receipt = {{"role", "tool"}, {"tool_call_id", call.id},
                                            {"content", output}};
                            search_messages.push_back(receipt);
                            outcome.kept.push_back(std::move(receipt));
                        }
                    }
                    return outcome;
                };
                const auto first = run_search_pass(search_plan.passes.front());
                prompt_tokens += first.prompt_tokens;
                output_tokens += first.output_tokens;
                for (const auto& message : first.kept) advisory_messages.push_back(message);
                const double first_took = std::chrono::duration<double>(Clock::now() - pass_started).count();
                std::vector<std::future<SearchPassOutcome>> later;
                std::vector<int> later_numbers;
                if (std::chrono::duration<double>(pass_deadline - Clock::now()).count() >= first_took) {
                    for (std::size_t i = 1; i < search_plan.passes.size(); ++i) {
                        later_numbers.push_back(search_plan.passes[i].which);
                        later.push_back(std::async(std::launch::async, run_search_pass,
                                                   search_plan.passes[i]));
                    }
                }
                std::vector<SearchNote> extra_notes;
                for (std::size_t i = 0; i < later.size(); ++i) {
                    auto next = later[i].get();
                    prompt_tokens += next.prompt_tokens;
                    output_tokens += next.output_tokens;
                    extra_notes.push_back({later_numbers[i], std::move(next.note)});
                }
                const json notes = search_note_messages(first.note, extra_notes);
                search_note_written = !notes.empty();
                for (const auto& message : notes)
                    advisory_messages.push_back(message);
            }
            if (!search_plan.searchable && remaining(deadline, config_.llm_timeout_seconds) >= 20) {
                const Packet closest = closest_records(
                    packet, closest_anchor_holders(ranking, request.user_input));
                if (!closest.records.empty()) {
                    try {
                        const auto reading = call_model(closest_reading_messages(
                            request, closest, packet, prompts_, options), json::array(),
                                                        config_.max_output_tokens,
                                                        base_records_effort,
                                                        config_.llm_timeout_seconds);
                        const std::string note = model_strip(reading.content);
                        if (!note.empty() && reading.finish != "length" && reading.calls.empty())
                            reading_messages_note = closest_reading_note(closest, packet, note);
                    } catch (const ModelError& error) {
                        std::cerr << "reading failed case=" << request.case_id << ": "
                                  << error.what() << '\n';
                    }
                }
            }
        }
        for (const auto& note : reading_messages_note) advisory_messages.push_back(note);
        for (const auto& note : timeline_messages_note) advisory_messages.push_back(note);
        json messages = json::array();
        json active_tools = offered;
        if (short_messages) {
            messages = *short_messages;
            if (!has_tool(request, "calculate")) active_tools.push_back(calculate_tool_definition());
        } else if (lane == "records") {
            std::string system = prompt(prompts_, "records", "MEMORY_LANE_SYSTEM") + "\n" +
                                 prompt(prompts_, "records", "SUBJECT_DISCIPLINE") + "\n" +
                                 prompt(prompts_, "records", "THREAD_READING");
            system = with_operator(system, request.system_prompt,
                                   prompt(prompts_, "action", "OPERATOR_SEAM"));
            messages.push_back({{"role", "system"}, {"content", system}});
            messages.push_back({{"role", "user"}, {"content", packet.rendered}});
            if (!recall_served_calls.empty()) {
                ModelResult receipts;
                receipts.calls = recall_served_calls;
                messages.push_back(assistant_message(receipts));
                for (std::size_t i = 0; i < recall_served_calls.size(); ++i)
                    messages.push_back({{"role", "tool"},
                                        {"tool_call_id", recall_served_calls[i].id},
                                        {"content", recall_served_outputs[i]}});
            }
            if (!has_tool(request, "calculate")) active_tools.push_back(calculate_tool_definition());
            if (search_plan.finder)
                active_tools.push_back(find_tool_definition(config_.finder_order));
            for (const auto& note : advisory_messages) messages.push_back(note);
        } else {
            const std::string system = with_operator(
                prompt(prompts_, "action", "ACTION_LANE_PROMPT"), request.system_prompt,
                prompt(prompts_, "action", "OPERATOR_SEAM"));
            messages.push_back({{"role", "system"}, {"content", system}});
            messages.push_back({{"role", "user"},
                                {"content", (action_lead.empty() ? "" : action_lead + "\n\n") +
                                            compose_action_packet(packet, request.user_input)}});
        }

        const int max_turns = lane == "records" ? config_.records_max_turns : config_.action_max_turns;
        const int case_max_tokens = short_messages ? config_.short_max_tokens :
            (lane == "action" ? config_.action_max_tokens :
             (search_plan.finder ? std::max(config_.max_output_tokens, 16000) :
                                    config_.max_output_tokens));
        std::size_t packet_chars = 0;
        for (const auto& pair : packet.records)
            packet_chars += codepoints(pair.prompt) + codepoints(pair.response) + 64;
        const std::string decide_effort = short_messages ? config_.short_effort :
            (lane == "action" ? config_.action_effort :
             (packet_chars > static_cast<std::size_t>(config_.long_packet_chars) ||
              (search_note_written && search_plan.short_identifier) ?
                 "low" : base_records_effort));
        DeliberationPolicy draft_policy;
        draft_policy.drafts = config_.drafts;
        draft_policy.temperature = config_.draft_temperature;
        draft_policy.seed = config_.sampling_seed;
        bool called = false;
        bool nudged = false;
        bool length_retried = false;
        bool wrapped = false;
        bool closing_asked = false;
        bool deliberated = false;
        bool drafting = false;
        bool followed_up = false;
        bool rewriting = false;
        std::size_t draft_brief_index = 0;
        std::string draft_opening;
        int provider_rejections = 0;
        int turns_left = max_turns;
        while (true) {
            if (turns_left <= 0 || remaining(deadline, config_.llm_timeout_seconds) < 3) {
                if (closing_asked || !model_strip(final_text).empty() ||
                    remaining(deadline, config_.llm_timeout_seconds) < 3) break;
                closing_asked = true;
                turns_left = 1;
                messages.push_back({{"role", "user"},
                                    {"content", prompt(prompts_, lane, "CLOSING_TURN")}});
            }
            --turns_left;
            ModelResult result;
            try {
                result = call_model(messages, active_tools, case_max_tokens,
                                    (length_retried || closing_asked ||
                                     (lane == "action" && wrapped)) ? "low" : decide_effort,
                                    config_.llm_timeout_seconds);
            } catch (const ModelError& error) {
                std::cerr << "model failed case=" << request.case_id << ": " << error.what() << '\n';
                turns_left = 0;
                continue;
            }
            if (result.calls.empty()) {
                if (result.finish == "error" && model_strip(result.content).empty() &&
                    provider_rejections < 2 &&
                    result.provider_error.is_object()) {
                    const std::string detail = json_string(result.provider_error, "message");
                    if (!detail.empty() &&
                        (lower(detail).find("schema") != std::string::npos ||
                         lower(detail).find("validation") != std::string::npos)) {
                        ++provider_rejections;
                        messages.push_back({{"role", "user"},
                            {"content", format(prompt(prompts_, "action", "PROVIDER_SHAPE_NOTE"),
                                                {{"message", detail.substr(0, 400)}})}});
                        continue;
                    }
                }
                if (lane == "records" && !short_messages && config_.deliberation &&
                    !deliberated && (!model_strip(result.content).empty() || result.finish == "length")) {
                    const double seconds_left = std::chrono::duration<double>(deadline - Clock::now()).count();
                    const std::string skip = draft_policy.skip_reason(
                        static_cast<int>(packet.records.size()), seconds_left, turns_left,
                        has_identifier_focus(request.user_input, ranking.ordered),
                        route.reason == "statement", ranking.names_value);
                    deliberated = true;
                    if (skip.empty()) {
                        drafting = true;
                        draft_opening = result.content;
                        if (result.finish == "length") length_retried = true;
                        std::vector<std::string> slots{draft_slot(1, result)};
                        const auto draft_end = Clock::now() + (deadline - Clock::now()) / 2;
                        struct DraftOutcome {
                            int index = 0;
                            std::optional<ModelResult> result;
                            int prompt_tokens = 0;
                            int output_tokens = 0;
                        };
                        std::vector<std::future<DraftOutcome>> drafts;
                        for (int index : draft_policy.indexes()) {
                            drafts.push_back(std::async(std::launch::async, [&, index] {
                                DraftOutcome outcome;
                                outcome.index = index;
                                const int window = remaining(draft_end, config_.llm_timeout_seconds);
                                if (window < 2) return outcome;
                                try {
                                    outcome.result = config_.mock_model ?
                                        ModelResult{"Mock reply.\nANSWER: mock", {}, "stop",
                                                    json::object(), 0, 0} :
                                        model->complete(messages, active_tools, case_max_tokens,
                                            length_retried ? "low" : decide_effort,
                                            draft_policy.temperature,
                                            std::to_string(config_.sampling_seed + index - 1),
                                            config_.llm_timeout_seconds, kDraftToolChoice, true,
                                            std::min(remaining_seconds(draft_end),
                                                     remaining_seconds(deadline)));
                                    outcome.prompt_tokens = outcome.result->prompt_tokens;
                                    outcome.output_tokens = outcome.result->output_tokens;
                                } catch (const ModelError& error) {
                                    outcome.prompt_tokens = error.prompt_tokens;
                                    outcome.output_tokens = error.output_tokens;
                                } catch (const std::exception&) {
                                }
                                return outcome;
                            }));
                        }
                        for (auto& draft : drafts) {
                            const auto alternative = draft.get();
                            prompt_tokens += alternative.prompt_tokens;
                            output_tokens += alternative.output_tokens;
                            slots.push_back(alternative.result ?
                                draft_slot(alternative.index, *alternative.result) :
                                failed_draft_slot(alternative.index));
                        }
                        draft_brief_index = messages.size();
                        messages.push_back({{"role", "user"}, {"content", deliberation_brief(slots)}});
                        continue;
                    }
                }
                if (rewriting) {
                    if (!model_strip(result.content).empty()) final_text = result.content;
                    turns_left = 0;
                    continue;
                }
                if (model_strip(result.content).empty() && result.finish == "length" &&
                    !length_retried && (lane == "action" || decide_effort != "low")) {
                    length_retried = true;
                    continue;
                }
                if (model_strip(result.content).empty() && !nudged) {
                    nudged = true;
                    if (lane == "records") turns_left = std::max(turns_left, 1);
                    messages.push_back({{"role", "user"},
                                        {"content", prompt(prompts_, lane, "EMPTY_REPLY_NUDGE")}});
                    continue;
                }
                if (lane == "action" && model_strip(result.content).empty() &&
                    !observed.empty() && !wrapped) {
                    wrapped = true;
                    turns_left = std::max(turns_left, 1);
                    continue;
                }
                if (lane == "records" && drafting && config_.follow_up && !followed_up &&
                    !model_strip(result.content).empty() && result.finish != "length" &&
                    turns_left > 0 && remaining(deadline, 30) >= 25) {
                    followed_up = true;
                    json follow_messages = messages;
                    if (draft_brief_index < follow_messages.size() &&
                        follow_messages[draft_brief_index].is_object() &&
                        json_string(follow_messages[draft_brief_index], "content").rfind(
                            "Before you reply, here are ", 0) == 0)
                        follow_messages.erase(follow_messages.begin() + draft_brief_index);
                    follow_messages.push_back({{"role", "assistant"}, {"content", result.content}});
                    follow_messages.push_back({{"role", "user"},
                        {"content", prompt(prompts_, "records", "FOLLOW_UP_BRIEF")}});
                    std::string question;
                    const TimePoint follow_deadline = std::min(
                        deadline, Clock::now() + std::chrono::seconds(30));
                    std::optional<ModelResult> last_advice;
                    for (int attempt = 0; attempt < (config_.follow_up_retry ? 2 : 1); ++attempt) {
                        try {
                            last_advice = call_model(follow_messages, json::array(), 4000,
                                length_retried ? "low" : decide_effort, 30, "auto", false,
                                std::numeric_limits<double>::quiet_NaN(), 0, follow_deadline);
                            if (!retry_empty_follow_up(*last_advice)) break;
                        } catch (const ModelError&) { break; }
                    }
                    if (last_advice && last_advice->finish != "length" &&
                        last_advice->calls.empty())
                        question = model_strip(last_advice->content);
                    const std::string question_prefix = question.empty() ? "" :
                                                        question.substr(0, question.size() - 1);
                    const bool one_question = !question.empty() && question.back() == '?' &&
                                              question.find('\n') == std::string::npos &&
                                              !answer_slot(question) &&
                                              !std::regex_search(question_prefix,
                                                                 std::regex(R"([.!?;]\s)"));
                    if (one_question) {
                        final_text = result.content;
                        rewriting = true;
                        messages.push_back({{"role", "assistant"}, {"content", result.content}});
                        messages.push_back({{"role", "user"},
                            {"content", format(prompt(prompts_, "records", "FOLLOW_UP_NOTE"),
                                               {{"question", question}})}});
                        continue;
                    }
                }
                if (!model_strip(result.content).empty()) final_text = result.content;
                turns_left = 0;
                continue;
            }
            messages.push_back(assistant_message(result));
            if (!called && lane == "action") {
                called = true;
                messages[0]["content"] = with_operator(
                    prompt(prompts_, "action", "CALLED_LANE_PROMPT"), request.system_prompt,
                    prompt(prompts_, "action", "OPERATOR_SEAM"));
            }
            bool read_worthy = false;
            for (const auto& call : result.calls) {
                auto [output, completed] = execute_call(
                    call, true, packet, lane == "action" && config_.result_suffix,
                    json_string(messages[1], "content"), case_max_tokens,
                    lane == "action" ? config_.action_effort : base_records_effort,
                    lane == "records" && !short_messages && search_plan.finder);
                std::string raw_output = output;
                if (lane == "action") {
                    const std::string suffix = prompt(prompts_, "action", "TOOL_RESULT_SUFFIX");
                    if (!suffix.empty() && raw_output.ends_with(suffix))
                        raw_output.resize(raw_output.size() - suffix.size());
                }
                if (completed && std::regex_search(raw_output, std::regex(R"(\S+\s+\S+)")))
                    read_worthy = true;
                messages.push_back({{"role", "tool"}, {"tool_call_id", call.id}, {"content", output}});
            }
            if (lane == "action" && read_worthy && turns_left > 0 && config_.result_read &&
                route.reason != "imperative-setter" &&
                remaining(deadline, 30) >= 10) {
                try {
                    const std::string system = with_operator(
                        prompt(prompts_, "action_extra", "RESULT_READ_SYSTEM"),
                        request.system_prompt, prompt(prompts_, "action", "OPERATOR_SEAM"));
                    const std::string question = format(
                        prompt(prompts_, "action_extra", "RESULT_READ_QUESTION"),
                        {{"message", request.user_input}, {"calls", ledger_text(ledger)}});
                    const json read_messages = json::array({{{"role", "system"}, {"content", system}},
                        {{"role", "user"}, {"content", question}}});
                    const TimePoint read_deadline = std::min(
                        deadline, Clock::now() + std::chrono::seconds(30));
                    const auto reading = call_model(read_messages, json::array(), case_max_tokens,
                                                    config_.action_effort, 30, "auto", false,
                                                    std::numeric_limits<double>::quiet_NaN(), 0,
                                                    read_deadline);
                    if (!model_strip(reading.content).empty() && reading.finish != "length") {
                        const std::string note = format(prompt(prompts_, "action", "RESULT_READ_NOTE"),
                                                        {{"reading", reading.content.substr(0, 2000)}});
                        messages[0]["content"] = with_operator(
                            prompt(prompts_, "action", "CALLED_LANE_PROMPT") + "\n\n" + note,
                            request.system_prompt, prompt(prompts_, "action", "OPERATOR_SEAM"));
                    }
                } catch (const ModelError&) {
                }
            }
            if ((lane == "action" || !drafting) && !result.content.empty())
                final_text = result.content;
            if (lane == "action" && turns_left == 0 && model_strip(final_text).empty() &&
                !observed.empty() && !wrapped) {
                wrapped = true;
                turns_left = 1;
            }
        }
        if (final_text.empty() && drafting) final_text = draft_opening;
        if (short_messages && model_strip(final_text).empty()) {
            // ShortPath/TopicPath only count as handled when their deciding
            // reply has text. Keep this case's tool ledger, observed calls and
            // token tally, then run the ordinary records path with the same
            // deadline and model client.
            short_messages.reset();
            continue;
        }
        break;
        }
    }
    const auto [stripped, answer] = parse_slot(final_text);
    json response = {{"final_text", plain_type(stripped)}, {"tool_calls", observed},
                     {"prompt_tokens", prompt_tokens}, {"output_tokens", output_tokens},
                     {"latency_ms", std::chrono::duration_cast<std::chrono::milliseconds>(
                                        Clock::now() - started).count()}};
    if (answer) response["answer"] = plain_type(*answer);
    return response;
}

}  // namespace ditto
