#include "agent.hpp"

#include <atomic>
#include <future>
#include <stdexcept>
#include <string>
#include <thread>

namespace {
void require(bool yes, const std::string& message) {
    if (!yes) throw std::runtime_error(message);
}
}

int main() {
    ditto::ToolCall valid;
    valid.name = "send_message";
    valid.raw_args = R"({ "recipient" : "Ada", "message" : "hello", "": 7, "meta": {"z": 1, "a": 2} })";
    valid.args = ditto::json::parse(valid.raw_args);
    require(ditto::tool_args_for_prompt(valid) ==
                R"({"recipient": "Ada", "message": "hello", "": 7, "meta": {"z": 1, "a": 2}})",
            "model-visible ledger lost insertion order or spaced separators");
    require(ditto::tool_args_for_assistant(valid) ==
                R"({"recipient": "Ada", "message": "hello", "meta": {"z": 1, "a": 2}})",
            "assistant tool arguments were not reserialized from the parsed object");

    ditto::ToolCall unreadable;
    unreadable.raw_args = "{broken JSON";
    unreadable.valid = false;
    require(ditto::tool_args_for_assistant(unreadable) == unreadable.raw_args,
            "unreadable tool arguments should retain the raw model string");
    require(ditto::tool_args_for_prompt(unreadable) == "{}",
            "unreadable tool arguments should not be parsed into a ledger object");

    ditto::ModelResult follow_up;
    follow_up.content = " \n\t";
    require(ditto::retry_empty_follow_up(follow_up), "blank follow-up must be retried");
    follow_up.content = "Maybe ask this?";
    follow_up.finish = "length";
    follow_up.calls.push_back(valid);
    require(!ditto::retry_empty_follow_up(follow_up),
            "nonblank follow-up must stop retries even with length finish or tool calls");
    require(ditto::model_strip("\xC2\xA0\xE2\x80\xA8") == "",
            "Unicode-only model reply should be treated as blank");
    require(ditto::model_strip("\xC2\xA0Value\xE2\x80\xA8") == "Value",
            "Unicode model reply stripping failed");
    follow_up.content = "\xC2\xA0";
    require(ditto::retry_empty_follow_up(follow_up),
            "NBSP-only follow-up should be retried");

    const ditto::json memory_reply = {
        {"served_by", "local"},
        {"memories", ditto::json::array({{{"text", "hello"}, {"session_id", "s"},
                                          {"timestamp", "2026-01-01"}, {"pair_id", "p1"}}})},
        {"note", "read this"},
    };
    require(ditto::memory_tool_content("search_memories", memory_reply) ==
                R"({"memories": [{"pair_id": "p1", "timestamp": "2026-01-01", "session_id": "s", "text": "hello"}], "served_by": "local", "note": "read this"})",
            "memory tool receipt lost key order or spaced separators");
    require(ditto::memory_tool_content("fetch_memories", "Tool error: empty") ==
                "Tool error: empty", "empty-input memory note was JSON quoted");

    ditto::ShortOrderCache cache;
    int reads = 0;
    require(cache.get_or_read("same notes", [&] {
                ++reads; return std::optional<std::string>("M2, M1");
            }) == "M2, M1", "first order reading missing");
    require(cache.get_or_read("same notes", [&] {
                ++reads; return std::optional<std::string>("wrong");
            }) == "M2, M1" && reads == 1, "cached order reading was repeated");
    require(!cache.get_or_read("failed", [&] {
                ++reads; return std::optional<std::string>{};
            }), "failed reading was not returned as empty");
    require(cache.get_or_read("failed", [&] {
                ++reads; return std::optional<std::string>("recovered");
            }) == "recovered" && reads == 3, "failed reading was cached instead of retried");
    for (int index = 0; index < 520; ++index)
        cache.get_or_read("key " + std::to_string(index), [] {
            return std::optional<std::string>("held");
        });
    require(cache.size() == 512, "order cache exceeded its 512-entry bound");

    std::promise<void> release;
    auto gate = release.get_future().share();
    std::atomic<int> concurrent_reads{0};
    auto first = std::async(std::launch::async, [&] {
        return cache.get_or_read("in flight", [&] {
            ++concurrent_reads;
            gate.wait();
            return std::optional<std::string>("shared");
        });
    });
    while (concurrent_reads.load() == 0) std::this_thread::yield();
    auto second = std::async(std::launch::async, [&] {
        return cache.get_or_read("in flight", [&] {
            ++concurrent_reads;
            return std::optional<std::string>("wrong");
        });
    });
    release.set_value();
    require(first.get() == "shared" && second.get() == "shared" && concurrent_reads == 1,
            "concurrent cases duplicated an in-flight order reading");
}
