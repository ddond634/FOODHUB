Vercel Deployment Instructions
=============================

This project serves a static frontend located in the `frontend/` folder. The included `vercel.json` routes all incoming requests to files under `frontend/`.

Two ways to deploy:

1) Quick deploy with Vercel CLI (recommended for local testing)

Install the Vercel CLI (if not installed):

```bash
npm i -g vercel
```

Login and deploy (run from the `FinalProject/qwerty` folder):

```bash
cd FinalProject/qwerty
vercel login
vercel --prod
```

2) GitHub integration (recommended for production / CI)

- Push the `FinalProject/qwerty` repo (or this folder) to GitHub.
- In the Vercel Dashboard, create a new Project and import the repository.
- Set the Root Directory to the repository path that contains `vercel.json` (for example: `/` if `vercel.json` is at repo root, or `FinalProject/qwerty` if importing the repository root).
- No build command is required for a pure static site. Vercel will use `@vercel/static` to serve the `frontend/` folder.

Environment variables
---------------------

If you need the frontend to talk to Supabase or other services, set the following environment variables in the Vercel Project settings:

- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_ANON_KEY` — anon/public key
- Any other keys defined in your `.env` that the frontend needs at runtime

Notes
-----
- If you prefer to build with a bundler (Vite, Next.js, etc.), add the appropriate `build` command and use `@vercel/static-build` instead.
- The `vercel.json` included routes requests to static files in `frontend/` to preserve existing paths.
