-- Run this in Supabase SQL Editor (Project -> SQL Editor -> New query)
-- This adds the target_role column needed for the role-selector feature.
-- Safe to run even if you already ran supabase_schema.sql before this existed.

alter table public.conversations
    add column if not exists target_role text;
