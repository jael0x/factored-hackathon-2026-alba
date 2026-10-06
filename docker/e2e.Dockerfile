ARG PLAYWRIGHT_VERSION=1.63.0

FROM mcr.microsoft.com/playwright:v${PLAYWRIGHT_VERSION}-noble@sha256:eff16c30e6f3f4af0a03fa4b706120d5e9b0891c344a27d64559aff5900a4a27

ARG PLAYWRIGHT_VERSION
ENV NPM_CONFIG_UPDATE_NOTIFIER=false

WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
# The image carries the browsers of one Playwright version; a lockfile on another would fail only at launch.
RUN test "$(npx playwright --version)" = "Version ${PLAYWRIGHT_VERSION}"

COPY web /app/web
COPY api/fixtures /app/api/fixtures

CMD ["npx", "playwright", "test"]
