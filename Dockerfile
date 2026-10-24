# tilder's image: Python, an SVG renderer that uses the theme's fonts for
# the icons and the share preview (woff2_decompress: the renderer shapes
# text with HarfBuzz, which reads TTF, not WOFF2), and the generator itself
# at this version, under /tilder. Everything else is the standard library.
# The reference docs of this version ride along in /tilder/docs/ (theme.md,
# the theme contract; types.md, markdown.md, languages.md, seo.md), so a
# theme can be checked against the builder it is built with:
#
#   docker run --rm ghcr.io/thosted/tilder cat /tilder/docs/theme.md
#
#   docker run --rm -v "$PWD:/site" -v "$PWD/public:/out" ghcr.io/thosted/tilder \
#     python3 -B /tilder/build.py --root /site --out /out
#
# Two images from this file. The default, lean one has no diagram renderer:
# a ```mermaid block is shown as its source, with its description. The
# `mermaid` target adds the Mermaid CLI (mmdc) and a headless Chromium, and
# draws them (docs/markdown.md, "Diagrams"); it is published with a
# `-mermaid` suffix on every tag (1.5.0-mermaid, 1-mermaid, latest-mermaid):
#
#   docker build -t tilder .                      # lean
#   docker build --target mermaid -t tilder .     # with diagrams
FROM python:3-alpine AS base
RUN apk add --no-cache rsvg-convert fontconfig woff2
ARG VERSION=dev
ENV TILDER_VERSION=$VERSION
COPY build.py defaults.toml LICENSE /tilder/
COPY src/ /tilder/src/
COPY types/ /tilder/types/
COPY docs/*.md /tilder/docs/
WORKDIR /site
CMD ["python3", "-B", "/tilder/build.py", "--root", "/site", "--out", "/out", "--watch"]

# The Mermaid CLI on Alpine's own Chromium: puppeteer downloads none.
FROM base AS mermaid
ARG MERMAID_CLI=12.0.0
ENV PUPPETEER_SKIP_DOWNLOAD=1 \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser
RUN apk add --no-cache chromium nodejs npm \
 && npm install --global --omit=dev --no-audit --no-fund "@mermaid-js/mermaid-cli@$MERMAID_CLI" \
 && npm cache clean --force \
 && apk del npm \
 && find /usr/local/lib/node_modules \( -name '*.map' -o -name '*.d.ts' -o -name '*.md' \) -delete
# Chromium writes its profile and crash database under HOME: the build may
# run as any user (docker run --user), whose home may not exist.
ENV HOME=/tmp

# The default target, last: the lean image.
FROM base
