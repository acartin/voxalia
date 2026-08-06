FROM ubuntu:22.04

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends asterisk asterisk-doc tini ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY config/ /etc/asterisk/
COPY entrypoint.sh /usr/local/bin/voxalia-asterisk-runtime-entrypoint.sh

RUN chmod +x /usr/local/bin/voxalia-asterisk-runtime-entrypoint.sh \
    && mkdir -p /etc/asterisk/voxalia /var/lib/asterisk /var/log/asterisk /var/spool/asterisk /var/run/asterisk \
    && chown -R asterisk:asterisk /etc/asterisk /var/lib/asterisk /var/log/asterisk /var/spool/asterisk /var/run/asterisk

EXPOSE 5060/udp 5038/tcp 8088/tcp

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/voxalia-asterisk-runtime-entrypoint.sh"]
