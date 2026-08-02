FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git build-essential meson ninja-build cmake pkg-config flex bison \
    libsctp-dev libgnutls28-dev libgcrypt-dev libssl-dev libidn11-dev \
    libmongoc-dev libbson-dev libyaml-dev libnghttp2-dev libmicrohttpd-dev \
    libtalloc-dev libcurl4-openssl-dev libmaxminddb-dev \
    iproute2 iputils-ping net-tools tcpdump vim curl ca-certificates gnupg && \
    rm -rf /var/lib/apt/lists/*

# MongoDB official repo for Ubuntu 22.04
RUN curl -fsSL https://pgp.mongodb.com/server-7.0.asc | \
    gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor && \
    echo "deb [ arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" \
    > /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && apt-get install -y mongodb-org && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /open5gs

RUN git clone https://github.com/open5gs/open5gs.git /open5gs && \
    meson build --prefix=/usr && \
    ninja -C build

# --------------------------------------------------
# Install Prometheus
# --------------------------------------------------

WORKDIR /opt

RUN mkdir -p /opt/prometheus && \
    curl -L https://github.com/prometheus/prometheus/releases/download/v3.5.0/prometheus-3.5.0.linux-amd64.tar.gz \
    -o /tmp/prometheus.tar.gz && \
    tar -xzf /tmp/prometheus.tar.gz -C /opt/prometheus && \
    rm /tmp/prometheus.tar.gz


RUN mkdir -p /data/db /logs /lab/configs

CMD ["bash", "-lc", "mongod --bind_ip 127.0.0.1 --dbpath /data/db --fork --logpath /logs/mongodb.log && sleep infinity"]
