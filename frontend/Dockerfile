# Bun — matches local toolchain (bun.lock) and our verified `bun run build`.
FROM oven/bun:1 AS base
WORKDIR /app

# Install deps first (cached layer).
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# App source (self-hosted font under app/fonts → no build-time font fetch).
COPY . .

# NEXT_PUBLIC_* is baked into the client bundle at BUILD time. Pass the deployed
# API base as a build arg; defaults to localhost:8000 for local container builds.
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ARG NEXT_PUBLIC_DEFAULT_TARGET
ENV NEXT_PUBLIC_DEFAULT_TARGET=${NEXT_PUBLIC_DEFAULT_TARGET}

RUN bun run build

# Cloud Run injects $PORT; Next listens on it.
ENV PORT=3000
EXPOSE 3000
CMD ["sh", "-c", "bunx next start -H 0.0.0.0 -p ${PORT}"]
