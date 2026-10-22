#pragma once

#include <optional>
#include <stdexcept>
#include <string>

#include "types.hpp"

namespace ditto {

enum class DeliveryState {
    completed,
    delivery_unknown,
    delivered_failed,
    not_delivered,
    blocked_before_execution,
};

struct ToolResult {
    std::string output;
    DeliveryState state = DeliveryState::not_delivered;
    bool observed = false;
    long http_status = 0;
};

class ModelError : public std::runtime_error {
public:
    ModelError(std::string message, int prompt_tokens = 0, int output_tokens = 0);

    int prompt_tokens;
    int output_tokens;
};

class ModelClient {
public:
    // `openrouter` applies only to direct OpenRouter traffic. Per-case relay
    // inference URLs use the ordinary OpenAI-compatible wire contract.
    ModelClient(std::string base_url, std::string model, std::string token,
                bool openrouter = false, int max_attempts = 2,
                std::optional<double> top_p = std::nullopt);

    // timeout_seconds caps each HTTP attempt. case_remaining_seconds is the
    // remaining case budget (including retries); omission retains the old
    // combined deadline for callers that have not supplied the case budget yet.
    // `once` is used by advisory draft calls, which must not be retried.
    ModelResult complete(const json& messages, const json& tools, int max_tokens,
                         const std::string& effort, double temperature,
                         const std::string& seed, int timeout_seconds,
                         const std::string& tool_choice = "auto", bool once = false,
                         std::optional<double> case_remaining_seconds = std::nullopt) const;

private:
    std::string base_url_;
    std::string model_;
    std::string token_;
    bool openrouter_ = false;
    int max_attempts_ = 2;
    std::optional<double> top_p_;
};

class ToolEndpoint {
public:
    // timeout_seconds caps each HTTP trip, including a 429 retry. The optional
    // case budget is separate so the second trip can receive its own timeout.
    ToolResult execute(const RunRequest& request, const ToolCall& call, int hop,
                       int timeout_seconds,
                       std::optional<double> case_remaining_seconds = std::nullopt) const;
};

}  // namespace ditto
