-- add_coding_questions_table.sql
create table if not exists public.coding_questions (
    id text primary key,
    skill text not null,
    role_tags text[] default '{}',
    difficulty int not null default 3,
    title text not null,
    prompt text not null,
    function_name text not null,
    function_signature text not null,
    starter_code text not null,
    test_cases jsonb not null,
    expected_concepts text[] default '{}',
    created_at timestamptz not null default now()
);

