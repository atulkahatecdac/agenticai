-- One Empire — Supabase: instagram_tokens table
-- Run in Supabase SQL Editor

create table if not exists instagram_tokens (
  id                  uuid primary key default gen_random_uuid(),
  member_email        text unique not null,

  -- Instagram user identifiers
  instagram_id        text,
  instagram_username  text,
  instagram_name      text,

  -- Page/business account linked to the Instagram account
  page_id             text,
  page_name           text,

  -- OAuth tokens
  -- short-lived token from initial auth (1h), then exchanged for long-lived (60d)
  access_token        text not null,
  token_type          text default 'bearer',
  expires_in          integer,           -- seconds from token_stored_at
  token_stored_at     text,              -- ISO 8601 timestamp string
  token_expires_at    text,              -- ISO 8601 timestamp string

  is_active           boolean default true,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

-- Keep updated_at current on every row change
create or replace function update_instagram_tokens_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_instagram_tokens_updated_at on instagram_tokens;
create trigger trg_instagram_tokens_updated_at
  before update on instagram_tokens
  for each row execute procedure update_instagram_tokens_updated_at();

-- Allow n8n service role full access
alter table instagram_tokens enable row level security;

create policy "Service role full access"
  on instagram_tokens
  for all
  using (true)
  with check (true);
