# FreePBX

FreePBX is the web GUI used to configure Asterisk for Voxalia voice operations:
trunks, numbers, extensions, inbound routes, queues, IVR, recordings, and PBX
settings.

The local compose uses `escomputers/freepbx:17-nofail2ban` with a dedicated
MariaDB container. FreePBX manages Asterisk internally.

## Required Modules

The FreePBX container starts through `entrypoint-with-modules.sh`, which runs the
image's original entrypoint and then ensures required GUI modules are installed.

Currently required:

- `ringgroups`: visible call fan-out for testing inbound calls against multiple
  extensions without hiding dialplan in Asterisk custom files.
