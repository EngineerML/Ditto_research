// Compile this isolated test with -lcurl -pthread. Including the implementation
// lets the test exercise remote-response validation without a listening server.
#include "../src/embedding.cpp"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cmath>
#include <iostream>

int main() {
    const auto vectors = ditto::parse_vectors(R"({"embeddings":[[3,4]]})");
    assert(vectors.size() == 1 && vectors[0].size() == 2);
    assert(std::abs(vectors[0][0] - 0.6f) < 1e-6f);
    assert(std::abs(vectors[0][1] - 0.8f) < 1e-6f);

    // Numeric conversion failures surface as EmbeddingError. The agent
    // catches that type and falls back to lexical retrieval.
    for (const char* bad : {
             R"({"embeddings":[["not a number"]]})",
             R"({"embeddings":[["1e99999"]]})",
             R"({"embeddings":[[null]]})"}) {
        bool caught = false;
        try { static_cast<void>(ditto::parse_vectors(bad)); }
        catch (const ditto::EmbeddingError&) { caught = true; }
        assert(caught);
    }
    std::cout << "embedding smoke passed\n";
}
