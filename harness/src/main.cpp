#include <cstdlib>
#include <exception>
#include <iostream>
#include <string>
#include <algorithm>

#include <httplib.h>

#include "agent.hpp"

namespace {

void json_reply(httplib::Response& response, const ditto::json& body, int status = 200) {
    response.status = status;
    response.set_content(body.dump(), "application/json; charset=utf-8");
}

}  // namespace

int main() {
    try {
        ditto::AgentConfig config = ditto::AgentConfig::from_env();
        ditto::Store store(config.db_path);
        ditto::Agent agent(config, store);
        httplib::Server server;
        server.set_payload_max_length(64U * 1024U * 1024U);
        server.set_read_timeout(300, 0);
        server.set_write_timeout(300, 0);

        server.Get("/health", [](const httplib::Request&, httplib::Response& response) {
            json_reply(response, {{"status", "ok"}});
        });
        server.Post("/seed", [&agent](const httplib::Request& request, httplib::Response& response) {
            try {
                auto body = ditto::json::parse(request.body);
                if (!body.is_object()) throw std::invalid_argument("seed body must be an object");
                json_reply(response, agent.seed(body));
            } catch (const ditto::json::exception& error) {
                json_reply(response, {{"error", error.what()}}, 400);
            } catch (const std::invalid_argument& error) {
                json_reply(response, {{"error", error.what()}}, 400);
            } catch (const std::exception& error) {
                std::cerr << "seed failure: " << error.what() << '\n';
                json_reply(response, {{"error", "seed failed"}}, 500);
            }
        });
        server.Post("/run", [&agent](const httplib::Request& request, httplib::Response& response) {
            ditto::RunRequest parsed;
            try {
                auto body = ditto::json::parse(request.body);
                parsed = ditto::parse_run_request(body);
            } catch (const ditto::json::exception& error) {
                std::string detail = "malformed run request: " + std::string(error.what());
                json_reply(response, {{"error", detail.substr(0, 500)}}, 400);
                return;
            } catch (const std::invalid_argument& error) {
                std::string detail = "malformed run request: " + std::string(error.what());
                json_reply(response, {{"error", detail.substr(0, 500)}}, 400);
                return;
            }
            try {
                json_reply(response, agent.run(parsed));
            } catch (const std::exception& error) {
                std::cerr << "run failure: " << error.what() << '\n';
                std::string detail = "run request failed: " + std::string(error.what());
                json_reply(response, {{"error", detail.substr(0, 500)}}, 500);
            }
        });

        int port = 8080;
        if (const char* raw = std::getenv("PORT")) {
            try { port = std::clamp(std::stoi(raw), 1, 65535); }
            catch (const std::exception&) { std::cerr << "invalid PORT\n"; return EXIT_FAILURE; }
        }
        std::cerr << "Ditto C++ server listening on 0.0.0.0:" << port << '\n';
        if (!server.listen("0.0.0.0", port)) {
            std::cerr << "failed to listen on port " << port << '\n';
            return EXIT_FAILURE;
        }
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "startup failure: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
