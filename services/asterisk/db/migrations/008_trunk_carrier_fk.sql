-- Relate SIP trunks to the global carrier catalog.

alter table asterisk.sip_trunks
  add column if not exists carrier_key text;

update asterisk.sip_trunks st
set carrier_key = c.carrier_key
from asterisk.carriers c
where st.carrier_key is null
  and lower(st.carrier_name) = lower(c.display_name);

update asterisk.sip_trunks
set carrier_key = 'freepbx-lab'
where carrier_key is null
  and trunk_key = 'lab-freepbx'
  and exists (select 1 from asterisk.carriers where carrier_key = 'freepbx-lab');

alter table asterisk.sip_trunks
  drop constraint if exists sip_trunks_carrier_fk;

alter table asterisk.sip_trunks
  add constraint sip_trunks_carrier_fk
  foreign key (carrier_key)
  references asterisk.carriers(carrier_key)
  on update cascade
  on delete restrict;
