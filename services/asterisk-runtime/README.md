# Voxalia Asterisk Runtime

Direct Asterisk runtime managed by Voxalia.

This container is intentionally separate from `services/asterisk`:

- `services/asterisk` is the API/provisioner and reads Voxalia PostgreSQL.
- `services/asterisk-runtime` runs Asterisk and loads generated config files.
- FreePBX remains a lab/reference container and is not part of the Voxalia
  apply-config path.

Local compose mounts the `voxalia-asterisk-rendered` volume at:

```text
/etc/asterisk/voxalia
```

The runtime includes these generated files:

```text
/etc/asterisk/voxalia/pjsip_voxalia.conf
/etc/asterisk/voxalia/extensions_voxalia.conf
/etc/asterisk/voxalia/queues_voxalia.conf
```

`voxalia-asterisk-api` reloads the runtime through AMI after `Apply Config`.

Local ports:

```text
5060/udp       SIP
5038/tcp       AMI
8087->8088/tcp Asterisk HTTP/WebSocket
13000-13100    RTP
```

Do not put SIP credentials, tenant business rules or generated tenant dialplan
in the static files in this directory. Tenant-owned runtime state must be
rendered from Voxalia database state by the Asterisk API/provisioner.
