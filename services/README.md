# Services

Executable Voxalia processes live here. The initial architecture should stay as
a modular monolith or a few deployable processes until contracts and operations
justify splitting further.

- `web-api`: authoritative BFF for web apps, auth, menu and lightweight web data.
- `asterisk`: independent Asterisk control-plane/provisioning service. It owns
  Asterisk desired/applied state and must not be mixed into `web-api`.
