-- ============================================================================
-- AgenticMentor Database Schema - Add Per-User Ownership
-- ============================================================================
-- Migration: 002_add_owner_uid.sql
-- Date: March 19, 2026
--
-- Adds owner_uid columns used to enforce per-user access control.
-- This migration is backwards-compatible: existing rows will have NULL owner_uid
-- until you backfill them.
-- ============================================================================

ALTER TABLE IF EXISTS projects
    ADD COLUMN IF NOT EXISTS owner_uid TEXT;

ALTER TABLE IF EXISTS conversation_messages
    ADD COLUMN IF NOT EXISTS owner_uid TEXT;

ALTER TABLE IF EXISTS mockups
    ADD COLUMN IF NOT EXISTS owner_uid TEXT;

CREATE INDEX IF NOT EXISTS idx_projects_owner_uid ON projects(owner_uid);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_owner_uid ON conversation_messages(owner_uid);
CREATE INDEX IF NOT EXISTS idx_mockups_owner_uid ON mockups(owner_uid);

-- Optional hardening (recommended once you’ve backfilled):
-- ALTER TABLE projects ALTER COLUMN owner_uid SET NOT NULL;
-- ALTER TABLE conversation_messages ALTER COLUMN owner_uid SET NOT NULL;
-- ALTER TABLE mockups ALTER COLUMN owner_uid SET NOT NULL;

