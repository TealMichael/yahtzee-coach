-- Yahtzee Coach v43B Phase 2K.11
-- Player-created retro avatar profile. Safe to run more than once.

alter table public.players
    add column if not exists avatar_config jsonb not null default '{"hair":"spiky","outfit":"blue_tank","skin":"warm","accessory":"white_headband","shoes":"blue"}'::jsonb;

alter table public.players
    add column if not exists avatar_setup_complete boolean not null default false;

-- Keep the stored value small and object-shaped. The app owns the allowed option list.
do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'players_avatar_config_object'
          and conrelid = 'public.players'::regclass
    ) then
        alter table public.players
            add constraint players_avatar_config_object
            check (jsonb_typeof(avatar_config) = 'object');
    end if;
end $$;
