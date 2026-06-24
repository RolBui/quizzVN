# QuizVN Monorepo

Source chinh cua repo duoc sap xep theo huong monorepo:

```text
apps/
  api/         # FastAPI backend
  admin-web/   # Vite + React admin panel
packages/      # Cho shared package ve sau
docker-compose.yml
```

## Chay local

Backend:

```powershell
cd "c:\backend api\apps\api"
..\..\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host localhost --port 8000
```

Admin web:

```powershell
cd "c:\backend api\apps\admin-web"
npm install
npm run dev
```

Docker:

```powershell
cd "c:\backend api"
docker compose up --build
```

## Ghi chu

- `apps/api` va `apps/admin-web` la layout monorepo moi de tiep tuc phat trien.
- Cac folder cu o root van con ton tai tam thoi do Windows dang khoa mot so file luc di chuyen. Sau khi ban verify moi thu chay on, co the xoa thu cong cac ban sao cu o root.
- `packages/` duoc de san cho shared client, shared types hoac ui-kit ve sau.
- Cau hinh xac thuc email nam tai `docs/email-verification.md`.
