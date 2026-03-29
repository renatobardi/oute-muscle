# Multi-stage Dockerfile for SvelteKit with adapter-node

# Stage 1: install dependencies
FROM node:20-alpine AS deps

WORKDIR /app

COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci

# Stage 2: build the SvelteKit app
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ .
RUN npm run build
RUN npm prune --omit=dev

# Stage 3: production runtime
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOST=0.0.0.0

# Copy built output and production node_modules
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["node", "build"]
