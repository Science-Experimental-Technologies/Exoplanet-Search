# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="SXS — SCIX Exoplanet Search" \
      org.opencontainers.image.description="Kepler transit recovery and independent candidate vetting. No confirmed discoveries." \
      org.opencontainers.image.source="https://github.com/Science-Experimental-Technologies/Exoplanet-Search" \
      org.opencontainers.image.url="https://science-experimental-technologies.github.io/Exoplanet-Search/" \
      org.opencontainers.image.authors="Rasya Andrean / Science Experimental Technologies <scix.official@gmail.com>" \
      org.opencontainers.image.licenses="LicenseRef-SXS-Source-Available-Commercial-1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    TF_CPP_MIN_LOG_LEVEL=2 \
    HOME=/home/sxs

# Keep dependency installation cacheable, and include CPU TensorFlow for baseline training.
COPY requirements.txt /tmp/sxs-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/sxs-requirements.txt \
    && python -m pip check \
    && groupadd --gid 10001 sxs \
    && useradd --uid 10001 --gid sxs --create-home sxs

WORKDIR /opt/sxs
# Explicit inputs avoid shipping local data, credentials, models, or unpublished reports.
COPY --chown=sxs:sxs src/ ./src/
COPY --chown=sxs:sxs configs/ ./configs/
COPY --chown=sxs:sxs LICENSE NOTICE COMMERCIAL_USE.md DISCLAIMER.md README.md ./
RUN mkdir -p data models reports /opt/.sxs-locks \
    && chown sxs:sxs /opt/sxs data models reports /opt/.sxs-locks

USER 10001:10001
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--help"]
