1. Создать папку `data` и выдать права:
   ```bash
   mkdir -p data
   sudo chown -R 1000:1000 data
   ```
   (при запуске это выполняет контейнер `langflow-init`)

2. Создать файл `.env` (для демонстарии достаточно скопировать из `.env.example`).
   Флаг `LANGFLOW_BACKEND_ONLY=false/true` включает или выключает UI.

3. Сервис доступен на `http://<host>:7860` (`/flow` — UI, `/docs` — Swagger).

4. Запуск:
   ```bash
   docker-compose up -d --build --remove-orphans
   ```
   Логи: `docker logs -f langflow-app`. SQLite: `data/langflow.db`
