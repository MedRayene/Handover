FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    git sudo ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global http.postBuffer 524288000 && \
    git config --global http.lowSpeedLimit 0 && \
    git config --global http.lowSpeedTime 999999

WORKDIR /build
RUN git clone --depth 1 https://github.com/OPENAIRINTERFACE/openairinterface5g.git
WORKDIR /build/openairinterface5g
RUN git fetch --depth 1 origin 0dab3bb6a1d230791bb8b26ad20e0fdcc16471fc && \
    git checkout FETCH_HEAD

WORKDIR /build/openairinterface5g/cmake_targets
RUN ./build_oai -I --gNB --nrUE
RUN rm -rf ran_build
RUN ./build_oai --ninja --nrUE --gNB --build-lib telnetsrv

FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsctp1 zlib1g libssl3 libconfig9 libyaml-cpp0.8 libreadline8 \
    tini iproute2 iputils-ping telnet \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/oai-ran
COPY --from=builder /build/openairinterface5g/cmake_targets/ran_build/build/nr-softmodem .
COPY --from=builder /build/openairinterface5g/cmake_targets/ran_build/build/nr-uesoftmodem .
COPY --from=builder /build/openairinterface5g/cmake_targets/ran_build/build/*.so .

ENV LD_LIBRARY_PATH=/opt/oai-ran
ENTRYPOINT ["/usr/bin/tini", "-v", "--"]
