-- ResQ-AI operational inventory.
-- Run this migration in Supabase SQL Editor before enabling persistent inventory.
-- Only operator-verified records should be uploaded here. Do not import sample CSVs.
create table if not exists public.resource_inventory (
    record_id text primary key,
    record jsonb not null,
    updated_at timestamptz not null default now()
);

create table if not exists public.hospital_inventory (
    record_id text primary key,
    record jsonb not null,
    updated_at timestamptz not null default now()
);

create table if not exists public.shelter_inventory (
    record_id text primary key,
    record jsonb not null,
    updated_at timestamptz not null default now()
);

create index if not exists resource_inventory_updated_at_idx
    on public.resource_inventory (updated_at desc);
create index if not exists hospital_inventory_updated_at_idx
    on public.hospital_inventory (updated_at desc);
create index if not exists shelter_inventory_updated_at_idx
    on public.shelter_inventory (updated_at desc);
