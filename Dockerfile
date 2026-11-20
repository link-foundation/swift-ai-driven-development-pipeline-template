FROM swift:6.4.1-noble@sha256:6304481cf2717966b7ba175162e397ea2f2cc3161909f2b2a5cf40036079a0f7 AS build
WORKDIR /package
COPY Package* ./
COPY Sources Sources
COPY Tests Tests
RUN set -eu; \
    if [ -f Package.resolved ]; then set -- --disable-automatic-resolution; else set --; fi; \
    swift build -c release -j 2 --product swift-pipeline-example "$@"; \
    cp "$(swift build -c release --show-bin-path)/swift-pipeline-example" /swift-pipeline-example

FROM swift:6.4.1-noble-slim@sha256:503a11af64a22b3f80335cbe7d7189f67689bbe026c482ae17e1ece453f31cd5
COPY --from=build /swift-pipeline-example /usr/local/bin/
USER 65532:65532
ENTRYPOINT ["/usr/local/bin/swift-pipeline-example"]
