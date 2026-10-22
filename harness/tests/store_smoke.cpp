#include "store.hpp"

// Keep smoke assertions active even when CMake uses its Release profile.
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

#include <unistd.h>

int main() {
    ditto::Store store(":memory:");
    const auto counts = store.seed({
        {"user_id", "A"},
        {"pairs", ditto::json::array({
            {{"pair_id", "p1"}, {"timestamp", "2026-01-01"}, {"prompt", "apple alpha"}},
            {{"pair_id", "p2"}, {"timestamp", "2026-01-02"}, {"prompt", "banana beta"}}
        })},
        {"subjects", ditto::json::array({{{"id", "s1"}, {"subject_text", "Apple"}}})},
        {"links", ditto::json::array({{{"subject_id", "s1"}, {"pair_id", "p1"}}})}
    });
    assert(counts["pairs"] == 2 && counts["subjects"] == 1 && counts["links"] == 1);
    const auto first = store.get_pair("A", "p1");
    assert(first && first->seq == 1);
    assert(store.all_pairs("A").size() == 2);

    const auto updated = store.seed({{"user_id", "A"}, {"pairs", ditto::json::array({
        {{"pair_id", "p1"}, {"timestamp", "2026-01-03"}, {"prompt", "apple revised"}}
    })}});
    assert(updated["pairs"] == 1);
    assert(store.get_pair("A", "p1")->seq == first->seq);
    assert(store.get_pair("A", "p1")->prompt == "apple revised");
    store.seed({{"user_id", "B"}, {"pairs", ditto::json::array({
        {{"pair_id", "p1"}, {"prompt", "red apple"}}
    })}});
    assert(store.get_pair("B", "p1")->prompt == "red apple");
    assert(store.get_pair("A", "p1")->prompt == "apple revised");

    // Pydantic rejects present-but-nonstring seed fields; a bad later row
    // must roll back earlier rows in the same wave.
    auto invalid_seed = [&](const ditto::json& body) {
        try { store.seed(body); }
        catch (const std::invalid_argument&) { return; }
        assert(false && "malformed seed request was accepted");
    };
    invalid_seed({{"user_id", 42}});
    invalid_seed({{"user_id", "A"}, {"pairs", ditto::json::array({
        {{"pair_id", "rollback-p"}, {"prompt", "first row"}},
        {{"pair_id", "bad-p"}, {"prompt", 42}}
    })}});
    assert(!store.get_pair("A", "rollback-p"));
    invalid_seed({{"pairs", ditto::json::array({{{"pair_id", "bad-null"}, {"response", nullptr}}})}});
    invalid_seed({{"subjects", ditto::json::array({{{"id", "bad-subject"}, {"description_text", false}}})}});
    invalid_seed({{"links", ditto::json::array({{{"subject_id", "s1"}, {"pair_id", 7}}})}});
    invalid_seed({{"wave", "not an integer"}});
    invalid_seed({{"wave", 1.5}});
    invalid_seed({{"wave", ditto::json::array()}});
    invalid_seed({{"wave", "1__0"}});
    assert(store.seed({{"wave", true}})["pairs"] == 0);
    assert(store.seed({{"wave", " 1_0.00 "}})["pairs"] == 0);
    assert(store.seed({{"wave", -4.0}})["pairs"] == 0);
    store.seed({{"pairs", ditto::json::array({{{"pair_id", "default-p"}, {"prompt", "default graph"}}})}});
    assert(store.get_pair("", "default-p"));
    assert(store.get_pair("\u00a0\u3000", "default-p"));
    assert(!store.get_pair("A", "default-p"));
    store.seed({{"user_id", " A "}, {"pairs", ditto::json::array({
        {{"pair_id", "spaced-p"}, {"prompt", "exact user capability"}}
    })}});
    assert(store.get_pair(" A ", "spaced-p"));
    assert(!store.get_pair("A", "spaced-p"));

    const auto search = store.local_tool("A", "search_memories", {{"queries", "apple"}});
    assert(search.is_object() && search["memories"].size() == 1);
    assert(search["memories"][0]["pair_id"] == "p1");
    store.seed({{"user_id", "A"}, {"subjects", ditto::json::array({
        {{"id", "unicode-k"}, {"subject_text", "\u212aelvin project"}},
        {{"id", "unicode-i"}, {"subject_text", "ab\u0130 notes"}}
    })}});
    const auto kelvin = store.local_tool("A", "search_subjects", {{"query", "kelvin"}});
    assert(kelvin["subjects"].size() == 1 && kelvin["subjects"][0]["id"] == "unicode-k");
    const auto dotted = store.local_tool("A", "search_subjects", {{"query", "abi"}});
    assert(dotted["subjects"].size() == 1 && dotted["subjects"][0]["id"] == "unicode-i");
    assert(store.local_tool("B", "search_subjects", {{"query", "kelvin"}})["subjects"].empty());
    const auto unicode_empty = store.local_tool("A", "search_memories", {{"query", "\u00a0"}});
    assert(unicode_empty.is_string() && unicode_empty.get<std::string>().find("empty queries") != std::string::npos);
    store.seed({{"user_id", "A"}, {"pairs", ditto::json::array({
        {{"pair_id", "unicode-p"}, {"prompt", "unicodesnippet\u00a0spacetoken"}}
    })}});
    const auto unicode_search = store.local_tool("A", "search_memories", {{"query", "unicodesnippet"}});
    assert(unicode_search["memories"].size() == 1);
    assert(unicode_search["memories"][0]["text"].get<std::string>().find("unicodesnippet spacetoken") != std::string::npos);
    const auto scoped = store.local_tool("A", "search_memories_in_subjects", {{"subject_id", "s1"}});
    assert(scoped["memories"].size() == 1 && scoped["memories"][0]["pair_id"] == "p1");
    store.seed({{"user_id", "A"}, {"pairs", ditto::json::array({
        {{"pair_id", "unicode-subject-p"}, {"prompt", "\u00c9clair \u212aite"}}
    })}, {"links", ditto::json::array({
        {{"subject_id", "s1"}, {"pair_id", "unicode-subject-p"}}
    })}});
    const auto scoped_unicode = store.local_tool("A", "search_memories_in_subjects",
        {{"subject_id", "s1"}, {"query", "\u00e9clair"}});
    assert(scoped_unicode["memories"].size() == 1 &&
           scoped_unicode["memories"][0]["pair_id"] == "unicode-subject-p");
    const auto scoped_kelvin = store.local_tool("A", "search_memories_in_subjects",
        {{"subject_id", "s1"}, {"query", "kite"}});
    assert(scoped_kelvin["memories"].size() == 1 &&
           scoped_kelvin["memories"][0]["pair_id"] == "unicode-subject-p");
    assert(store.unheld_ids("A", "fetch_memories", {{"pairIds", "p1"}}).empty());
    assert(store.unheld_ids("A", "fetch_memories", {{"pairIds", ditto::json::array({"missing", "missing"})}})
           == std::vector<std::string>({"missing", "missing"}));
    assert(store.unheld_ids("A", "fetch_memories", {{"pairIds", nullptr}, {"pair_ids", "p1"}}).empty());
    assert(store.unheld_ids("A", "search_memories_in_subjects", {{"subject_id", "s1"}}).empty());
    assert(store.unheld_ids("A", "search_memories_in_subjects", {{"subject_id", "missing"}})
           == std::vector<std::string>({"missing"}));
    assert(store.unheld_ids("A", "search_memories_in_subjects", ditto::json::object())
           == std::vector<std::string>({""}));
    assert(store.unheld_ids("A", "update_memory", {{"pair_id", "p1"}}).empty());
    assert(store.unheld_ids("B", "update_memory", {{"pair_id", "p2"}})
           == std::vector<std::string>({"p2"}));
    assert(store.memory_hits("A", "search_memories_in_subjects", {{"subject_id", "s1"}})
           == std::vector<std::string>({"unicode-subject-p", "p1"}));
    assert(store.memory_hits("A", "fetch_memories", {{"pairIds", ditto::json::array({"p1", "p1"})}})
           == std::vector<std::string>({"p1", "p1"}));
    assert(store.memory_hits("B", "fetch_memories", {{"pairIds", "p2"}}).empty());
    store.seed({{"user_id", "edge"}, {"pairs", ditto::json::array({
        {{"pair_id", ""}, {"prompt", "valid empty opaque id"}}
    })}});
    assert(store.memory_hits("edge", "fetch_memories", ditto::json::object()).empty());
    assert(store.memory_hits("edge", "fetch_memories", {{"pairIds", ""}}).empty());
    assert(store.memory_hits("edge", "fetch_memories", {{"pairIds", ditto::json::array({""})}})
           == std::vector<std::string>({""}));
    const auto fetched = store.local_tool("A", "fetch_memories", {{"pairIds", ditto::json::array()}});
    assert(fetched.is_string() && fetched.get<std::string>().find("empty pairIds") != std::string::npos);

    store.mirror_save("A", "Remember this local note");
    auto all = store.all_pairs("A");
    assert(all.size() == 5);
    bool saw_saved = false;
    std::string saved_id;
    for (const auto& pair : all) {
        if (pair.pair_id.rfind("saved-", 0) == 0) {
            saw_saved = true;
            saved_id = pair.pair_id;
        }
    }
    assert(saw_saved);
    store.mirror_save("A", "\u00a0\u3000");
    assert(store.all_pairs("A").size() == 5);
    assert(store.unheld_ids("A", "fetch_memories", {{"pairIds", saved_id}})
           == std::vector<std::string>({saved_id}));
    assert(store.unheld_ids("A", "update_memory", {{"pair_id", saved_id}})
           == std::vector<std::string>({saved_id}));
    assert(store.memory_hits("A", "fetch_memories", {{"pairIds", saved_id}})
           == std::vector<std::string>({saved_id}));
    assert(store.memory_hits("A", "search_memories", {{"query", "Remember"}})
           == std::vector<std::string>({saved_id}));
    store.mirror_save("A", "Remember this local note");
    assert(store.all_pairs("A").size() == 5);
    const auto fetched_saved = store.local_tool("A", "fetch_memories", {{"pairIds", saved_id}});
    assert(fetched_saved["memories"].size() == 1);
    assert(!fetched_saved["memories"][0].contains("pair_id"));
    const auto before_mirror = store.get_pair("A", "p2");
    store.mirror_update("A", "p2", "banana changed");
    assert(store.get_pair("A", "p2")->prompt == "banana changed");
    assert(store.get_pair("A", "p2")->response.empty());
    assert(store.get_pair("A", "p2")->seq == before_mirror->seq);
    assert(store.get_pair("A", "p2")->timestamp == before_mirror->timestamp);
    assert(store.local_tool("A", "search_memories", {{"queries", "beta"}})["memories"].empty());
    assert(store.local_tool("A", "search_memories", {{"queries", "changed"}})["memories"].size() == 1);
    store.mirror_update("B", "p2", "must not leak");
    assert(!store.get_pair("B", "p2"));

    store.put_vectors("A", {{"hash", {0.25f, -0.5f}}, {"zero", {}}});
    const auto vectors = store.vectors("A", {"hash", "zero", "missing"});
    assert(vectors.size() == 2 && vectors.at("hash").size() == 2);
    assert(vectors.at("zero").empty());
    assert(std::abs(vectors.at("hash")[1] + 0.5f) < 1e-6f);
    assert(store.vectors("B", {"hash"}).empty());

    // Open a second process-style Store to ensure the float32 data really
    // survived SQLite, rather than only the in-process vector cache.
    char db_path[] = "/tmp/ditto-store-smoke-XXXXXX";
    const int descriptor = ::mkstemp(db_path);
    assert(descriptor >= 0);
    ::close(descriptor);
    {
        ditto::Store first_store(db_path);
        first_store.put_vectors("A", {{"persisted", {1.0f, -2.5f}}, {"empty", {}}});
    }
    {
        ditto::Store reloaded(db_path);
        const auto held = reloaded.vectors("A", {"persisted", "empty"});
        assert(held.size() == 2);
        assert(held.at("persisted") == std::vector<float>({1.0f, -2.5f}));
        assert(held.at("empty").empty());
        assert(reloaded.vectors("B", {"persisted"}).empty());
    }
    std::remove(db_path);
    std::cout << "store smoke passed\n";
}
