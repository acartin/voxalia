-- Voxalia auth grants.
-- Keeps the application role operational and lets the declared admin role
-- inspect/manage the Voxalia database from tools such as pgAdmin.

grant usage, create on schema public to voxalia_app;
grant usage, create on schema public to voxalia_admin;

grant all privileges on all tables in schema public to voxalia_app;
grant all privileges on all sequences in schema public to voxalia_app;
grant execute on all functions in schema public to voxalia_app;

grant all privileges on all tables in schema public to voxalia_admin;
grant all privileges on all sequences in schema public to voxalia_admin;
grant execute on all functions in schema public to voxalia_admin;

alter default privileges in schema public
  grant all privileges on tables to voxalia_app;

alter default privileges in schema public
  grant all privileges on sequences to voxalia_app;

alter default privileges in schema public
  grant execute on functions to voxalia_app;

alter default privileges in schema public
  grant all privileges on tables to voxalia_admin;

alter default privileges in schema public
  grant all privileges on sequences to voxalia_admin;

alter default privileges in schema public
  grant execute on functions to voxalia_admin;
