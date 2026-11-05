# Optional local teaching renderer. MinerU runs natively on macOS for Metal/MPS.
# Build explicitly, record the resulting image ID, then disable network at run.
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config libcairo2-dev libpango1.0-dev ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir manim==0.21.0 numpy==2.2.6 matplotlib==3.10.8
WORKDIR /work
