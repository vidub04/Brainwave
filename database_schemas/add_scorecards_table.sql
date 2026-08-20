-- Run this in Supabase SQL Editor (Project -> SQL Editor -> New query)
-- Adds a dedicated scorecards table so past interview results can be
-- queried and charted over time, instead of being trapped inside a
-- single message's text.

create table if not exists public.scorecards (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    conversation_id uuid not null references public.conversations(id) on delete cascade,
    target_role text,
    technical_knowledge int,
    problem_solving int,
    core_cs_fundamentals int,
    project_knowledge int,
    communication int,
    confidence int,
    leadership int,
    behavioral_skills int,
    strengths jsonb,
    areas_for_improvement jsonb,
    study_topics jsonb,
    recommendation text,
    created_at timestamptz not null default now()
);

create index if not exists idx_scorecards_user on public.scorecards(user_id);
create index if not exists idx_scorecards_conversation on public.scorecards(conversation_id);

alter table public.scorecards enable row level security;

create policy "Users manage their own scorecards"
    on public.scorecards for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
