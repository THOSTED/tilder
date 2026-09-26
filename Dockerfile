# tilder's image: Python, an SVG renderer that uses the theme's fonts for
# the icons and the share preview (woff2_decompress: the renderer shapes
# text with HarfBuzz, which reads TTF, not WOFF2), and the generator itself
# at this version, under /tilder. Everything else is the standard library.
#
#   docker run --rm -v "$PWD:/site" -v "$PWD/public:/out" ghcr.io/thosted/tilder \
#     python3 -B /tilder/build.py --root /site --out /out
FROM python:3-alpine
RUN apk add --no-cache rsvg-convert fontconfig woff2
ARG VERSION=dev
ENV TILDER_VERSION=$VERSION
COPY build.py defaults.toml LICENSE /tilder/
COPY src/ /tilder/src/
COPY types/ /tilder/types/
WORKDIR /site
CMD ["python3", "-B", "/tilder/build.py", "--root", "/site", "--out", "/out", "--watch"]
