-- Run this in Supabase SQL Editor (Project -> SQL Editor -> New query)

-- Auth is handled entirely by Supabase's built-in `auth.users` table.
-- We only need our own app tables, keyed by auth.uid().

-- One row per interview session
create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text default 'Interview',
    created_at timestamptz not null default now()
);

-- Every chat turn (user + bot)
create table if not exists public.messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.conversations(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null check (role in ('user', 'bot')),
    content text not null,
    created_at timestamptz not null default now()
);

-- Parsed resume data per user (one active resume at a time, keep history if you want)
create table if not exists public.resumes (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    filename text,
    raw_text text,
    structured jsonb,           -- {name, skills, experience, education, ...}
    created_at timestamptz not null default now()
);

-- Indexes for common lookups
create index if not exists idx_conversations_user on public.conversations(user_id);
create index if not exists idx_messages_conversation on public.messages(conversation_id);
create index if not exists idx_messages_user on public.messages(user_id);
create index if not exists idx_resumes_user on public.resumes(user_id);

-- Row Level Security: users can only touch their own rows.
-- (Our FastAPI backend uses the service_role key, which bypasses RLS,
--  but we enable it anyway in case you ever query directly from the client.)
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.resumes enable row level security;

create policy "Users manage their own conversations"
    on public.conversations for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users manage their own messages"
    on public.messages for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users manage their own resumes"
    on public.resumes for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
