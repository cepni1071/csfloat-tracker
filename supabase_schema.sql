-- CSFloat Tracker — Supabase tablo şeması
-- Supabase Dashboard > SQL Editor > New query > buraya yapıştır > Run.

-- Takip edilen skinler
create table if not exists skins (
    id               bigint generated always as identity primary key,
    market_hash_name text not null,
    target_price     double precision,
    last_price       double precision,
    float_min        double precision default 0,
    float_max        double precision default 1,
    image_url        text,
    global_price     double precision,
    added_at         timestamptz default now(),
    unique (market_hash_name, float_min, float_max)
);

-- Uygulama ayarları (ör. notify_email)
create table if not exists settings (
    key   text primary key,
    value text
);
