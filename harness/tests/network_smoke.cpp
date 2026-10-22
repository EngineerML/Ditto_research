#include "network.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <chrono>
#include <cctype>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace {

struct Reply {
    int status;
    std::string body;
    int delay_ms = 0;
    bool silent = false;
};

struct Capture {
    std::string path;
    std::string headers;
    std::string body;
};

void require(bool test, const std::string& message) {
    if (!test) throw std::runtime_error(message);
}

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return value;
}

void send_all(int fd, const std::string& bytes) {
    std::size_t offset = 0;
    while (offset < bytes.size()) {
        const auto sent = send(fd, bytes.data() + offset, bytes.size() - offset, MSG_NOSIGNAL);
        if (sent <= 0) return;  // A timed-out client can close before the scripted reply.
        offset += static_cast<std::size_t>(sent);
    }
}

class Server {
public:
    explicit Server(std::vector<Reply> replies) : replies_(std::move(replies)) {
        fd_ = socket(AF_INET, SOCK_STREAM, 0);
        require(fd_ >= 0, "socket failed");
        const int yes = 1;
        setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        address.sin_port = 0;
        require(bind(fd_, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0,
                "bind failed");
        require(listen(fd_, 4) == 0, "listen failed");
        socklen_t address_size = sizeof(address);
        require(getsockname(fd_, reinterpret_cast<sockaddr*>(&address), &address_size) == 0,
                "getsockname failed");
        port_ = ntohs(address.sin_port);
        worker_ = std::thread([this] { serve(); });
    }

    ~Server() {
        if (fd_ >= 0) {
            shutdown(fd_, SHUT_RDWR);
            close(fd_);
            fd_ = -1;
        }
        if (worker_.joinable()) worker_.join();
    }

    std::string url() const { return "http://127.0.0.1:" + std::to_string(port_); }

    std::vector<Capture> captures() {
        if (worker_.joinable()) worker_.join();
        std::lock_guard lock(mutex_);
        return captures_;
    }

private:
    void serve() {
        for (const auto& reply : replies_) {
            pollfd ready{fd_, POLLIN, 0};
            if (poll(&ready, 1, 5000) <= 0 || !(ready.revents & POLLIN)) return;
            const int client = accept(fd_, nullptr, nullptr);
            if (client < 0) return;
            if (reply.silent) {
                std::this_thread::sleep_for(std::chrono::milliseconds(reply.delay_ms));
                close(client);
                continue;
            }
            timeval recv_timeout{4, 0};
            setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &recv_timeout, sizeof(recv_timeout));
            std::string request;
            char chunk[4096];
            std::size_t header_end = std::string::npos;
            while ((header_end = request.find("\r\n\r\n")) == std::string::npos) {
                const auto got = recv(client, chunk, sizeof(chunk), 0);
                if (got <= 0) break;
                request.append(chunk, static_cast<std::size_t>(got));
            }
            if (header_end == std::string::npos) {
                close(client);
                return;
            }
            const std::string headers = request.substr(0, header_end);
            std::size_t content_length = 0;
            const std::string search = lower(headers);
            const auto start = search.find("content-length:");
            if (start != std::string::npos) {
                const auto number = start + std::strlen("content-length:");
                content_length = std::stoul(search.substr(number));
            }
            std::string body = request.substr(header_end + 4);
            while (body.size() < content_length) {
                const auto got = recv(client, chunk, sizeof(chunk), 0);
                if (got <= 0) break;
                body.append(chunk, static_cast<std::size_t>(got));
            }
            const auto path_start = headers.find(' ');
            const auto path_end = headers.find(' ', path_start + 1);
            Capture capture{headers.substr(path_start + 1, path_end - path_start - 1),
                            headers, body};
            {
                std::lock_guard lock(mutex_);
                captures_.push_back(std::move(capture));
            }
            if (reply.delay_ms) std::this_thread::sleep_for(std::chrono::milliseconds(reply.delay_ms));
            const std::string status = reply.status == 200 ? "OK" :
                                       reply.status == 400 ? "Bad Request" :
                                       reply.status == 429 ? "Too Many Requests" : "Server Error";
            send_all(client, "HTTP/1.1 " + std::to_string(reply.status) + " " + status +
                             "\r\nContent-Type: application/json\r\nContent-Length: " +
                             std::to_string(reply.body.size()) +
                             "\r\nConnection: close\r\n\r\n" + reply.body);
            close(client);
        }
    }

