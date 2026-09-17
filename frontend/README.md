# TrustMind frontend

Next.js (TypeScript) check-in UI. It does **not** call OpenAI. It `POST`s to the FastAPI backend.

Full project README, RQ, and Table 3: [`../README.md`](../README.md).

```bash
npm install
# .env.local: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run dev
```

Open [http://localhost:3000/analyse](http://localhost:3000/analyse).
