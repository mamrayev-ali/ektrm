# Security Rules (e-КТРМ)

## Auth model (mandatory)
- Identity provider: Keycloak (локально в Docker на этапе MVP).
- Frontend: OIDC Authorization Code + PKCE.
- Backend: валидация bearer JWT на каждом защищенном endpoint.

## Backend token validation checklist
- Проверка подписи JWT по JWKS.
- Проверка `iss`.
- Проверка `aud` (ожидаемый клиент).
- Проверка срока токена и корректной обработки refresh/session timeout.
- Извлечение ролей и organization-binding из claims/доменного профиля.

## RBAC and data access
- Backend — единственная точка enforcement access rules.
- Frontend guards — только UX-слой, не security-граница.
- `Applicant` всегда ограничен своими объектами.
- `OPS` имеет полный рабочий доступ по scope MVP.

## Sensitive data handling
- Запрещено хранить секреты в репозитории.
- Конфигурация секретов только через environment variables / secret storage.
- PII (БИН, ИИН, контакты) не должна утекать в error payload и debug logs.
- Логи должны использовать redaction для чувствительных полей.

## Security headers and CORS
- Security headers задаются на gateway уровне (implementation ticket).
- CORS ограничивается разрешенными origin из конфигурации, без wildcard в production-конфигурации.

## High-risk change policy
- Следующие изменения требуют отдельного PR и расширенной проверки:
  - auth/roles/permissions;
  - security middleware/headers;
  - публичные API-контракты;
  - миграции данных, влияющие на доступ/аудит.

## Incident protocol
- Если найдено потенциальное нарушение безопасности:
  - остановить текущую реализацию;
  - зафиксировать инцидент в тикет-логе;
  - выполнить минимальный threat-model note;
  - продолжать только после подтверждения mitigation-плана.
