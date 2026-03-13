# OPS ECP verifier trust store

Этот каталог монтируется в runtime контейнеры как `/app/cert-signing` и используется backend verifier path для проверки CMS-подписи.

Минимально сюда нужно положить:
- `nuc-ca-chain.pem` — доверенная цепочка/CA bundle для проверки подписи;
- `nuc.crl` — optional CRL file, если используется `CERT_SIGNATURE_CRL_FILE`.

Ограничения:
- не коммитить секретные ключи, токены или приватные контейнеры сертификатов;
- допустимо хранить только публичные trust artifacts, если это разрешено вашей политикой;
- если файл `nuc-ca-chain.pem` отсутствует, backend вернет `validation_backend_unavailable`, и сертификат не будет опубликован.
