#include "store.hpp"

#include <sqlite3.h>
#include <openssl/sha.h>

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <ctime>
#include <iomanip>
#include <memory>
#include <limits>
#include <locale.h>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
#include <wctype.h>

namespace ditto {
namespace {

constexpr const char* kSchema = R"sql(
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS pairs (
    user_id TEXT NOT NULL,
    pair_id TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '',
    ts TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL DEFAULT '',
    response TEXT NOT NULL DEFAULT '',
    seq INTEGER NOT NULL,
    PRIMARY KEY (user_id, pair_id)
);
CREATE INDEX IF NOT EXISTS pairs_session ON pairs(user_id, session_id, seq);
CREATE INDEX IF NOT EXISTS pairs_ts ON pairs(user_id, ts, seq);
CREATE VIRTUAL TABLE IF NOT EXISTS pairs_fts USING fts5(
    prompt, response, content='pairs', content_rowid='rowid', tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS pairs_ai AFTER INSERT ON pairs BEGIN
    INSERT INTO pairs_fts(rowid, prompt, response) VALUES (new.rowid, new.prompt, new.response);
END;
CREATE TRIGGER IF NOT EXISTS pairs_ad AFTER DELETE ON pairs BEGIN
    INSERT INTO pairs_fts(pairs_fts, rowid, prompt, response) VALUES ('delete', old.rowid, old.prompt, old.response);
END;
CREATE TABLE IF NOT EXISTS subjects (
    user_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    subject_text TEXT NOT NULL DEFAULT '',
    description_text TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (user_id, subject_id)
);
CREATE TABLE IF NOT EXISTS links (
    user_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    pair_id TEXT NOT NULL,
    PRIMARY KEY (user_id, subject_id, pair_id)
);
CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS vectors (user_id TEXT NOT NULL, h TEXT NOT NULL, v BLOB NOT NULL,
    PRIMARY KEY (user_id, h));
INSERT OR IGNORE INTO counters(name, value) VALUES ('seq', 0);
)sql";

constexpr const char* kProvenance =
    "read locally from this harness's own memory store for this user, not returned by the tool endpoint";
constexpr const char* kNoSearchMatches =
    "no stored conversation matches these queries. An empty result is an answer about the user's own history.";
constexpr const char* kSearchIdsNote =
    "each entry's pair_id is that stored record's own identifier: pass it to fetch_memories for the full text, and when one of these notes is itself the thing to be changed or removed, take the identifier from the entry whose text is that note";

void exec_sql(sqlite3* db, const char* sql) {
    char* error = nullptr;
    const int rc = sqlite3_exec(db, sql, nullptr, nullptr, &error);
    if (rc != SQLITE_OK) {
        const std::string detail = error ? error : sqlite3_errmsg(db);
        sqlite3_free(error);
        throw std::runtime_error("SQLite: " + detail);
    }
}

class Statement {
public:
    Statement(sqlite3* db, const char* sql) : db_(db) {
        if (sqlite3_prepare_v2(db, sql, -1, &stmt_, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("SQLite prepare: ") + sqlite3_errmsg(db));
        }
    }
    ~Statement() { sqlite3_finalize(stmt_); }
    Statement(const Statement&) = delete;
    Statement& operator=(const Statement&) = delete;