    int fd_ = -1;
    unsigned short port_ = 0;
    std::vector<Reply> replies_;
    std::vector<Capture> captures_;
    std::mutex mutex_;
    std::thread worker_;
};

ditto::ModelResult complete(ditto::ModelClient& model, bool once = true,
                            int timeout_seconds = 5,
                            std::optional<double> case_remaining_seconds = std::nullopt) {
    return model.complete(ditto::json::array({{{"role", "user"}, {"content", "hello"}}}),
                          ditto::json::array(), 2000, "medium", 0.0, "42",
                          timeout_seconds, "auto", once, case_remaining_seconds);
}

ditto::RunRequest tool_request(const std::string& endpoint) {
    ditto::RunRequest request;
    request.case_id = "case-1";
    request.user_id = "user-1";
    request.tool_endpoint = endpoint;
    return request;
}

void test_model_modes_and_parser() {
    const std::string success = R"({"choices":[{"message":{"content":"answer","tool_calls":[{"id":"a","function":{"name":"write","arguments":"{\"x\":1}"}},{"function":{"name":"bad","arguments":"{oops"}}]},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":2,"completion_tokens":1}})";
    Server normal({{200, success}});
    ditto::ModelClient plain(normal.url() + "/v1/", "model", "ticket", false, 2, 0.83);
    const auto result = complete(plain);
    const auto captures = normal.captures();
    require(captures.size() == 1 && captures[0].path == "/v1/chat/completions",
            "OpenAI-compatible path mismatch");
    const auto body = ditto::json::parse(captures[0].body);
    require(body["reasoning_effort"] == "medium" && body["top_p"] == 0.83 &&
            !body.contains("provider") &&
            !body.contains("reasoning"), "plain provider payload mismatch");
    require(result.content == "answer" && result.calls.size() == 2 &&
            result.calls[0].valid && result.calls[0].raw_args == "{\"x\":1}" &&
            result.calls[0].args["x"] == 1 && !result.calls[1].valid,
            "model tool-argument parsing mismatch");

    Server router({{200, R"({"choices":[{"message":{"content":"ok"}}]})"}});
    ditto::ModelClient openrouter(router.url(), "model", "secret", true);
    require(complete(openrouter).content == "ok", "OpenRouter response not parsed");
    const auto router_captures = router.captures();
    require(router_captures.size() == 1, "OpenRouter call count mismatch");
    const auto router_body = ditto::json::parse(router_captures[0].body);
    require(router_body["reasoning"] == ditto::json({{"effort", "medium"}, {"exclude", true}}) &&
            !router_body.contains("reasoning_effort") &&
            !router_body.contains("top_p") &&
            router_body["provider"]["sort"] == "throughput" &&
            router_body["provider"]["allow_fallbacks"] == false &&
            router_body["provider"]["data_collection"] == "deny" &&
            router_body["provider"]["zdr"] == true &&
            router_body["provider"]["ignore"] == ditto::json::array({"coreweave"}),
            "OpenRouter provider preferences mismatch");
    const std::string headers = lower(router_captures[0].headers);
    require(headers.find("http-referer: https://heyditto.ai") != std::string::npos &&
            headers.find("x-title: ditto") != std::string::npos &&
            headers.find("authorization: bearer secret") != std::string::npos,
            "OpenRouter headers mismatch");

    Server rejected({{200, R"({"error":{"message":"tool call validation failed"},"usage":{"prompt_tokens":5}})"}});
    ditto::ModelClient rejection_model(rejected.url(), "model", "ticket");
    const auto rejection = complete(rejection_model);
    require(rejection.finish == "error" && rejection.provider_error["message"] ==
            "tool call validation failed" && rejection.prompt_tokens == 5,
            "provider rejection lost as malformed completion");
    require(rejected.captures().size() == 1, "provider rejection was retried");

    Server malformed({{200, R"({"choices":[],"usage":{"prompt_tokens":3,"completion_tokens":1}})"},
                      {200, R"({"choices":[{"message":{"content":"fixed"}}],"usage":{"prompt_tokens":2,"completion_tokens":1}})"}});
    ditto::ModelClient recovering(malformed.url(), "model", "ticket");
    const auto recovered = complete(recovering, false);
    require(recovered.content == "fixed" && recovered.prompt_tokens == 5 &&
            recovered.output_tokens == 2, "malformed-response retry/usage mismatch");
    require(malformed.captures().size() == 2, "malformed completion was not retried");

    Server no_retry({{200, R"({"choices":[],"usage":{"prompt_tokens":3}})"}});
    ditto::ModelClient one_attempt(no_retry.url(), "model", "ticket", false, 1);
    bool exhausted = false;
    try {
        (void)complete(one_attempt, false);
    } catch (const ditto::ModelError& error) {
        exhausted = true;
        require(error.prompt_tokens == 3, "one-attempt failure lost usage");
    }
    require(exhausted && no_retry.captures().size() == 1,
            "configured one-attempt limit was ignored");

    Server three_retries({{200, R"({"choices":[]})"}, {200, R"({"choices":[]})"},
                          {200, R"({"choices":[{"message":{"content":"third"}}]})"}});
    ditto::ModelClient three_attempts(three_retries.url(), "model", "ticket", false, 3);
    require(complete(three_attempts, false).content == "third" &&
            three_retries.captures().size() == 3,
            "configured three-attempt limit was ignored");

    // The first HTTP attempt times out at one second, while the case still has
    // enough time for a second attempt. The retry reduces max_tokens.
    Server retry_after_timeout({{200, R"({"choices":[{"message":{"content":"late"}}]})", 1500},
                                {200, R"({"choices":[{"message":{"content":"recovered"}}]})"}});
    ditto::ModelClient timeout_model(retry_after_timeout.url(), "model", "ticket");
    require(complete(timeout_model, false, 1, 8.0).content == "recovered",
            "model per-attempt timeout consumed the entire case retry window");
    const auto timed_requests = retry_after_timeout.captures();
    require(timed_requests.size() == 2 &&
            ditto::json::parse(timed_requests[0].body)["max_tokens"] == 2000 &&
            ditto::json::parse(timed_requests[1].body)["max_tokens"] == 1200,
            "timed-out model retry did not reduce max_tokens");
}

