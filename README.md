# RabbitMQ Bootstrap для Клієнта

Простий ідемпотентний bootstrap-скрипт для онбордингу нового клієнта.

Сутності, якими керує скрипт:
- vhost
- users
- permissions
- exchanges
- queues
- bindings

Якщо сутність уже існує, скрипт пропускає її і не змінює.

У `config.yaml` вказується тільки список `vhosts`.
Усі інші сутності генеруються автоматично з назви кожного `vhost`.

## 1) Встановлення залежностей

```bash
python -m pip install -r requirements.txt
```

## 2) Підготовка конфігурації

Скопіюйте `config.yaml.example` у `config.yaml` і вкажіть список `vhosts`.

Обов'язкові ключі в `config.yaml`:
- `vhosts`

Параметри підключення до RabbitMQ Management API задаються у `.env` файлі.

Приклад `.env`:

```env
RABBITMQ_API_URL=http://127.0.0.1:15672
RABBITMQ_API_USER=admin
RABBITMQ_API_PASSWORD=change_me
```

За потреби можна перевизначити шлях до env-файлу параметром `--env-file`.

Що генерується автоматично для кожного `vhost`:
- користувачі: `<vhost>_producer`, `<vhost>_consumer` (не-алфанумеричні символи замінюються на `_`)
- exchange: `<vhost>.events`
- queue: `<vhost>.events.q`
- binding: `<vhost>.events` -> `<vhost>.events.q`, routing key `<vhost>.events.*`
- permissions для producer/consumer

## 3) Перевірка без змін (dry run)

```bash
python scripts/bootstrap_rabbitmq.py --config config.yaml --check
```

## 4) Застосування змін

```bash
python scripts/bootstrap_rabbitmq.py --config config.yaml
```

## 5) Згенеровані паролі

Якщо скрипт створює нового користувача RabbitMQ без явно заданого пароля в конфігурації,
він генерує сильний пароль і зберігає його у файлі `users`.

Можна перевизначити шлях до файлу параметром:

```bash
python scripts/bootstrap_rabbitmq.py --config config.yaml --users-file users
```

## Команди для перевірки

```bash
rabbitmqctl list_vhosts
rabbitmqctl list_users
rabbitmqctl list_permissions -p <vhost>
rabbitmqctl list_exchanges -p <vhost>
rabbitmqctl list_queues -p <vhost>
rabbitmqctl list_bindings -p <vhost>
```