    void bind(int index, const std::string& value) {
        if (sqlite3_bind_text(stmt_, index, value.data(), static_cast<int>(value.size()), SQLITE_TRANSIENT) != SQLITE_OK) {
            throw std::runtime_error(std::string("SQLite bind text: ") + sqlite3_errmsg(db_));
        }
    }
    void bind(int index, std::int64_t value) {
        if (sqlite3_bind_int64(stmt_, index, value) != SQLITE_OK) {
            throw std::runtime_error(std::string("SQLite bind integer: ") + sqlite3_errmsg(db_));
        }
    }
    void bind_blob(int index, const std::vector<float>& values) {
        const std::size_t bytes = values.size() * sizeof(float);
        if (bytes > static_cast<std::size_t>(std::numeric_limits<int>::max())) {
            throw std::invalid_argument("embedding vector too large for SQLite blob");
        }
        static const unsigned char empty_byte = 0;
        const void* blob = values.empty() ? static_cast<const void*>(&empty_byte) : values.data();
        if (sqlite3_bind_blob(stmt_, index, blob, static_cast<int>(bytes), SQLITE_TRANSIENT) != SQLITE_OK) {
            throw std::runtime_error(std::string("SQLite bind blob: ") + sqlite3_errmsg(db_));
        }
    }
    int step() {
        const int rc = sqlite3_step(stmt_);
        if (rc != SQLITE_ROW && rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("SQLite step: ") + sqlite3_errmsg(db_));
        }
        return rc;
    }
    void done() {
        if (step() != SQLITE_DONE) throw std::runtime_error("SQLite statement returned an unexpected row");
    }
    void reset() {
        const int rc = sqlite3_reset(stmt_);
        if (rc != SQLITE_OK) {
            throw std::runtime_error(std::string("SQLite reset: ") + sqlite3_errmsg(db_));
        }
        sqlite3_clear_bindings(stmt_);
    }
    sqlite3_stmt* get() const { return stmt_; }

private:
    sqlite3* db_ = nullptr;
    sqlite3_stmt* stmt_ = nullptr;
};

class Transaction {
public:
    explicit Transaction(sqlite3* db) : db_(db) { exec_sql(db_, "BEGIN"); }
    ~Transaction() {
        if (!committed_) sqlite3_exec(db_, "ROLLBACK", nullptr, nullptr, nullptr);
    }
    void commit() {
        exec_sql(db_, "COMMIT");
        committed_ = true;
    }
private:
    sqlite3* db_;
    bool committed_ = false;
};

std::string column_text(sqlite3_stmt* stmt, int index) {
    const unsigned char* ptr = sqlite3_column_text(stmt, index);
    return ptr ? reinterpret_cast<const char*>(ptr) : "";
}

MemoryPair row_pair(sqlite3_stmt* stmt) {
    MemoryPair pair;
    pair.pair_id = column_text(stmt, 0);
    pair.session_id = column_text(stmt, 1);
    pair.timestamp = column_text(stmt, 2);
    pair.prompt = column_text(stmt, 3);
    pair.response = column_text(stmt, 4);
    pair.seq = sqlite3_column_int64(stmt, 5);
    return pair;
}

std::optional<MemoryPair> find_pair(sqlite3* db, const std::string& uid,
                                    const std::string& pair_id) {
    Statement stmt(db, "SELECT pair_id,session_id,ts,prompt,response,seq FROM pairs "
                       "WHERE user_id=? AND pair_id=?");
    stmt.bind(1, uid);
    stmt.bind(2, pair_id);
    if (stmt.step() == SQLITE_ROW) return row_pair(stmt.get());
    return std::nullopt;
}

std::int64_t next_seq(sqlite3* db) {
    Statement stmt(db, "UPDATE counters SET value=value+1 WHERE name='seq' RETURNING value");
    if (stmt.step() != SQLITE_ROW) throw std::runtime_error("SQLite sequence counter missing");
    return sqlite3_column_int64(stmt.get(), 0);
}

bool ascii_alnum(unsigned char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9');
}

std::string lower_ascii(std::string value) {
    for (char& c : value) {
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    }
    return value;
}

std::string python_lower(const std::string& value);

std::vector<std::string> ascii_words(const std::string& text, std::size_t min_length) {
    std::vector<std::string> words;
    std::size_t start = 0;
    while (start < text.size()) {
        while (start < text.size() && !ascii_alnum(static_cast<unsigned char>(text[start]))) ++start;
        if (start >= text.size()) break;
        std::size_t end = start;
        while (end < text.size() && ascii_alnum(static_cast<unsigned char>(text[end]))) ++end;
        if (end - start >= min_length) words.push_back(lower_ascii(text.substr(start, end - start)));
        start = end;
    }
    return words;
}

std::string fts_query(const std::string& query) {
    std::unordered_set<std::string> seen;
    std::string expression;
    for (const std::string& word : ascii_words(query, 2)) {
        if (!seen.insert(word).second) continue;
        if (!expression.empty()) expression += " OR ";
        expression += '"' + word + '"';
        if (seen.size() >= 24) break;
    }
    return expression;
}

std::vector<MemoryPair> fts_search(sqlite3* db, const std::string& uid,
                                   const std::string& query, int limit) {
    const std::string match = fts_query(query);
    if (match.empty()) return {};
    Statement stmt(db, "SELECT p.pair_id,p.session_id,p.ts,p.prompt,p.response,p.seq,"
                       "bm25(pairs_fts) AS score FROM pairs_fts JOIN pairs p "
                       "ON p.rowid=pairs_fts.rowid WHERE pairs_fts MATCH ? "
                       "AND p.user_id=? ORDER BY score LIMIT ?");
    stmt.bind(1, match);
    stmt.bind(2, uid);
    stmt.bind(3, static_cast<std::int64_t>(limit));
    std::vector<MemoryPair> out;
    while (stmt.step() == SQLITE_ROW) out.push_back(row_pair(stmt.get()));
    return out;
}

std::vector<MemoryPair> subject_pairs(sqlite3* db, const std::string& uid,
                                      const std::string& subject_id) {
    Statement stmt(db, "SELECT p.pair_id,p.session_id,p.ts,p.prompt,p.response,p.seq "
                       "FROM links l JOIN pairs p ON p.user_id=l.user_id AND p.pair_id=l.pair_id "
                       "WHERE l.user_id=? AND l.subject_id=? ORDER BY p.ts,p.seq");
    stmt.bind(1, uid);
    stmt.bind(2, subject_id);
    std::vector<MemoryPair> out;
    while (stmt.step() == SQLITE_ROW) out.push_back(row_pair(stmt.get()));
    return out;
}

struct SubjectRow {
    std::string id;
    std::string subject;
    std::string description;
    int hits = 0;
};

std::vector<SubjectRow> subjects_search(sqlite3* db, const std::string& uid,
                                         const std::string& query, std::size_t limit) {
    const auto raw_words = ascii_words(query, 3);
    const std::set<std::string> words(raw_words.begin(), raw_words.end());
    Statement stmt(db, "SELECT subject_id,subject_text,description_text FROM subjects WHERE user_id=?");
    stmt.bind(1, uid);
    std::vector<SubjectRow> scored;
    while (stmt.step() == SQLITE_ROW) {
        SubjectRow row{column_text(stmt.get(), 0), column_text(stmt.get(), 1), column_text(stmt.get(), 2), 0};
        const std::string text = python_lower(row.subject + " " + row.description);
        for (const auto& word : words) {
            if (text.find(word) != std::string::npos) ++row.hits;
        }
        if (row.hits) scored.push_back(std::move(row));
    }
    std::stable_sort(scored.begin(), scored.end(), [](const SubjectRow& a, const SubjectRow& b) {
        return a.hits > b.hits;
    });
    if (scored.size() > limit) scored.resize(limit);
    return scored;
}

std::pair<std::uint32_t, std::size_t> utf8_point(const std::string& value, std::size_t at) {
    const unsigned char lead = static_cast<unsigned char>(value[at]);
    if (lead < 0x80) return {lead, 1};
    const std::size_t width = lead < 0xE0 ? 2 : lead < 0xF0 ? 3 : 4;
    if (at + width > value.size()) return {lead, 1};
    std::uint32_t point = lead & (width == 2 ? 0x1F : width == 3 ? 0x0F : 0x07);
    for (std::size_t i = 1; i < width; ++i) {
        const unsigned char next = static_cast<unsigned char>(value[at + i]);
        if ((next & 0xC0) != 0x80) return {lead, 1};
        point = (point << 6) | (next & 0x3F);
    }
    return {point, width};
}

void append_utf8(std::string& out, std::uint32_t point) {
    if (point < 0x80) {
        out.push_back(static_cast<char>(point));
    } else if (point < 0x800) {
        out.push_back(static_cast<char>(0xC0 | (point >> 6)));
        out.push_back(static_cast<char>(0x80 | (point & 0x3F)));
    } else if (point < 0x10000) {
        out.push_back(static_cast<char>(0xE0 | (point >> 12)));
        out.push_back(static_cast<char>(0x80 | ((point >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (point & 0x3F)));
    } else {
        out.push_back(static_cast<char>(0xF0 | (point >> 18)));
        out.push_back(static_cast<char>(0x80 | ((point >> 12) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | ((point >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (point & 0x3F)));
    }
}

std::string python_lower(const std::string& value) {
    // One-code-point lowercase mappings match glibc 2.39's
    // C.UTF-8 locale. U+0130 is its sole multi-code-point expansion.
    static const locale_t utf8_locale = newlocale(LC_CTYPE_MASK, "C.UTF-8", nullptr);
    if (!utf8_locale) throw std::runtime_error("C.UTF-8 locale is required for Unicode memory matching");
    std::string out;
    out.reserve(value.size());
    for (std::size_t at = 0; at < value.size();) {
        const auto [point, width] = utf8_point(value, at);
        if (point == 0x0130) out += "i\xCC\x87";
        else append_utf8(out, static_cast<std::uint32_t>(towlower_l(point, utf8_locale)));
        at += width;
    }
    return out;
}

bool python_space(std::uint32_t point) {
    return (point >= 0x09 && point <= 0x0D) || (point >= 0x1C && point <= 0x20) ||
           point == 0x85 || point == 0xA0 || point == 0x1680 ||
           (point >= 0x2000 && point <= 0x200A) || point == 0x2028 ||
           point == 0x2029 || point == 0x202F || point == 0x205F || point == 0x3000;
}

bool blank(const std::string& value) {
    for (std::size_t at = 0; at < value.size();) {
        const auto [point, width] = utf8_point(value, at);
        if (!python_space(point)) return false;
        at += width;
    }
    return true;
}

std::string trim_ascii(const std::string& value) {
    std::size_t first = std::string::npos, last = 0;
    for (std::size_t at = 0; at < value.size();) {
        const auto [point, width] = utf8_point(value, at);
        if (!python_space(point)) {
            if (first == std::string::npos) first = at;
            last = at + width;
        }
        at += width;
    }
    return first == std::string::npos ? "" : value.substr(first, last - first);
}

std::string py_string(const json& value) {
    if (value.is_string()) return value.get<std::string>();
    if (value.is_null()) return "None";
    if (value.is_boolean()) return value.get<bool>() ? "True" : "False";
    return value.dump();
}

bool truthy(const json& value) {
    if (value.is_null()) return false;
    if (value.is_boolean()) return value.get<bool>();
    if (value.is_number()) return value.get<double>() != 0.0;
    if (value.is_string()) return !value.get_ref<const std::string&>().empty();
    if (value.is_array() || value.is_object()) return !value.empty();
    return false;
}

json selected(const json& args, const char* first, const char* second = nullptr) {
    if (!args.is_object()) return "";
    auto it = args.find(first);
    if (it != args.end() && truthy(*it)) return *it;
    if (second != nullptr) {
        it = args.find(second);
        if (it != args.end() && truthy(*it)) return *it;
    }
    return "";
}

std::vector<std::string> queries(const json& raw) {
    std::vector<std::string> out;
    if (raw.is_string()) {
        const std::string value = raw.get<std::string>();
        if (!blank(value)) out.push_back(value);
    } else if (raw.is_array()) {
        for (const auto& item : raw) {
            const std::string value = py_string(item);
            if (!blank(value)) out.push_back(value);
        }
    }
    return out;
}

std::vector<std::string> ids_of(const json& raw) {
    std::vector<std::string> out;
    if (raw.is_array()) {
        for (const auto& item : raw) out.push_back(py_string(item));
    } else {
        out.push_back(py_string(raw));
    }
    return out;
}

// Return the first N UTF-8 code points, preserving their encoded bytes.
std::string prefix_chars(const std::string& value, std::size_t limit) {
    std::size_t pos = 0;
    std::size_t count = 0;
    while (pos < value.size() && count < limit) {
        const unsigned char c = static_cast<unsigned char>(value[pos]);
        const std::size_t width = (c < 0x80) ? 1 : (c < 0xE0) ? 2 : (c < 0xF0) ? 3 : 4;
        pos = std::min(value.size(), pos + width);
        ++count;
    }
    return value.substr(0, pos);
}

std::size_t char_count(const std::string& value) {
    std::size_t count = 0;
    for (unsigned char c : value) {
        if ((c & 0xC0) != 0x80) ++count;
    }
    return count;
}

std::string collapse_space(const std::string& value) {
    std::string out;
    bool gap = false;
    for (std::size_t at = 0; at < value.size();) {
        const auto [point, width] = utf8_point(value, at);
        if (python_space(point)) {
            gap = !out.empty();
        } else {
            if (gap) out.push_back(' ');
            out.append(value, at, width);
            gap = false;
        }
        at += width;
    }
    return out;
}

std::string snippet(const std::string& text, std::size_t limit = 220) {
    const std::string one_line = collapse_space(text);
    if (char_count(one_line) <= limit) return one_line;
    return trim_ascii(prefix_chars(one_line, limit)) + "…";
}

json shown_entry(const MemoryPair& pair, json fields) {
    if (pair.pair_id.rfind("saved-", 0) != 0) fields["pair_id"] = pair.pair_id;
    return fields;
}

json empty_note(const std::string& name, const std::string& field) {
    return "Tool error: " + name + " was called with an empty " + field +
           ", so this harness read no stored conversation for it. Send it again with " +
           field + " filled in.";
}

std::string required_string(const json& object, const char* field) {
    if (!object.is_object() || !object.contains(field) || !object.at(field).is_string()) {
        throw std::invalid_argument(std::string("seed requires string ") + field);
    }
    return object.at(field).get<std::string>();
}

std::string optional_seed_string(const json& object, const char* field) {
    if (!object.is_object()) throw std::invalid_argument("seed row must be an object");
    if (!object.contains(field)) return "";
    if (!object.at(field).is_string()) {
        throw std::invalid_argument(std::string("seed requires string ") + field);
    }
    return object.at(field).get<std::string>();
}

const json& array_field(const json& object, const char* field) {
    static const json empty = json::array();
    if (!object.contains(field)) return empty;
    const json& value = object.at(field);
    if (!value.is_array()) throw std::invalid_argument(std::string("seed requires array ") + field);
    return value;
}

bool valid_wave_string(const std::string& value) {
    const std::string text = trim_ascii(value);
    std::size_t at = 0;
    if (at < text.size() && (text[at] == '+' || text[at] == '-')) ++at;
    if (at == text.size() || text[at] < '0' || text[at] > '9') return false;
    ++at;
    while (at < text.size()) {
        if (text[at] >= '0' && text[at] <= '9') {
            ++at;
        } else if (text[at] == '_' && at + 1 < text.size() &&
                   text[at + 1] >= '0' && text[at + 1] <= '9') {
            at += 2;
        } else {
            break;
        }
    }
    if (at < text.size() && text[at] == '.') {
        ++at;
        if (at == text.size()) return false;
        while (at < text.size() && text[at] == '0') ++at;
    }
    return at == text.size();
}

void validate_seed_wave(const json& body) {
    if (!body.contains("wave") || body.at("wave").is_null()) return;
    const auto& wave = body.at("wave");
    if (wave.is_boolean() || wave.is_number_integer() || wave.is_number_unsigned()) return;
    if (wave.is_number_float()) {
        const double number = wave.get<double>();
        if (std::isfinite(number) && std::trunc(number) == number &&
            std::abs(number) < 0x1.0p63) return;
    } else if (wave.is_string() && valid_wave_string(wave.get<std::string>())) {
        return;
    }
    throw std::invalid_argument("seed requires integer wave");
}

}  // namespace

Store::Store(std::string db_path) {
    if (sqlite3_open_v2(db_path.c_str(), &db_, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX, nullptr) != SQLITE_OK) {
        const std::string detail = db_ ? sqlite3_errmsg(db_) : "open failed";
        if (db_) sqlite3_close(db_);
        db_ = nullptr;
        throw std::runtime_error("SQLite open: " + detail);
    }
    try {
        sqlite3_busy_timeout(db_, 5000);
        exec_sql(db_, kSchema);
    } catch (...) {
        sqlite3_close(db_);
        db_ = nullptr;
        throw;
    }
}

Store::~Store() {
    std::lock_guard lock(mutex_);
    if (db_) sqlite3_close(db_);
}

json Store::seed(const json& body) {
    if (!body.is_object()) throw std::invalid_argument("seed body must be an object");
    validate_seed_wave(body);
    std::string raw_user_id;
    if (body.contains("user_id") && !body.at("user_id").is_null()) {
        if (!body.at("user_id").is_string()) throw std::invalid_argument("seed requires string user_id");
        raw_user_id = body.at("user_id").get<std::string>();
    }
    const std::string uid = normalize_user_id(raw_user_id);
    const json& pairs = array_field(body, "pairs");
    const json& subjects = array_field(body, "subjects");
    const json& links = array_field(body, "links");
    std::lock_guard lock(mutex_);
    Transaction transaction(db_);
    Statement select(db_, "SELECT seq FROM pairs WHERE user_id=? AND pair_id=?");
    Statement remove(db_, "DELETE FROM pairs WHERE user_id=? AND pair_id=?");
    Statement insert(db_, "INSERT INTO pairs(user_id,pair_id,session_id,ts,prompt,response,seq) "
                          "VALUES(?,?,?,?,?,?,?)");
    Statement subject_stmt(db_, "INSERT OR REPLACE INTO subjects(user_id,subject_id,subject_text,description_text) "
                                "VALUES(?,?,?,?)");
    Statement link_stmt(db_, "INSERT OR IGNORE INTO links(user_id,subject_id,pair_id) VALUES(?,?,?)");
    for (const auto& item : pairs) {
        const std::string pair_id = required_string(item, "pair_id");
        select.bind(1, uid);
        select.bind(2, pair_id);
        const bool existing = select.step() == SQLITE_ROW;
        const std::int64_t seq = existing ? sqlite3_column_int64(select.get(), 0) : next_seq(db_);
        select.reset();
        if (existing) {
            remove.bind(1, uid);
            remove.bind(2, pair_id);
            remove.done();
            remove.reset();
        }
        insert.bind(1, uid);
        insert.bind(2, pair_id);
        insert.bind(3, optional_seed_string(item, "session_id"));
        insert.bind(4, optional_seed_string(item, "timestamp"));
        insert.bind(5, optional_seed_string(item, "prompt"));
        insert.bind(6, optional_seed_string(item, "response"));
        insert.bind(7, seq);
        insert.done();
        insert.reset();
    }
    for (const auto& item : subjects) {
        subject_stmt.bind(1, uid);
        subject_stmt.bind(2, required_string(item, "id"));
        subject_stmt.bind(3, optional_seed_string(item, "subject_text"));
        subject_stmt.bind(4, optional_seed_string(item, "description_text"));
        subject_stmt.done();
        subject_stmt.reset();
    }
    for (const auto& item : links) {
        link_stmt.bind(1, uid);
        link_stmt.bind(2, required_string(item, "subject_id"));
        link_stmt.bind(3, required_string(item, "pair_id"));
        link_stmt.done();
        link_stmt.reset();
    }
    transaction.commit();
    return {{"pairs", pairs.size()}, {"subjects", subjects.size()}, {"links", links.size()}};
}

std::vector<MemoryPair> Store::all_pairs(const std::string& user_id) {
    const std::string uid = normalize_user_id(user_id);
    std::lock_guard lock(mutex_);
    Statement stmt(db_, "SELECT pair_id,session_id,ts,prompt,response,seq FROM pairs "
                        "WHERE user_id=? ORDER BY ts,seq");
    stmt.bind(1, uid);
    std::vector<MemoryPair> out;
    while (stmt.step() == SQLITE_ROW) out.push_back(row_pair(stmt.get()));
    return out;
}

std::optional<MemoryPair> Store::get_pair(const std::string& user_id,
                                           const std::string& pair_id) {
    const std::string uid = normalize_user_id(user_id);
    std::lock_guard lock(mutex_);
    return find_pair(db_, uid, pair_id);
}

std::unordered_map<std::string, std::vector<float>> Store::vectors(
    const std::string& user_id, const std::vector<std::string>& hashes) {
    const std::string uid = normalize_user_id(user_id);
    std::lock_guard lock(mutex_);
    auto& cached = vector_cache_[uid];
    std::unordered_map<std::string, std::vector<float>> out;
    Statement stmt(db_, "SELECT v FROM vectors WHERE user_id=? AND h=?");
    for (const auto& hash : hashes) {
        if (auto it = cached.find(hash); it != cached.end()) {
            out[hash] = it->second;
            continue;
        }
        stmt.bind(1, uid);
        stmt.bind(2, hash);
        if (stmt.step() == SQLITE_ROW) {
            const int bytes = sqlite3_column_bytes(stmt.get(), 0);
            if (bytes < 0 || bytes % static_cast<int>(sizeof(float)) != 0) {
                throw std::runtime_error("stored embedding vector blob has invalid size");
            }
            std::vector<float> values(static_cast<std::size_t>(bytes) / sizeof(float));
            if (bytes > 0) std::memcpy(values.data(), sqlite3_column_blob(stmt.get(), 0), static_cast<std::size_t>(bytes));
            cached[hash] = values;
            out[hash] = std::move(values);
        }
        stmt.reset();
    }
    return out;
}

void Store::put_vectors(const std::string& user_id,
                        const std::unordered_map<std::string, std::vector<float>>& vectors) {
    if (vectors.empty()) return;
    const std::string uid = normalize_user_id(user_id);
    std::lock_guard lock(mutex_);
    Transaction transaction(db_);
    Statement stmt(db_, "INSERT OR REPLACE INTO vectors(user_id,h,v) VALUES(?,?,?)");
    for (const auto& [hash, values] : vectors) {
        stmt.bind(1, uid);
        stmt.bind(2, hash);
        stmt.bind_blob(3, values);
        stmt.done();
        stmt.reset();
    }
    transaction.commit();
    auto& cached = vector_cache_[uid];
    for (const auto& [hash, values] : vectors) cached[hash] = values;
}

json Store::local_tool(const std::string& user_id, const std::string& name,
                       const json& args) {
    const std::string uid = normalize_user_id(user_id);
    std::lock_guard lock(mutex_);
    if (name == "search_memories") {
        const auto wanted = queries(selected(args, "queries", "query"));
        if (wanted.empty()) return empty_note(name, "queries");
        json memories = json::array();
        std::unordered_set<std::string> seen;
        for (const auto& query : wanted) {
            for (const auto& pair : fts_search(db_, uid, query, 8)) {
                if (!seen.insert(pair.pair_id).second) continue;
                memories.push_back(shown_entry(pair, {{"timestamp", pair.timestamp},
                    {"session_id", pair.session_id},
                    {"text", snippet(pair.prompt + " || " + pair.response, 700)}}));
            }
        }
        if (memories.empty()) return {{"memories", json::array()}, {"served_by", kProvenance},
                                      {"note", kNoSearchMatches}};
        if (memories.size() > 12) memories.erase(memories.begin() + 12, memories.end());
        return {{"memories", memories}, {"served_by", kProvenance}, {"note", kSearchIdsNote}};
    }
    if (name == "search_subjects") {
        const auto wanted = queries(selected(args, "queries", "query"));
        if (wanted.empty()) return empty_note(name, "queries");
        json subjects = json::array();
        std::unordered_map<std::string, std::size_t> positions;
        for (const auto& query : wanted) {
            for (const auto& subject : subjects_search(db_, uid, query, 8)) {
                json entry = {{"id", subject.id}, {"name", subject.subject},
                              {"description", subject.description}};
                auto [it, inserted] = positions.emplace(subject.id, subjects.size());
                if (inserted) subjects.push_back(std::move(entry));
                else subjects[it->second] = std::move(entry);
            }
        }
        return {{"subjects", subjects}, {"served_by", kProvenance}};
    }
    if (name == "fetch_memories") {
        json raw = selected(args, "pairIds", "pair_ids");
        if (raw.is_null() || (raw.is_string() && raw.get<std::string>().empty())) raw = json::array();
        const auto ids = ids_of(raw);
        if (std::none_of(ids.begin(), ids.end(), [](const std::string& id) { return !blank(id); })) {
            return empty_note(name, "pairIds");
        }
        json memories = json::array();
        for (const auto& id : ids) {
            if (auto pair = find_pair(db_, uid, id)) {
                memories.push_back(shown_entry(*pair, {{"timestamp", pair->timestamp},
                    {"session_id", pair->session_id}, {"prompt", pair->prompt},
                    {"response", pair->response}}));
            }
        }
        return {{"memories", memories}, {"served_by", kProvenance}};
    }
    if (name == "search_memories_in_subjects") {
        const std::string subject_id = py_string(selected(args, "subject_id"));
        if (blank(subject_id)) return empty_note(name, "subject_id");
        auto pairs = subject_pairs(db_, uid, subject_id);
        const auto wanted = queries(selected(args, "queries", "query"));
        if (!wanted.empty()) {
            std::vector<MemoryPair> filtered;
            for (const auto& pair : pairs) {
                const std::string haystack = python_lower(pair.prompt + " " + pair.response);
                if (std::any_of(wanted.begin(), wanted.end(), [&](const std::string& query) {
                        return haystack.find(python_lower(query)) != std::string::npos;
                    })) filtered.push_back(pair);
            }
            if (!filtered.empty()) pairs = std::move(filtered);
        }
        json memories = json::array();
        for (std::size_t i = 0; i < pairs.size() && i < 16; ++i) {
            const auto& pair = pairs[i];
            memories.push_back({{"pair_id", pair.pair_id}, {"timestamp", pair.timestamp},
                                {"summary", snippet(pair.prompt + " || " + pair.response)}});
        }
        return {{"memories", memories}, {"served_by", kProvenance}};
    }
    return "Tool error: unknown memory tool " + name;
}

std::vector<std::string> Store::unheld_ids(const std::string& user_id,
                                            const std::string& name,
                                            const json& args) {
    const std::string uid = normalize_user_id(user_id);
    std::lock_guard lock(mutex_);
    if (name == "fetch_memories") {
        json raw;
        if (args.is_object()) {
            if (args.contains("pairIds")) raw = args.at("pairIds");
            else if (args.contains("pair_ids")) raw = args.at("pair_ids");
        }
        const std::vector<std::string> ids = raw.is_null() ? std::vector<std::string>{} : ids_of(raw);
        std::vector<std::string> unheld;
        for (const auto& id : ids) {
            if (id.rfind("saved-", 0) == 0 || !find_pair(db_, uid, id)) unheld.push_back(id);
        }
        return unheld;
    }
    if (name == "search_memories_in_subjects") {
        std::string subject_id;
        if (args.is_object() && args.contains("subject_id") && !args.at("subject_id").is_null()) {
            subject_id = py_string(args.at("subject_id"));
        }
        Statement stmt(db_, "SELECT 1 FROM subjects WHERE user_id=? AND subject_id=?");
        stmt.bind(1, uid);
        stmt.bind(2, subject_id);
        return stmt.step() == SQLITE_ROW ? std::vector<std::string>{} : std::vector<std::string>{subject_id};
    }
    if (args.is_object() && args.contains("pair_id") && args.at("pair_id").is_string()) {
        const std::string pair_id = args.at("pair_id").get<std::string>();
        if (!blank(pair_id)) {
            if (pair_id.rfind("saved-", 0) == 0 || !find_pair(db_, uid, pair_id)) return {pair_id};
        }
    }
    return {};
}

std::vector<std::string> Store::memory_hits(const std::string& user_id,
                                            const std::string& name,
                                            const json& args) {
    const std::string uid = normalize_user_id(user_id);
    std::lock_guard lock(mutex_);
    std::vector<std::string> hits;
    if (name == "search_memories") {
        for (const auto& query : queries(selected(args, "queries", "query"))) {
            for (const auto& pair : fts_search(db_, uid, query, 8)) hits.push_back(pair.pair_id);
        }
    } else if (name == "fetch_memories") {
        json raw = selected(args, "pairIds", "pair_ids");
        if (raw.is_null() || (raw.is_string() && raw.get<std::string>().empty())) raw = json::array();
        for (const auto& id : ids_of(raw)) {
            if (auto pair = find_pair(db_, uid, id)) hits.push_back(pair->pair_id);
        }
    } else if (name == "search_memories_in_subjects") {
        const std::string subject_id = py_string(selected(args, "subject_id"));
        for (const auto& pair : subject_pairs(db_, uid, subject_id)) hits.push_back(pair.pair_id);
    }
    return hits;
}

void Store::mirror_save(const std::string& user_id, const std::string& content) {
    if (blank(content)) return;
    std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
    SHA256(reinterpret_cast<const unsigned char*>(content.data()), content.size(), digest.data());
    std::ostringstream hex;
    hex << std::hex << std::setfill('0');
    for (std::size_t i = 0; i < 8; ++i) hex << std::setw(2) << static_cast<int>(digest[i]);
    const std::string pair_id = "saved-" + hex.str();
    const std::string uid = normalize_user_id(user_id);
    std::lock_guard lock(mutex_);
    if (find_pair(db_, uid, pair_id)) return;
    std::time_t now = std::time(nullptr);
    std::tm utc{};
    gmtime_r(&now, &utc);
    char stamp[32]{};
    std::strftime(stamp, sizeof(stamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
    Transaction transaction(db_);
    Statement insert(db_, "INSERT INTO pairs(user_id,pair_id,session_id,ts,prompt,response,seq) "
                          "VALUES(?,?,'',?,?,'',?)");
    insert.bind(1, uid);
    insert.bind(2, pair_id);
    insert.bind(3, std::string(stamp));
    insert.bind(4, content);
    insert.bind(5, next_seq(db_));
    insert.done();
    transaction.commit();
}

void Store::mirror_update(const std::string& user_id, const std::string& pair_id,
                          const std::string& content) {
    if (blank(content)) return;
    const std::string uid = normalize_user_id(user_id);
    std::lock_guard lock(mutex_);
    const auto old = find_pair(db_, uid, pair_id);
    if (!old) return;
    Transaction transaction(db_);
    Statement remove(db_, "DELETE FROM pairs WHERE user_id=? AND pair_id=?");
    remove.bind(1, uid);
    remove.bind(2, pair_id);
    remove.done();
    Statement insert(db_, "INSERT INTO pairs(user_id,pair_id,session_id,ts,prompt,response,seq) "
                          "VALUES(?,?,?,?,?,'',?)");
    insert.bind(1, uid);
    insert.bind(2, pair_id);
    insert.bind(3, old->session_id);
    insert.bind(4, old->timestamp);
    insert.bind(5, content);
    insert.bind(6, old->seq);
    insert.done();
    transaction.commit();
}

}  // namespace ditto
