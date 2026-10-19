-- Adds the structured snapshots needed to restore submitted reports after refresh.
-- Run this once in Supabase SQL Editor for the existing public.incidents table.
ALTER TABLE public.incidents
    ADD COLUMN IF NOT EXISTS incident_code text,
    ADD COLUMN IF NOT EXISTS incident_data jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS analysis_data jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS assignment_data jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS incidents_incident_code_unique
    ON public.incidents (incident_code)
    WHERE incident_code IS NOT NULL;
