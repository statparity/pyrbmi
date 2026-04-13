# R Validation Base Image for pyrbmi
# Uses r2u (CRAN-as-apt) for pre-compiled R packages
# Build time: ~2 min vs ~15 min from source

FROM ubuntu:24.04

ARG R_VERSION=4.4.1
ARG RBMI_VERSION=1.3.2
ARG RSTAN_VERSION=2.32.6

LABEL org.opencontainers.image.title="pyrbmi-r-base"
LABEL org.opencontainers.image.description="Base image for R validation of pyrbmi"
LABEL org.opencontainers.image.version="r${R_VERSION}-rbmi${RBMI_VERSION}"
LABEL org.opencontainers.image.source="https://github.com/statparity/pyrbmi"

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    software-properties-common \
    dirmngr \
    build-essential \
    libssl-dev \
    libcurl4-openssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    libbz2-dev \
    liblzma-dev \
    libpcre2-dev \
    libblas-dev \
    liblapack-dev \
    gfortran \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Add r2u repository (CRAN-as-apt)
RUN wget -qO- https://raw.githubusercontent.com/eddelbuettel/r2u/main/inst/scripts/add-r2u-to-sources.sh | bash -s -- focal

# Install R and r2u packages
RUN apt-get update && apt-get install -y \
    r-base-core \
    r-base-dev \
    r-cran-rstan \
    r-cran-stanheaders \
    && rm -rf /var/lib/apt/lists/*

# Install rbmi from CRAN (r2u doesn't have it yet, install from source but with pre-built deps)
RUN R -e "install.packages('rbmi', repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores())"

# Install Python 3.11 and uv
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set Python defaults
ENV PYTHONUNBUFFERED=1
ENV UV_PYTHON=python3.11

# Install rpy2 with pre-built R
RUN pip3 install --no-cache-dir rpy2>=3.5

# Verify installations
RUN R -e "packageVersion('rbmi')" && \
    R -e "packageVersion('rstan')" && \
    python3 -c "import rpy2; print(f'rpy2: {rpy2.__version__}')" && \
    R --version

# Set working directory
WORKDIR /workspace

# Default command
CMD ["R"]
