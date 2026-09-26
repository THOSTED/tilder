# The builder's image: Python, and an SVG renderer that uses the theme's
# fonts, for the icons and the share preview (woff2_decompress: the renderer
# shapes text with HarfBuzz, which reads TTF, not WOFF2). Everything else in
# the build is the standard library.
FROM python:3-alpine
RUN apk add --no-cache rsvg-convert fontconfig woff2
WORKDIR /repo
