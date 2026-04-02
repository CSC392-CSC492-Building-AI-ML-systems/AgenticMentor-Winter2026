-- Persist project-scoped LLM settings (mode, model, verified flags).
-- Custom API keys are NOT stored here — only server memory (see llm_custom_key_store).

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS llm_settings JSONB NOT NULL DEFAULT '{
    "mode": "default",
    "model": null,
    "verified": false,
    "verified_at": null
  }'::jsonb;
