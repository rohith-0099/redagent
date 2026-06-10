# Bun — matches local toolchain (bun.lock) and our verified `bun run build`.
FROM oven/bun:1 AS base
WORKDIR /app

# Install deps first (cached layer).
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# App source (self-hosted font under app/fonts → no build-time font fetch).
COPY . .

# NEXT_PUBLIC_* is baked into the client bundle at BUILD time. Defaults are the
# deployed Cloud Run URLs (public client values) so `gcloud run deploy --source`
# bakes them without --build-arg; override via --build-arg for other envs. Local
# `bun dev` / `bun run build` ignore the Dockerfile, so local stays on localhost.
ARG NEXT_PUBLIC_API_BASE=https://redagent-api-563626673936.us-central1.run.app
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ARG NEXT_PUBLIC_DEFAULT_TARGET=https://redagent-victim-563626673936.us-central1.run.app
ENV NEXT_PUBLIC_DEFAULT_TARGET=${NEXT_PUBLIC_DEFAULT_TARGET}

RUN bun run build

# Cloud Run injects $PORT; Next listens on it.
ENV PORT=3000
EXPOSE 3000
CMD ["sh", "-c", "bunx next start -H 0.0.0.0 -p ${PORT}"]
