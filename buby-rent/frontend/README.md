# Welcome to your Lovable project

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Open your project in the [Lovable editor](https://lovable.dev) and keep building.

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: connect the project to GitHub and every change made in Lovable is committed straight to your repository.
- **Full ownership**: this code is yours. Push to your repository and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Bun and Node.js 22 or newer.

```sh
cd buby-rent/frontend
bun install --frozen-lockfile
bun run dev
```

The frontend talks to FastAPI using `VITE_API_URL` (defaults to `http://localhost:8000`). For Supabase Auth, also set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`; only the publishable key belongs in browser builds.

## Built with

- TanStack Start
- TypeScript
- React
- Tailwind CSS
