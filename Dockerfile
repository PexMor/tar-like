FROM python:3
WORKDIR /app
COPY tar_like/ /app/tar_like/
ENV PYTHONPATH=/app HOME=/data/rw
# RUN pip install --only-binary :all: --no-cache-dir --upgrade py-lz4framed requests
RUN pip install --no-cache-dir --upgrade py-lz4framed requests pyyaml
