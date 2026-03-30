# Stage 1: Build Rust ZK circuits
FROM rust:1.77-slim AS zk-builder

WORKDIR /build
COPY zk_circuits/ ./zk_circuits/

RUN apt-get update && apt-get install -y python3-dev && rm -rf /var/lib/apt/lists/*
RUN cargo install maturin
RUN cd zk_circuits && maturin build --release

# Stage 2: Python runtime
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

# Copy built ZK wheel from stage 1
COPY --from=zk-builder /build/zk_circuits/target/wheels/*.whl /tmp/
RUN pip install /tmp/*.whl 2>/dev/null || echo "ZK wheel not yet available — skipping"

ENTRYPOINT ["python"]
