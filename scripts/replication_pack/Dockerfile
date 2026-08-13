# TradeArena deterministic replication pack v1 (CPU-only, no API keys).
#
# Build and run from the pack root:
#   docker build -t tradearena-replication .
#   docker run --rm -v "$PWD/outputs:/pack/outputs" tradearena-replication --environment-class linux
#
# The replication report appears in ./outputs/ on the host.
FROM python:3.12-slim

LABEL org.opencontainers.image.title="TradeArena deterministic replication pack v1" \
      org.opencontainers.image.description="Zero-key deterministic anchor replication for the TradeArena benchmark (v0.3 protocol)." \
      org.opencontainers.image.licenses="MIT"

WORKDIR /pack
COPY . /pack

# Standard library only: nothing to pip install.
ENTRYPOINT ["python", "replicate.py"]
CMD ["--environment-class", "linux"]
