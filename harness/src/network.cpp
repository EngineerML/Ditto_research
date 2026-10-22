#include "network.hpp"

#include <curl/curl.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <limits>
#include <memory>
#include <mutex>
#include <optional>
#include <regex>
#include <sstream>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>

namespace ditto {
namespace {

using Clock = std::chrono::steady_clock;
using OrderedJson = nlohmann::ordered_json;

constexpr int kCapacityWaits = 30;
constexpr int kOutputMaxChars = 6000;
constexpr int kMinToolSeconds = 2;

struct HttpResponse {
    CURLcode code = CURLE_OK;
    long status = 0;
    bool reached_request_stage = false;
    bool retry_after_present = false;
    std::string body;
    std::string retry_after;
    std::string error;
};

void ensure_curl() {
    static std::once_flag once;
    static CURLcode result = CURLE_OK;
    std::call_once(once, [] { result = curl_global_init(CURL_GLOBAL_DEFAULT); });
    if (result != CURLE_OK) throw std::runtime_error("curl_global_init failed");
}

std::string trim(std::string value) {
    auto not_space = [](unsigned char c) { return std::isspace(c) == 0; };
    value.erase(value.begin(), std::find_if(value.begin(), value.end(), not_space));
    value.erase(std::find_if(value.rbegin(), value.rend(), not_space).base(), value.end());
    return value;
}

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

size_t write_body(char* ptr, size_t size, size_t count, void* context) {
    const size_t bytes = size * count;
    static_cast<std::string*>(context)->append(ptr, bytes);
    return bytes;
}

size_t read_header(char* ptr, size_t size, size_t count, void* context) {
    const size_t bytes = size * count;
    const std::string_view line(ptr, bytes);
    const auto colon = line.find(':');
    if (colon != std::string_view::npos && lower(std::string(line.substr(0, colon))) == "retry-after") {
        auto* response = static_cast<HttpResponse*>(context);
        response->retry_after_present = true;
        response->retry_after = trim(std::string(line.substr(colon + 1)));
    }
    return bytes;
}

HttpResponse post_json(const std::string& url, const std::string& body,
                       const std::vector<std::string>& headers, int timeout_ms) {
    ensure_curl();
    HttpResponse response;
    std::unique_ptr<CURL, decltype(&curl_easy_cleanup)> handle(curl_easy_init(), curl_easy_cleanup);
    if (!handle) throw std::runtime_error("curl_easy_init failed");
    curl_slist* raw_headers = nullptr;
    for (const auto& header : headers) raw_headers = curl_slist_append(raw_headers, header.c_str());
    std::unique_ptr<curl_slist, decltype(&curl_slist_free_all)> header_list(raw_headers,
                                                                            curl_slist_free_all);
    char error_buffer[CURL_ERROR_SIZE] = {};
    curl_easy_setopt(handle.get(), CURLOPT_URL, url.c_str());
    curl_easy_setopt(handle.get(), CURLOPT_HTTPHEADER, header_list.get());
    curl_easy_setopt(handle.get(), CURLOPT_POST, 1L);
    curl_easy_setopt(handle.get(), CURLOPT_POSTFIELDS, body.data());
    curl_easy_setopt(handle.get(), CURLOPT_POSTFIELDSIZE_LARGE,
                     static_cast<curl_off_t>(body.size()));
    curl_easy_setopt(handle.get(), CURLOPT_TIMEOUT_MS, static_cast<long>(std::max(1, timeout_ms)));
    curl_easy_setopt(handle.get(), CURLOPT_CONNECTTIMEOUT_MS,
                     static_cast<long>(std::min(10000, std::max(1, timeout_ms))));
    curl_easy_setopt(handle.get(), CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(handle.get(), CURLOPT_FOLLOWLOCATION, 0L);
    curl_easy_setopt(handle.get(), CURLOPT_ACCEPT_ENCODING, "");
    curl_easy_setopt(handle.get(), CURLOPT_WRITEFUNCTION, write_body);
    curl_easy_setopt(handle.get(), CURLOPT_WRITEDATA, &response.body);
    curl_easy_setopt(handle.get(), CURLOPT_HEADERFUNCTION, read_header);
    curl_easy_setopt(handle.get(), CURLOPT_HEADERDATA, &response);
    curl_easy_setopt(handle.get(), CURLOPT_ERRORBUFFER, error_buffer);
    curl_easy_setopt(handle.get(), CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(handle.get(), CURLOPT_SSL_VERIFYHOST, 2L);
    // libcurl's proxy and NO_PROXY handling is left enabled. Honor explicit
    // container CA paths while retaining the system trust store by default.
    const char* ca = std::getenv("CURL_CA_BUNDLE");
    if (!ca || !*ca) ca = std::getenv("SSL_CERT_FILE");
    if (ca && *ca) curl_easy_setopt(handle.get(), CURLOPT_CAINFO, ca);
    response.code = curl_easy_perform(handle.get());
    if (response.code != CURLE_OK) {
        response.error = error_buffer[0] ? error_buffer : curl_easy_strerror(response.code);
    }
    curl_easy_getinfo(handle.get(), CURLINFO_RESPONSE_CODE, &response.status);
    curl_off_t pretransfer_us = 0;
    curl_off_t uploaded_bytes = 0;
    curl_easy_getinfo(handle.get(), CURLINFO_PRETRANSFER_TIME_T, &pretransfer_us);
    curl_easy_getinfo(handle.get(), CURLINFO_SIZE_UPLOAD_T, &uploaded_bytes);
    response.reached_request_stage = pretransfer_us > 0 || uploaded_bytes > 0;
    return response;
}

int seconds_left(Clock::time_point deadline) {
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - Clock::now()).count();
    return ms <= 0 ? 0 : static_cast<int>((ms + 999) / 1000);
}

int milliseconds_left(Clock::time_point deadline) {
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - Clock::now()).count();
    return ms <= 0 ? 0 : static_cast<int>(std::min<std::int64_t>(ms, std::numeric_limits<int>::max()));
}

double precise_seconds_left(Clock::time_point deadline) {
    return std::chrono::duration<double>(deadline - Clock::now()).count();
}

Clock::time_point case_deadline(int per_attempt_seconds,
                                std::optional<double> case_remaining_seconds) {
    const double remaining = case_remaining_seconds.value_or(per_attempt_seconds);
    if (!std::isfinite(remaining))
        throw std::invalid_argument("invalid case deadline");
    return Clock::now() + std::chrono::duration_cast<Clock::duration>(
                              std::chrono::duration<double>(std::max(0.0, remaining)));
}

int attempt_timeout_ms(int per_attempt_seconds, Clock::time_point deadline) {
    const auto cap = static_cast<std::int64_t>(per_attempt_seconds) * 1000;
    return static_cast<int>(std::min<std::int64_t>(cap, milliseconds_left(deadline)));
}

void pause_for(double seconds, Clock::time_point deadline) {
    const auto available = std::chrono::duration<double>(deadline - Clock::now()).count();
    if (available <= 0) return;
    std::this_thread::sleep_for(std::chrono::duration<double>(std::min(seconds, available)));
}

double retry_after_seconds(const std::string& header) {
    try {
        size_t consumed = 0;
        const double value = std::stod(header, &consumed);
        if (consumed == header.size() && std::isfinite(value)) return std::clamp(value, 0.0, 5.0);
    } catch (const std::exception&) {
    }
    return 1.0;
}

int whole_number(const json& value) {
    try {
        long long n = 0;
        if (value.is_number_integer()) n = value.get<long long>();
        else if (value.is_number_float()) {
            const double number = value.get<double>();
            if (!std::isfinite(number)) return 0;
            if (number >= std::numeric_limits<int>::max()) return std::numeric_limits<int>::max();
            if (number <= 0) return 0;
            n = static_cast<long long>(number);
        } else if (value.is_string()) {
            const std::string token = trim(value.get<std::string>());
            size_t used = 0;
            n = std::stoll(token, &used);
            if (used != token.size()) return 0;
        }
        else if (value.is_boolean()) n = value.get<bool>() ? 1 : 0;
        return static_cast<int>(std::clamp<long long>(n, 0, std::numeric_limits<int>::max()));
    } catch (const std::exception&) {
        return 0;
    }
}

std::pair<int, int> usage_of(const json& body) {
    if (!body.is_object() || !body.contains("usage") || !body["usage"].is_object()) return {0, 0};
    const auto& usage = body["usage"];
    return {whole_number(usage.value("prompt_tokens", json())),
            whole_number(usage.value("completion_tokens", json()))};
}

bool provider_rejected(const json& error) {
    const std::string message = lower(json_string(error, "message"));
    for (const char* marker : {"tool call validation failed", "schema", "tool choice is none",
                               "failed to parse tool call arguments"}) {
        if (message.find(marker) != std::string::npos) return true;
    }
    return false;
}

ModelResult parse_completion(const json& body) {
    if (!body.is_object()) throw std::runtime_error("completion body is not a JSON object");
    const auto [prompt, output] = usage_of(body);
    ModelResult result;
    result.prompt_tokens = prompt;
    result.output_tokens = output;
    if (!body.contains("choices") || !body["choices"].is_array() || body["choices"].empty()) {
        if (body.contains("error") && body["error"].is_object() &&
            provider_rejected(body["error"])) {
            result.finish = "error";
            result.provider_error = body["error"];
            return result;
        }
        throw std::runtime_error("no choices in completion");
    }
    const auto& choice = body["choices"][0];
    if (!choice.is_object()) throw std::runtime_error("choice is not a JSON object");
    json message = choice.value("message", json::object());
    if (message.is_null()) message = json::object();
    if (!message.is_object()) throw std::runtime_error("message is not a JSON object");
    const json content = message.value("content", json());
    if (content.is_string()) result.content = content.get<std::string>();
    else if (content.is_array()) {
        for (const auto& part : content) {
            if (part.is_object()) result.content += json_string(part, "text");
        }
    }
    result.finish = json_string(choice, "finish_reason");
    if (choice.contains("error") && choice["error"].is_object()) {
        result.provider_error = choice["error"];
    }
    const json calls = message.value("tool_calls", json::array());
    if (!calls.is_array()) return result;
    for (size_t index = 0; index < calls.size(); ++index) {
        const auto& item = calls[index];
        if (!item.is_object()) continue;
        const json function = item.value("function", json::object());
        if (!function.is_object()) continue;
        ToolCall call;
        call.name = json_string(function, "name");
        if (call.name.empty()) continue;
        call.id = json_string(item, "id", "call_" + std::to_string(index));
        if (call.id.empty()) call.id = "call_" + std::to_string(index);
        const json arguments = function.value("arguments", json());
        if (arguments.is_object()) {
            call.args = arguments;
        } else if (arguments.is_string()) {
            call.raw_args = arguments.get<std::string>();
            const std::string stripped = trim(call.raw_args);
            if (stripped.empty() || stripped == "null") {
                call.args = json::object();
            } else {
                const json parsed = json::parse(call.raw_args, nullptr, false);
                call.valid = parsed.is_object();
                call.args = call.valid ? parsed : json::object();
            }
        } else if (!arguments.is_null()) {
            call.raw_args = arguments.dump();
            call.valid = false;
        }
        result.calls.push_back(std::move(call));
    }
    return result;
}

std::string brief(const std::string& text) {
    return text.substr(0, std::min<size_t>(text.size(), 300));
}

std::string python_quoted(const std::string& value) {
    const char quote = value.find('\'') != std::string::npos && value.find('"') == std::string::npos
                           ? '"' : '\'';
    std::string out(1, quote);
    const char* hex = "0123456789abcdef";
    for (unsigned char c : value) {
        if (c == '\\' || c == static_cast<unsigned char>(quote)) {
            out.push_back('\\');
            out.push_back(static_cast<char>(c));
        } else if (c == '\n') out += "\\n";
        else if (c == '\r') out += "\\r";
        else if (c == '\t') out += "\\t";
        else if (c < 0x20 || c == 0x7f) {
            out += "\\x";
            out.push_back(hex[c >> 4]);
            out.push_back(hex[c & 15]);
        } else out.push_back(static_cast<char>(c));
    }
    out.push_back(quote);
    return out;
}

std::string python_repr(const OrderedJson& value) {
    if (value.is_null()) return "None";
    if (value.is_boolean()) return value.get<bool>() ? "True" : "False";
    if (value.is_string()) return python_quoted(value.get<std::string>());
    if (value.is_number()) return value.dump();
    if (value.is_array()) {
        std::string out = "[";
        for (size_t i = 0; i < value.size(); ++i) {
            if (i) out += ", ";
            out += python_repr(value[i]);
        }
        return out + "]";
    }
    if (value.is_object()) {
        std::string out = "{";
        bool first = true;
        for (auto it = value.begin(); it != value.end(); ++it) {
            if (!first) out += ", ";
            first = false;
            out += python_quoted(it.key()) + ": " + python_repr(it.value());
        }
        return out + "}";
    }
    return value.dump();
}

std::string python_str(const OrderedJson& value) {
    return value.is_string() ? value.get<std::string>() : python_repr(value);
}

bool python_truthy(const OrderedJson& value) {
    if (value.is_null()) return false;
    if (value.is_boolean()) return value.get<bool>();
    if (value.is_string()) return !value.get<std::string>().empty();
    if (value.is_array() || value.is_object()) return !value.empty();
    if (value.is_number()) return value.get<double>() != 0.0;
    return false;
}

size_t utf8_prefix(const std::string& value, size_t max_chars) {
    size_t chars = 0;
    size_t byte = 0;
    while (byte < value.size() && chars < max_chars) {
        const unsigned char c = static_cast<unsigned char>(value[byte]);
        const size_t width = c < 0x80 ? 1 : c < 0xe0 ? 2 : c < 0xf0 ? 3 : 4;
        byte += std::min(width, value.size() - byte);
        ++chars;
    }
    return byte;
}

bool transient_error(const std::string& text) {
    static const std::regex pattern("transient|temporar|try again|\\bretry\\b|timed? ?out|\\b50[234]\\b",
                                    std::regex::icase);
    return std::regex_search(text, pattern);
}

bool certainly_unsent(const HttpResponse& response) {
    const CURLcode code = response.code;
    if (code == CURLE_COULDNT_CONNECT || code == CURLE_COULDNT_RESOLVE_HOST ||
        code == CURLE_COULDNT_RESOLVE_PROXY || code == CURLE_UNSUPPORTED_PROTOCOL ||
        code == CURLE_URL_MALFORMAT || code == CURLE_SSL_CONNECT_ERROR ||
        code == CURLE_PEER_FAILED_VERIFICATION || code == CURLE_SSL_CACERT_BADFILE)
        return true;
    // libcurl reports both connect and read timeouts as CURLE_OPERATION_TIMEDOUT.
    // A timeout before pretransfer cannot have delivered this POST; after that
    // point it may have run, so preserve the uncertainty receipt.
    return code == CURLE_OPERATION_TIMEDOUT && !response.reached_request_stage;
}

std::string tool_body(const RunRequest& request, const ToolCall& call, int hop) {
    const json args = call.args.is_object() ? call.args : json::object();
    const json raw = json::parse(call.raw_args, nullptr, false);
    const std::string arguments = call.valid && raw.is_object() ? call.raw_args : args.dump();
    std::string body = "{\"case_id\":" + json(request.case_id).dump();
    if (!request.user_id.empty()) body += ",\"user_id\":" + json(request.user_id).dump();
    body += ",\"name\":" + json(call.name).dump();
    body += ",\"hop\":" + std::to_string(hop);
    body += ",\"args\":" + arguments + "}";
    return body;
}

}  // namespace

ModelError::ModelError(std::string message, int prompt, int output)
    : std::runtime_error(std::move(message)), prompt_tokens(prompt), output_tokens(output) {}

ModelClient::ModelClient(std::string base_url, std::string model, std::string token,
                         bool openrouter, int max_attempts, std::optional<double> top_p)
    : base_url_(std::move(base_url)), model_(std::move(model)), token_(std::move(token)),
      openrouter_(openrouter), max_attempts_(std::max(1, max_attempts)), top_p_(top_p) {
    while (!base_url_.empty() && base_url_.back() == '/') base_url_.pop_back();
    if (base_url_.empty()) throw std::invalid_argument("model base URL is empty");
    if (top_p_ && !std::isfinite(*top_p_))
        throw std::invalid_argument("model top_p must be finite");
}

ModelResult ModelClient::complete(const json& messages, const json& tools, int max_tokens,
                                  const std::string& effort, double temperature,
                                  const std::string& seed, int timeout_seconds,
                                  const std::string& tool_choice, bool once,
                                  std::optional<double> case_remaining_seconds) const {
    if (timeout_seconds <= 0) throw ModelError("model timeout is not positive");
    const auto deadline = case_deadline(timeout_seconds, case_remaining_seconds);
    json payload = {{"model", model_}, {"messages", messages}, {"temperature", temperature}};
    if (top_p_) payload["top_p"] = *top_p_;
    if (!seed.empty()) {
        try {
            size_t used = 0;
            const long long parsed = std::stoll(seed, &used);
            if (used == seed.size()) payload["seed"] = parsed;
        } catch (const std::exception&) {
        }
    }
    if (effort == "low" || effort == "medium" || effort == "high") {
        if (openrouter_) payload["reasoning"] = {{"effort", effort}, {"exclude", true}};
        else payload["reasoning_effort"] = effort;
    }
    if (openrouter_) {
        payload["provider"] = {{"sort", "throughput"}, {"ignore", json::array({"coreweave"})},
                               {"allow_fallbacks", false}, {"data_collection", "deny"},
                               {"zdr", true}};
    }
    if (tools.is_array() && !tools.empty()) {
        payload["tools"] = tools;
        payload["tool_choice"] = tool_choice.empty() ? "auto" : tool_choice;
    }
    if (max_tokens > 0) payload["max_tokens"] = max_tokens;
    int spent_prompt = 0;
    int spent_output = 0;
    int attempts = 0;
    int quick_failures = 0;
    int capacity_waits = 0;
    double slept = 0;
    std::string last_error = "deadline elapsed";
    const std::string url = base_url_ + "/chat/completions";
    std::vector<std::string> headers = {"Content-Type: application/json",
                                        "Authorization: Bearer " + token_};
    if (openrouter_) {
        headers.emplace_back("HTTP-Referer: https://heyditto.ai");
        headers.emplace_back("X-Title: Ditto");
    }
    while (attempts < max_attempts_ && seconds_left(deadline) > 1) {
        const auto started = Clock::now();
        const HttpResponse response = post_json(url, payload.dump(), headers,
                                                attempt_timeout_ms(timeout_seconds, deadline));
        const bool quick = std::chrono::duration<double>(Clock::now() - started).count() < 5.0;
        if (response.code != CURLE_OK) {
            if (response.code == CURLE_OPERATION_TIMEDOUT || !quick) ++attempts;
            else ++quick_failures;
            last_error = "model transport error: " + response.error;
            if (response.code == CURLE_OPERATION_TIMEDOUT && payload.contains("max_tokens")) {
                const int reduced = std::max(1200,
                    static_cast<int>(payload["max_tokens"].get<int>() * 0.4));
                payload["max_tokens"] = reduced;
            }
        } else {
            const json body = json::parse(response.body, nullptr, false);
            const auto [used_prompt, used_output] = usage_of(body);
            if (response.status == 200) {
                try {
                    ModelResult result = parse_completion(body);
                    result.prompt_tokens += spent_prompt;
                    result.output_tokens += spent_output;
                    return result;
                } catch (const std::exception& error) {
                    spent_prompt += used_prompt;
                    spent_output += used_output;
                    ++attempts;
                    last_error = std::string("malformed model completion: ") + error.what();
                }
            } else {
                spent_prompt += used_prompt;
                spent_output += used_output;
                const bool capacity = response.status == 429 ||
                    (response.status == 503 && response.retry_after_present);
                last_error = "model HTTP " + std::to_string(response.status) + ": " + brief(response.body);
                if (capacity && !once && capacity_waits < kCapacityWaits) {
                    ++capacity_waits;
                    pause_for(std::min(retry_after_seconds(response.retry_after),
                                       std::max(0.0, precise_seconds_left(deadline) - 1.0)), deadline);
                    continue;
                }
                const bool retryable = response.status == 408 || response.status == 409 ||
                    response.status == 425 || response.status == 429 || response.status >= 500;
                if (!retryable) throw ModelError(last_error, spent_prompt, spent_output);
                if (quick) ++quick_failures;
                else ++attempts;
            }
        }
        if (once || attempts >= max_attempts_) break;
        const double remaining = std::chrono::duration<double>(deadline - Clock::now()).count() - 1.0;
        const double backoff = std::min({4.0, 0.5 * std::pow(2.0,
            static_cast<double>(std::min(12, attempts + quick_failures))), std::max(0.0, remaining)});
        if (slept + backoff > 20.0) break;
        slept += backoff;
        pause_for(backoff, deadline);
    }
    throw ModelError("model exhausted attempts: " + last_error, spent_prompt, spent_output);
}

ToolResult ToolEndpoint::execute(const RunRequest& request, const ToolCall& call,
                                 int hop, int timeout_seconds,
                                 std::optional<double> case_remaining_seconds) const {
    const std::string endpoint = trim(request.tool_endpoint);
    if (endpoint.empty()) {
        return {"Tool " + call.name + " is unavailable in this environment.",
                DeliveryState::not_delivered, false, 0};
    }
    if (timeout_seconds < kMinToolSeconds) {
        return {"Tool error: " + call.name +
                    " was not sent because this request's time budget is spent, so it did not run.",
                DeliveryState::blocked_before_execution, false, 0};
    }
    const auto deadline = case_deadline(timeout_seconds, case_remaining_seconds);
    const std::string body = tool_body(request, call, hop);
    const std::vector<std::string> headers = {"Content-Type: application/json"};
    std::optional<HttpResponse> response;
    for (int round_trip = 0; round_trip < 2; ++round_trip) {
        const double window = std::min(static_cast<double>(timeout_seconds),
                                       precise_seconds_left(deadline));
        if (window < kMinToolSeconds) {
            if (!response) {
                return {"Tool error: " + call.name +
                            " was not sent because this request's time budget is spent, so it did not run.",
                        DeliveryState::blocked_before_execution, false, 0};
            }
            break;
        }
        response = post_json(endpoint, body, headers,
                             attempt_timeout_ms(timeout_seconds, deadline));
        if (response->code != CURLE_OK) {
            if (certainly_unsent(*response)) {
                return {"Tool " + call.name + " failed: endpoint unreachable.",
                        DeliveryState::not_delivered, false, 0};
            }
            return {"Tool error: " + call.name +
                        " was sent; no result came back, so whether it ran is unknown.",
                    DeliveryState::delivery_unknown, true, 0};
        }
        if (response->status == 429 && round_trip == 0) {
            pause_for(std::min(1.0, std::max(0.0,
                std::min(static_cast<double>(timeout_seconds), precise_seconds_left(deadline)))),
                deadline);
            continue;
        }
        break;
    }
    if (!response) throw std::runtime_error("tool response was not initialized");
    if (response->status >= 400 && response->status < 500) {
        return {"Tool error: " + call.name + " was refused with status " +
                    std::to_string(response->status) + " and did not run.",
                DeliveryState::delivered_failed, false, response->status};
    }
    if (response->status != 200) {
        return {"Tool error: " + call.name + " was sent and the endpoint answered " +
                    std::to_string(response->status) +
                    " with no result, so whether it ran is unknown.",
                DeliveryState::delivery_unknown, true, response->status};
    }
    const OrderedJson payload = OrderedJson::parse(response->body, nullptr, false);
    if (!payload.is_object()) return {"", DeliveryState::completed, true, 200};
    const OrderedJson error = payload.value("error", OrderedJson());
    if (python_truthy(error)) {
        std::string text = "Tool error: " + python_str(error);
        if ((call.name.rfind("list_", 0) == 0 || call.name.rfind("search_", 0) == 0 ||
             call.name.rfind("discover_", 0) == 0 || call.name.rfind("read_", 0) == 0 ||
             call.name.rfind("get_", 0) == 0 || call.name.rfind("fetch_", 0) == 0 ||
             call.name.rfind("find_", 0) == 0 || call.name.rfind("lookup_", 0) == 0 ||
             call.name.find("_search") != std::string::npos) && transient_error(text)) {
            text += " This failure is transient: issue the same call once more, unchanged.";
        }
        return {text, DeliveryState::delivered_failed, true, 200};
    }
    const OrderedJson result = payload.value("result", OrderedJson());
    std::string output = result.is_null() ? "" : python_str(result);
    const size_t prefix = utf8_prefix(output, kOutputMaxChars);
    if (prefix < output.size()) output = output.substr(0, prefix) + " …[truncated]";
    return {std::move(output), DeliveryState::completed, true, 200};
}

}  // namespace ditto
