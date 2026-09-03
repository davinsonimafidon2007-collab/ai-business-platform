# deps: capa cacheable — solo se reconstruye si cambia el lockfile.
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# builder: compila el servidor Next.js en modo standalone (BUILD_TARGET=docker
# en next.config.ts). El export Capacitor (BUILD_TARGET=capacitor) se hace en
# CI/host, no aquí.
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Las variables NEXT_PUBLIC_* se inlinean en el bundle EN BUILD TIME: hay que
# pasarlas como --build-arg (compose las toma de .env vía build.args).
ARG NEXT_PUBLIC_API_URL=http://localhost:8001
ARG NEXT_PUBLIC_AUTH_DISABLED=false
ARG NEXT_PUBLIC_APP_VERSION
ENV NEXT_TELEMETRY_DISABLED=1 \
    BUILD_TARGET=docker \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_AUTH_DISABLED=${NEXT_PUBLIC_AUTH_DISABLED} \
    NEXT_PUBLIC_APP_VERSION=${NEXT_PUBLIC_APP_VERSION}
RUN npm run build

# runner: imagen mínima con el bundle standalone (sin node_modules completo).
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder --chown=node:node /app/public ./public

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:3000/', (r) => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
