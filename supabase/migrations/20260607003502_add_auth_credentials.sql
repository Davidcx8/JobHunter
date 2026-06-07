-- Dynamic backend auth credentials for in-app password changes.
-- This table is only for the server-side service role; browser roles must not read it.
CREATE TABLE IF NOT EXISTS public.auth_credentials (
    id TEXT PRIMARY KEY DEFAULT 'primary',
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.auth_credentials ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.auth_credentials FROM anon;
REVOKE ALL ON TABLE public.auth_credentials FROM authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.auth_credentials TO service_role;
