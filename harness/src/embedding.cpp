#include "embedding.hpp"

#include <curl/curl.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <limits>
#include <memory>
#include <mutex>
#include <random>
#include <string_view>
#include <thread>
#include <utility>

namespace ditto {
namespace {

using json = nlohmann::json;

constexpr const char* kEmbedPath = "/api/embed";
constexpr const char* kEmbedModel = "embeddinggemma";
constexpr size_t kMaxInputs = 32;
constexpr size_t kMaxBatchChars = 60000;
constexpr size_t kMaxInputChars = 12000;
constexpr int kAttempts = 4;

struct HttpResponse {
    CURLcode code = CURLE_OK;
    long status = 0;
    std::string body;
    std::string error;
};

void ensure_curl() {
    static std::once_flag once;
    static CURLcode initialized = CURLE_OK;
    std::call_once(once, [] { initialized = curl_global_init(CURL_GLOBAL_DEFAULT); });
    if (initialized != CURLE_OK) throw EmbeddingError("curl_global_init failed");
}

size_t append_body(char* bytes, size_t size, size_t count, void* context) {
    const size_t length = size * count;
    static_cast<std::string*>(context)->append(bytes, length);
    return length;
}

// Input budgets count Unicode code points, not UTF-8 bytes.
size_t next_codepoint(const std::string& text, size_t at) {
    const unsigned char first = static_cast<unsigned char>(text[at]);
    const size_t width = first < 0x80 ? 1 : first < 0xe0 ? 2 : first < 0xf0 ? 3 : 4;
    return std::min(text.size(), at + width);
}

std::pair<std::string, size_t> truncate_input(const std::string& text) {
    size_t position = 0;
    size_t characters = 0;
    while (position < text.size() && characters < kMaxInputChars) {
        position = next_codepoint(text, position);
        ++characters;
    }
    return {text.substr(0, position), characters};
}

HttpResponse post_json(const std::string& url, const std::string& body, int timeout_seconds) {
    ensure_curl();
    HttpResponse response;
    std::unique_ptr<CURL, decltype(&curl_easy_cleanup)> handle(curl_easy_init(), curl_easy_cleanup);
    if (!handle) throw EmbeddingError("curl_easy_init failed");
    std::unique_ptr<curl_slist, decltype(&curl_slist_free_all)> headers(
        curl_slist_append(nullptr, "Content-Type: application/json"), curl_slist_free_all);
    if (!headers) throw EmbeddingError("could not allocate HTTP headers");
    char error_buffer[CURL_ERROR_SIZE] = {};
    const long timeout_ms = static_cast<long>(std::max(1, timeout_seconds)) * 1000;
    curl_easy_setopt(handle.get(), CURLOPT_URL, url.c_str());
    curl_easy_setopt(handle.get(), CURLOPT_HTTPHEADER, headers.get());
    curl_easy_setopt(handle.get(), CURLOPT_POST, 1L);
    curl_easy_setopt(handle.get(), CURLOPT_POSTFIELDS, body.data());
    curl_easy_setopt(handle.get(), CURLOPT_POSTFIELDSIZE_LARGE,
                     static_cast<curl_off_t>(body.size()));
    curl_easy_setopt(handle.get(), CURLOPT_TIMEOUT_MS, timeout_ms);
    curl_easy_setopt(handle.get(), CURLOPT_CONNECTTIMEOUT_MS, timeout_ms);
    curl_easy_setopt(handle.get(), CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(handle.get(), CURLOPT_FOLLOWLOCATION, 0L);
    curl_easy_setopt(handle.get(), CURLOPT_ACCEPT_ENCODING, "");
    curl_easy_setopt(handle.get(), CURLOPT_WRITEFUNCTION, append_body);
    curl_easy_setopt(handle.get(), CURLOPT_WRITEDATA, &response.body);
    curl_easy_setopt(handle.get(), CURLOPT_ERRORBUFFER, error_buffer);
    curl_easy_setopt(handle.get(), CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(handle.get(), CURLOPT_SSL_VERIFYHOST, 2L);
    // Keep libcurl's HTTP(S)_PROXY and NO_PROXY handling. A supplied CA bundle
    // takes precedence over the system trust store, as in the model client.
    const char* ca = std::getenv("CURL_CA_BUNDLE");
    if (!ca || !*ca) ca = std::getenv("SSL_CERT_FILE");
    if (ca && *ca) curl_easy_setopt(handle.get(), CURLOPT_CAINFO, ca);
    response.code = curl_easy_perform(handle.get());
    if (response.code != CURLE_OK) {
        response.error = error_buffer[0] ? error_buffer : curl_easy_strerror(response.code);
    }
    curl_easy_getinfo(handle.get(), CURLINFO_RESPONSE_CODE, &response.status);
    return response;
}

bool retry_status(long status) {
    return status == 429 || status == 500 || status == 502 || status == 503 || status == 504;
}

double number_from(const json& value) {
    if (value.is_number()) return value.get<double>();
    if (value.is_boolean()) return value.get<bool>() ? 1.0 : 0.0;
    if (value.is_string()) {
        const std::string text = value.get<std::string>();
        size_t consumed = 0;
        try {
            const double number = std::stod(text, &consumed);
            if (std::all_of(text.begin() + static_cast<std::ptrdiff_t>(consumed), text.end(),
                            [](unsigned char c) { return std::isspace(c) != 0; })) return number;
        } catch (const std::exception&) {
            // Invalid numeric vector values must be rejected, so a bad
            // remote vector must fall back to lexical retrieval, not fail /run.
        }
    }
    throw EmbeddingError("embedding response unreadable: vector contains a nonnumeric value");
}

std::vector<std::vector<float>> parse_vectors(const std::string& body) {
    const json decoded = json::parse(body, nullptr, false);
    if (!decoded.is_object() || !decoded.contains("embeddings")) {
        throw EmbeddingError("embedding response unreadable: no embeddings field");
    }
    const json& embeddings = decoded["embeddings"];
    if (!embeddings.is_array() || embeddings.empty()) {
        throw EmbeddingError("embedding response does not match the inputs");
    }
    size_t dimensions = 0;
    std::vector<std::vector<float>> vectors;
    vectors.reserve(embeddings.size());
    for (const auto& entry : embeddings) {
        if (!entry.is_array() || entry.empty()) {
            throw EmbeddingError("embedding response does not match the inputs");
        }
        if (dimensions == 0) dimensions = entry.size();
        if (entry.size() != dimensions) {
            throw EmbeddingError("embedding response does not match the inputs");
        }
        std::vector<double> values;
        values.reserve(entry.size());
        double sum_squares = 0.0;
        for (const auto& value : entry) {
            const double number = number_from(value);
            values.push_back(number);
            sum_squares += number * number;
        }
        const double norm = std::sqrt(sum_squares);
        if (norm == 0.0 || !std::isfinite(norm)) {
            throw EmbeddingError("embedding vector has no direction");
        }
        std::vector<float> vector;
        vector.reserve(values.size());
        for (const double value : values) vector.push_back(static_cast<float>(value / norm));
        vectors.push_back(std::move(vector));
    }
    return vectors;
}

void wait_before_retry(int attempt) {
    thread_local std::mt19937 engine(std::random_device{}());
    std::uniform_real_distribution<double> jitter(0.0, 0.25);
    const double base = std::min(8.0, 0.5 * std::pow(2.0, attempt));
    std::this_thread::sleep_for(std::chrono::duration<double>(base + jitter(engine)));
}

}  // namespace

Embedder::Embedder(std::string base_url, int timeout_seconds)
    : timeout_seconds_(timeout_seconds) {
    while (!base_url.empty() && base_url.back() == '/') base_url.pop_back();
    if (base_url.empty()) throw EmbeddingError("embedding base URL is empty");
    if (timeout_seconds_ <= 0) throw EmbeddingError("embedding timeout must be positive");
    url_ = std::move(base_url) + kEmbedPath;
}

std::vector<std::vector<float>> Embedder::embed(const std::vector<std::string>& texts) const {
    std::vector<std::vector<float>> output;
    if (texts.empty()) return output;
    std::vector<std::string> chunk;
    size_t chunk_chars = 0;
    auto flush = [&] {
        if (chunk.empty()) return;
        std::vector<std::vector<float>> vectors = post(chunk);
        if (vectors.size() != chunk.size() && chunk.size() > 1) {
            vectors.clear();
            for (const auto& text : chunk) {
                auto single = post({text});
                for (auto& vector : single) vectors.push_back(std::move(vector));
            }
        }
        if (vectors.size() != chunk.size()) {
            throw EmbeddingError("embedding service returned " + std::to_string(vectors.size()) +
                                 " vectors for " + std::to_string(chunk.size()) + " inputs");
        }
        for (auto& vector : vectors) output.push_back(std::move(vector));
        chunk.clear();
        chunk_chars = 0;
    };
    for (const auto& original : texts) {
        auto [text, characters] = truncate_input(original);
        if (!chunk.empty() && (chunk.size() >= kMaxInputs ||
                               chunk_chars + characters > kMaxBatchChars)) {
            flush();
        }
        chunk.push_back(std::move(text));
        chunk_chars += characters;
    }
    flush();
    return output;
}

std::vector<std::vector<float>> Embedder::post(const std::vector<std::string>& chunk) const {
    const std::string body = json{{"model", kEmbedModel}, {"input", chunk}}.dump();
    std::string problem;
    for (int attempt = 0; attempt < kAttempts; ++attempt) {
        if (attempt) wait_before_retry(attempt);
        const HttpResponse response = post_json(url_, body, timeout_seconds_);
        if (response.code != CURLE_OK) {
            problem = "transport: " + response.error;
            continue;
        }
        if (retry_status(response.status)) {
            problem = "status " + std::to_string(response.status);
            continue;
        }
        if (response.status != 200) {
            throw EmbeddingError("embedding request refused: status " +
                                 std::to_string(response.status) + ": " +
                                 response.body.substr(0, 300));
        }
        return parse_vectors(response.body);
    }
    throw EmbeddingError("embedding failed after " + std::to_string(kAttempts) +
                         " attempts: " + problem);
}

}  // namespace ditto
