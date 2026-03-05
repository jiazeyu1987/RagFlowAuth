# ONLYOFFICE Docs Docker Integration

## 1. Deploy ONLYOFFICE Document Server

```bash
docker run -d \
  --name onlyoffice-document-server \
  -p 8082:80 \
  --restart=always \
  -e JWT_ENABLED=true \
  -e JWT_SECRET=change_me_onlyoffice_secret \
  onlyoffice/documentserver
```

Or use repo compose profile:

```bash
docker compose -f docker/docker-compose.yml --profile onlyoffice up -d
```

## 2. Backend Environment Variables

Add the following to backend runtime env (or `.env`):

```env
ONLYOFFICE_ENABLED=true
ONLYOFFICE_SERVER_URL=http://127.0.0.1:8082
ONLYOFFICE_JWT_SECRET=change_me_onlyoffice_secret
ONLYOFFICE_PUBLIC_API_BASE_URL=http://127.0.0.1:8001
ONLYOFFICE_FILE_TOKEN_TTL_SECONDS=300
```

If using docker compose, copy `docker/.env.example` to `docker/.env` and edit values.

Notes:
- `ONLYOFFICE_SERVER_URL` is the Document Server address reachable by users' browser.
- `ONLYOFFICE_PUBLIC_API_BASE_URL` is the Auth backend public address reachable by Document Server.
- `ONLYOFFICE_JWT_SECRET` must match `JWT_SECRET` in the Document Server container.

## 3. Supported Online Preview Formats (ONLYOFFICE path)

- `.xls`
- `.ppt`
- `.pptx`

## 4. Validation Checklist

1. Open Document Browser and click `查看` for `.xls/.ppt/.pptx`.
2. Confirm preview opens in ONLYOFFICE viewer.
3. Verify non-download accounts cannot download/print in preview mode when backend permission is denied.
