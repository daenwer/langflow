## 🚀 Быстрый старт

Поднимаем два изолированных окружения Langflow:

- **PROM** — production-подобный контур без фронтенда (backend-only).
- **IFT** — испытательный контур с полноценным UI.

### PROM (backend-only)

```bash
cd two-envs/prom
docker-compose up -d --build
docker exec -it langflow-prom-ollama ollama pull llama3.2
```

### IFT (c UI)

```bash
cd two-envs/ift
docker-compose up -d --build
docker exec -it langflow-ift-ollama ollama pull llama3.2
```

## 📍 Полезные ссылки

1. **PROM Langflow API (backend-only)**: http://localhost:7860/docs
2. **PROM Ollama API**: http://localhost:11434/api/tags

3. **IFT Langflow UI (frontend)**: http://localhost:7861
4. **IFT Langflow API (frontend)**: http://localhost:7861/docs
5. **IFT Ollama API**: http://localhost:11435/api/tags

## 📖 Использование API

### 1. Готовим flow в IFT
- Пример создания flow: https://youtu.be/kFEMtax1yd4?si=ydRmbpzuJ0-S1jLJ
- Работай в UI: http://localhost:7861  
- Открой нужный flow и скопируй `flow_id` из адресной строки, например  
  `http://localhost:7861/flow/<flow_id>/folder/b6c23b0d-5c03-41ab-9c6f-bc7a05420256`

### 2. Экспортируем JSON flow из IFT
- Перейди в Swagger IFT: http://localhost:7861/docs#/Flows/read_flow_api_v1_flows__flow_id__get  
- Вставь `flow_id`, вызови ручку и скачай JSON.

### 3. Импортируем flow в PROM
- Открой Swagger PROM: http://localhost:7860/docs#/Flows/create_flow_api_v1_flows__post  
- Вставь JSON из шага 2, но **удали** поля:
  - `"id": "48e47bca-ab3f-4233-b6e5-0df62ac79759"`
  - `"user_id": "c301f97a-75a0-4da2-b268-fd7c6c25935f"`
  - `"folder_id": "b6c23b0d-5c03-41ab-9c6f-bc7a05420256"`
- Отправь запрос и сохрани новый `flow_id`, который вернёт PROM.

### 4. Запускаем задачу в PROM
- Используй ручку `POST /api/v1/build/{flow_id}/flow`: http://localhost:7860/docs#/Chat/build_flow_api_v1_build__flow_id__flow_post  
- Вставь новый `flow_id` и тело запроса:
  ```json
  {
    "inputs": {
      "input_value": "Какой фрукт самый полезный?"
    }
  }
  ```
- В ответе появится `job_id`.

### 5. Получаем результат
- Для просмотра событий и финального ответа перейди в: http://localhost:7860/docs#/Chat/get_build_events_api_v1_build__job_id__events_get  
- Подставь `job_id`, чтобы увидеть поток сообщений и итог.

## 🗄 Подключение к базам

Подключайся через DBeaver, выбрав SQLite и указав путь к файлу:

- IFT: `/<path>/langflow/two-envs/ift/data/ift/langflow_ift.db`
- PROM: `/<path>/langflow/two-envs/prom/data/prom/langflow_prom.db`
