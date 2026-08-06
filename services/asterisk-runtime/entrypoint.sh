#!/usr/bin/env bash
set -euo pipefail

ami_username="${VOXALIA_ASTERISK_RUNTIME_AMI_USERNAME:-voxalia_provisioner}"
ami_password="${VOXALIA_ASTERISK_RUNTIME_AMI_PASSWORD:-}"

if [ -z "$ami_password" ]; then
  printf 'VOXALIA_ASTERISK_RUNTIME_AMI_PASSWORD is required\n' >&2
  exit 1
fi

mkdir -p /etc/asterisk/voxalia /var/lib/asterisk /var/log/asterisk /var/spool/asterisk /var/run/asterisk
touch \
  /etc/asterisk/voxalia/pjsip_voxalia.conf \
  /etc/asterisk/voxalia/extensions_voxalia.conf \
  /etc/asterisk/voxalia/queues_voxalia.conf

cat > /etc/asterisk/manager.conf <<EOF
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0
displayconnects = no

[${ami_username}]
secret = ${ami_password}
deny = 0.0.0.0/0.0.0.0
permit = 172.16.0.0/255.240.0.0
permit = 127.0.0.1/255.255.255.255
read = system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan,originate,message
write = system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan,originate,message
writetimeout = 5000
EOF

chown -R asterisk:asterisk /etc/asterisk /var/lib/asterisk /var/log/asterisk /var/spool/asterisk /var/run/asterisk

exec asterisk -f
