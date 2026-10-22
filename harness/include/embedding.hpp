#pragma once

#include <stdexcept>
#include <string>
#include <vector>

namespace ditto {

class EmbeddingError : public std::runtime_error {
public:
    explicit EmbeddingError(const std::string& message) : std::runtime_error(message) {}
};

class Embedder {
public:
    Embedder(std::string base_url, int timeout_seconds);

    // Returns one unit-length float32 vector per input, in input order.
    // Empty input produces an empty result without an HTTP request.
    std::vector<std::vector<float>> embed(const std::vector<std::string>& texts) const;

private:
    std::vector<std::vector<float>> post(const std::vector<std::string>& chunk) const;

    std::string url_;
    int timeout_seconds_;
};

}  // namespace ditto
