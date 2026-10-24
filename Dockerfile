# tilder's image: Python, D2 for diagrams, an SVG renderer that uses the
# theme's fonts for the icons and the share preview (woff2_decompress: the
# renderer shapes text with HarfBuzz, which reads TTF, not WOFF2), and the
# generator itself at this version, under /tilder. Everything else is the standard library.
# The reference docs of this version ride along in /tilder/docs/ (theme.md,
# the theme contract; types.md, markdown.md, languages.md, seo.md), so a
# theme can be checked against the builder it is built with:
#
#   docker run --rm ghcr.io/thosted/tilder cat /tilder/docs/theme.md
#
#   docker run --rm -v "$PWD:/site" -v "$PWD/public:/out" ghcr.io/thosted/tilder \
#     python3 -B /tilder/build.py --root /site --out /out
#
# Diagrams (```d2 blocks, docs/markdown.md) are drawn by D2, one static
# binary, pinned and checked against its release checksum.
FROM alpine:3 AS d2
ARG D2_VERSION=0.9.0
ARG TARGETARCH=amd64
RUN apk add --no-cache curl \
 && case "$TARGETARCH" in \
      amd64) sum=5669ddc46b99e942cc96078f4a4e36d5e62103348f4c05179ede27802fdd87a9 ;; \
      arm64) sum=ac2c028697199479acb321db1e3d68caee9f2ba492ed73caa3cd13f3829bf913 ;; \
      *) echo "no D2 checksum for $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && curl -fsSL -o /d2.tgz "https://github.com/terrastruct/d2/releases/download/v$D2_VERSION/d2-v$D2_VERSION-linux-$TARGETARCH.tar.gz" \
 && echo "$sum  /d2.tgz" | sha256sum -c - \
 && tar -xzf /d2.tgz -C / \
 && mv "/d2-v$D2_VERSION/bin/d2" /usr/local/bin/d2 \
 && mkdir -p /licenses/d2 && mv "/d2-v$D2_VERSION/LICENSE.txt" "/d2-v$D2_VERSION/THIRD_PARTY_NOTICES.txt" /licenses/d2/

FROM python:3-alpine
RUN apk add --no-cache rsvg-convert fontconfig woff2
COPY --from=d2 /usr/local/bin/d2 /usr/local/bin/d2
COPY --from=d2 /licenses/d2/ /usr/share/licenses/d2/
ARG VERSION=dev
ENV TILDER_VERSION=$VERSION
COPY build.py defaults.toml LICENSE /tilder/
COPY src/ /tilder/src/
COPY types/ /tilder/types/
COPY docs/*.md /tilder/docs/
WORKDIR /site
CMD ["python3", "-B", "/tilder/build.py", "--root", "/site", "--out", "/out", "--watch"]
