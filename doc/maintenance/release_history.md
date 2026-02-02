# 发布记录（自动追加）

> 说明：由 `tool/maintenance/tool.py` 自动写入，用于追溯发布/数据同步/回滚历史。

- 2026-02-02 19:35:54 | LOCAL->TEST | server=172.30.30.58 | version=20260202_193430
  - server: 172.30.30.58
  - backend_image: ragflowauth-backend:20260202_193430
  - frontend_image: ragflowauth-frontend:20260202_193430
  - compose_path: 
  - env_path: 
  - docker-compose.yml sha256: 
  - .env sha256:
- 2026-02-02 19:38:45 | TEST->PROD(IMAGE) | server=172.30.30.57 | version=20260202_193631
  - server: 172.30.30.57
  - backend_image: ragflowauth-backend:20260202_193430
  - frontend_image: ragflowauth-frontend:20260202_193430
  - compose_path: 
  - env_path: 
  - docker-compose.yml sha256: 
  - .env sha256:
- 2026-02-02 20:41:47 | TEST->PROD(DATA) | server=172.30.30.57 | version=20260202_204004
  - sync auth.db + ragflow volumes
- 2026-02-02 22:04:36 | LOCAL->TEST | server=172.30.30.58 | version=20260202_220328
  - server: 172.30.30.58
  - backend_image: ragflowauth-backend:20260202_220328
  - frontend_image: ragflowauth-frontend:20260202_220328
  - compose_path: 
  - env_path: 
  - docker-compose.yml sha256: 
  - .env sha256:
