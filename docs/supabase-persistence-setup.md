# Supabase incident persistence setup

The app stores operator-submitted incident snapshots in Supabase Postgres. The Streamlit server connects using a server-side `DATABASE_URL`; the connection string must never be committed to GitHub or shared in chat.

## 1. Update the existing table

In Supabase Dashboard → SQL Editor → Create a new snippet, run the SQL in `supabase/migrations/202610200001_incident_persistence.sql`.

This adds JSON snapshots for the incident, NLP analysis, and recommended assignment. The app needs these columns to reconstruct the command queue after refresh.

## 2. Add the connection string to Streamlit secrets

1. In Supabase, open **Connect** and choose a PostgreSQL connection string. Prefer the **Session pooler** if the direct connection is not reachable from the deployment.
2. Open the Streamlit Community Cloud dashboard for this app, open the app menu, and select **Settings → Secrets** (sometimes shown as **Edit secrets**).
3. Add the following TOML entry, replacing the placeholder locally in the dashboard only:

```toml
DATABASE_URL = "postgresql://YOUR_DATABASE_USER:YOUR_DATABASE_PASSWORD@YOUR_DATABASE_HOST:5432/postgres?sslmode=require"
```

Use the exact host, port, username, and password shown by Supabase. Do not paste the real connection string into GitHub, source files, or chat.

## 3. Verify persistence

1. Wait for Streamlit to restart after saving secrets.
2. Submit a non-sensitive test incident in the app.
3. Confirm the row appears in Supabase → Table Editor → `public.incidents`.
4. Refresh the app and check that the same incident remains in Command Center.

If the report form says the database save failed, check that the SQL migration ran and that the secret contains the complete connection string.

## Prototype security note

The database credential is server-side, but the app's incident form is publicly accessible. Anyone who can open the app may submit reports, and the Command Center displays saved reports. Treat these as unverified prototype reports only; do not store private personal information or rely on this app for real emergency dispatch without adding authentication, abuse controls, and an operational review process.
