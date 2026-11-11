# syntax=docker/dockerfile:1
FROM golang:1.25-bookworm AS build
ARG UPSTREAM_COMMIT=68c69e693877f6351b960b755784852f55aa854f
WORKDIR /src
RUN git init . \
    && git remote add origin https://github.com/Mau2rice0/Open-Apple-Cache.git \
    && git fetch --depth=1 origin "${UPSTREAM_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${UPSTREAM_COMMIT}"
COPY patches/ /patches/
RUN git apply --check /patches/0001-ignore-origin-cache-control.patch \
    && git apply /patches/0001-ignore-origin-cache-control.patch
RUN go test ./... && go vet ./... \
    && CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/open-apple-cache .

FROM python:3.13-slim-bookworm AS runtime
ARG UPSTREAM_COMMIT=68c69e693877f6351b960b755784852f55aa854f
LABEL org.opencontainers.image.source="https://github.com/Mau2rice0/Open-Apple-Cache" \
      org.opencontainers.image.revision="${UPSTREAM_COMMIT}" \
      io.github.palbiez.patchset="ignore-origin-cache-control-v1"
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates openssl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 applecache \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin applecache
COPY --from=build /out/open-apple-cache /usr/local/bin/open-apple-cache
COPY --from=build /src/config.example.json /opt/open-apple-cache/config.example.json
COPY --from=build /src/scripts /opt/open-apple-cache/scripts
COPY --from=build /src/mac-helper /opt/open-apple-cache/mac-helper
COPY --from=build /src/docs /opt/open-apple-cache/docs
COPY --from=build /src/LICENSE /opt/open-apple-cache/LICENSE
COPY bootstrap.py healthcheck.py /opt/open-apple-cache/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8080 8443
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["python3", "/opt/open-apple-cache/healthcheck.py"]
ENTRYPOINT ["/usr/local/bin/open-apple-cache"]
CMD ["-config", "/etc/open-apple-cache/config.json"]
