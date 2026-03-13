# Integration Rules (e-КТРМ)

## Allowed integrations in MVP
- Keycloak:
  - identity and OIDC flows;
  - realm/client/roles/users bootstrap в локальном Docker окружении.
- PostgreSQL:
  - основная доменная БД.
- Redis:
  - Celery broker/result backend и realtime support.
- MinIO:
  - объектное хранилище вложений и сгенерированных PDF.
- Applicant BIN lookup:
  - backend-mediated GBD UL lookup by `BIN`;
  - backend-mediated Kompra `IIN -> FIO` enrichment for applicant leader fields;
  - only when configured through `.env`, without exposing source URLs or tokens to frontend.

## Forbidden integrations in MVP
- НУЦ РК и реальная ЭЦП.
- Внешние государственные реестры.
- Внешние e-mail/SMS провайдеры.
- Любые неутвержденные внешние API.

## Integration behavior constraints
- Все внешние зависимости должны быть конфигурационными (`.env`), без hardcode endpoint/keys.
- Applicant lookup integrations must be called only from backend:
  - frontend may call only internal runtime endpoints;
  - Kompra token must never be shipped to browser runtime config.
- Смена Keycloak должна выполняться сменой конфигурации, без изменения кода.
- Если структура ролей/claims внешнего Keycloak отличается:
  - запрещено самовольно придумывать mapping;
  - требуется явное уточнение от пользователя.

## File and storage contract
- Пользовательские и системные файлы хранятся в MinIO.
- Разрешенные upload форматы: pdf/doc/docx/xls/xlsx/jpg/jpeg/png.
- Рекомендуемый лимит: до 25 MB на файл.
- Повторный upload заменяет активный файл в слоте, прежняя запись хранится исторически/soft-delete.

## Notification and realtime contract
- Канал уведомлений MVP: только in-app.
- Доставка обновлений: WebSocket; fallback через refresh допустим.

## BPMN and analytics references
- Для проверки согласованности workflow используются:
  - `.agentkit/_temp/order_3.1.jpg`
  - `.agentkit/_temp/order_4.1.jpg`
  - `.agentkit/_temp/order_4.2.jpg`
  - `.agentkit/_temp/order_4.3.jpg`
  - `.agentkit/_temp/order_5.1.jpg`
  - `.agentkit/_temp/order_5.2.jpg`
  - `.agentkit/_temp/order_5.3.jpg`
