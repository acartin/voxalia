# FreePBX

FreePBX is the web GUI used to configure Asterisk for Voxalia voice operations:
trunks, numbers, extensions, inbound routes, queues, IVR, recordings, and PBX
settings.

The local compose uses `escomputers/freepbx:17-nofail2ban` with a dedicated
MariaDB container. FreePBX manages Asterisk internally.