void test_tool_delivery() {
    ditto::ToolEndpoint endpoint;
    ditto::ToolCall call;
    call.name = "write_task";
    call.raw_args = R"({"b":2, "a":"\u0061"})";
    call.args = ditto::json::parse(call.raw_args);

    Server completed({{200, R"({"result":"done"})"}});
    auto result = endpoint.execute(tool_request("  " + completed.url() + "/exec  "), call, 7, 5);
    require(result.state == ditto::DeliveryState::completed && result.observed &&
            result.output == "done", "successful tool delivery mismatch");
    const auto sent = completed.captures();
    require(sent.size() == 1 && sent[0].path == "/exec", "tool endpoint URL not trimmed");
    require(sent[0].body.find("\"args\":" + call.raw_args) != std::string::npos,
            "model-authored raw argument bytes were rewritten");
    const auto decoded = ditto::json::parse(sent[0].body);
    require(decoded["case_id"] == "case-1" && decoded["user_id"] == "user-1" &&
            decoded["name"] == "write_task" && decoded["hop"] == 7 &&
            decoded["args"]["a"] == "a", "tool execution body fields mismatch");

    Server two_second_boundary({{200, R"({"result":"sent"})"}});
    result = endpoint.execute(tool_request(two_second_boundary.url()), call, 0, 2, 10.0);
    require(result.state == ditto::DeliveryState::completed && result.observed &&
            result.output == "sent" && two_second_boundary.captures().size() == 1,
            "a configured two-second tool timeout blocked a call with ample case budget");

    Server refused({{400, R"({"error":"no"})"}});
    result = endpoint.execute(tool_request(refused.url()), call, 0, 5);
    require(result.state == ditto::DeliveryState::delivered_failed && !result.observed &&
            result.http_status == 400, "4xx admission refusal was marked executed");
    require(refused.captures().size() == 1, "4xx should not retry");

    Server throttled({{429, R"({"error":"busy"})"}, {200, R"({"result":"retried"})"}});
    result = endpoint.execute(tool_request(throttled.url()), call, 0, 5);
    require(result.state == ditto::DeliveryState::completed && result.observed &&
            result.output == "retried", "429 admission retry failed");
    const auto retries = throttled.captures();
    require(retries.size() == 2 && retries[0].body == retries[1].body,
            "429 retry changed tool request bytes");

    Server slow_throttle({{429, R"({"error":"busy"})", 1250},
                          {200, R"({"result":"second-trip"})"}});
    result = endpoint.execute(tool_request(slow_throttle.url()), call, 0, 2, 8.0);
    require(result.state == ditto::DeliveryState::completed && result.observed &&
            result.output == "second-trip" && slow_throttle.captures().size() == 2,
            "429 retry did not receive a fresh per-trip tool timeout");

    Server uncertain({{500, "{}"}});
    result = endpoint.execute(tool_request(uncertain.url()), call, 0, 5);
    require(result.state == ditto::DeliveryState::delivery_unknown && result.observed &&
            result.http_status == 500, "5xx response lost delivery uncertainty");
    require(uncertain.captures().size() == 1, "5xx tool call should not retry");

    Server malformed({{200, "not JSON"}});
    result = endpoint.execute(tool_request(malformed.url()), call, 0, 5);
    require(result.state == ditto::DeliveryState::completed && result.observed &&
            result.output.empty(), "malformed 200 tool result handling mismatch");
    require(malformed.captures().size() == 1, "malformed 200 tool result was retried");

    Server timed_out({{200, R"({"result":"too late"})", 3500}});
    result = endpoint.execute(tool_request(timed_out.url()), call, 0, 3);
    require(result.state == ditto::DeliveryState::delivery_unknown && result.observed,
            "read timeout after request upload should be delivery_unknown");
    require(timed_out.captures().size() == 1, "read timeout did not send a tool request");

    // A TCP connection that never completes TLS setup has not sent an HTTP
    // request, even though libcurl uses the same timeout code as a read timeout.
    Server tls_stall({{200, "", 3500, true}});
    std::string secure_url = tls_stall.url();
    secure_url.replace(0, 4, "https");
    result = endpoint.execute(tool_request(secure_url), call, 0, 3);
    require(result.state == ditto::DeliveryState::not_delivered && !result.observed,
            "TLS connect timeout must not create a tool receipt");
    require(tls_stall.captures().empty(), "TLS stall server parsed an HTTP request");

    result = endpoint.execute(tool_request("  "), call, 0, 5);
    require(result.state == ditto::DeliveryState::not_delivered && !result.observed &&
            result.output.find("unavailable") != std::string::npos,
            "blank tool endpoint must be unavailable");
    result = endpoint.execute(tool_request("http://127.0.0.1:0/exec"), call, 0, 5);
    require(result.state == ditto::DeliveryState::not_delivered && !result.observed,
            "connection refusal must not be observed");
}

}  // namespace

int main() {
    setenv("NO_PROXY", "127.0.0.1", 1);
    test_model_modes_and_parser();
    test_tool_delivery();
}
