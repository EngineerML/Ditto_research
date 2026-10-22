#pragma once

#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "types.hpp"

struct sqlite3;

namespace ditto {

// One SQLite connection per process, guarded for concurrent HTTP requests.
// All public methods normalize user IDs before reading or writing records.
class Store {
public:
    explicit Store(std::string db_path);
    ~Store();

    Store(const Store&) = delete;
    Store& operator=(const Store&) = delete;
    Store(Store&&) = delete;
    Store& operator=(Store&&) = delete;

    // Upsert pairs, subjects, then links in one transaction. Counts describe
    // input list lengths, including existing rows that were updated.
    json seed(const json& body);

    std::vector<MemoryPair> all_pairs(const std::string& user_id);
    std::optional<MemoryPair> get_pair(const std::string& user_id,
                                       const std::string& pair_id);

    // Native float32 blobs keyed by SHA-256 of full record text, scoped by user.
    std::unordered_map<std::string, std::vector<float>> vectors(
        const std::string& user_id, const std::vector<std::string>& hashes);
    void put_vectors(const std::string& user_id,
                     const std::unordered_map<std::string, std::vector<float>>& vectors);

    // Successful memory reads return JSON objects; input errors return JSON
    // strings. The caller serializes this value as model-visible tool content.
    json local_tool(const std::string& user_id, const std::string& name,
                    const json& args);

    // Identifiers a memory tool names but this user's store cannot hand out.
    // Check this before sending a memory-read call to the external endpoint.
    std::vector<std::string> unheld_ids(const std::string& user_id,
                                        const std::string& name, const json& args);
    // Recall pins are derived from local search hits, not displayed JSON;
    // synthetic saved IDs may be returned here even though they are hidden.
    std::vector<std::string> memory_hits(const std::string& user_id,
                                         const std::string& name, const json& args);

    // Mirror completed external save_memory/update_memory calls locally.
    void mirror_save(const std::string& user_id, const std::string& content);
    void mirror_update(const std::string& user_id, const std::string& pair_id,
                       const std::string& content);

private:
    sqlite3* db_ = nullptr;
    std::mutex mutex_;
    std::unordered_map<std::string, std::unordered_map<std::string, std::vector<float>>> vector_cache_;
};

}  // namespace ditto
