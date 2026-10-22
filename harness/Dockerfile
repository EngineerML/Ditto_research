FROM ubuntu:24.04 AS build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates cmake g++ make libsqlite3-dev libcurl4-openssl-dev \
    libssl-dev libcpp-httplib-dev nlohmann-json3-dev libicu-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY CMakeLists.txt ./
COPY include ./include
COPY src ./src
COPY tests ./tests
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build --parallel 2 && build/store_smoke && build/local_helpers_smoke && build/short_smoke && build/output_smoke && build/network_smoke && build/embedding_smoke && build/agent_control_smoke && build/retrieval_smoke

FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libsqlite3-0 libcurl4t64 libssl3t64 libcpp-httplib0.14t64 libicu74 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /src/build/ditto_cpp /app/ditto_cpp
COPY assets /app/assets
USER 65532:65532
EXPOSE 8080
CMD ["/app/ditto_cpp"]
