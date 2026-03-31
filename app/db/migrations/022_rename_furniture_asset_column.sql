alter table if exists furniture
drop column assets_url,
    add column assets_id BIGINT;


alter table furniture add constraint fk_assets_table foreign key(assets_id) references asset(id);
