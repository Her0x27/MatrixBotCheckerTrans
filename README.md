# Crypto Checker Bot

Бот для проверки транзакций различных криптовалют с автоматическим определением типа криптовалюты по формату адреса.

## Поддерживаемые криптовалюты

- Bitcoin
- Ethereum
- Litecoin
- TRON
- USDT (TRC20)
- USDT (ERC20)
- Dogecoin

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/crypto_checker_bot.git
cd crypto_checker_bot
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Создайте файл `.env` и заполните его необходимыми данными:
```
MATRIX_HOMESERVER=https://matrix.org
MATRIX_ACCESS_TOKEN=your_access_token
ETHERSCAN_API_KEY=your_etherscan_api_key
BLOCKCYPHER_API_KEY=your_blockcypher_api_key
TRONGRID_API_KEY=your_trongrid_api_key
```

## Получение токена доступа Matrix

Для получения токена доступа вы можете использовать следующие методы:

1. Через Element (или другой Matrix клиент):
   - Откройте настройки -> Помощь и о программе -> Дополнительно -> Доступ к API
   - Скопируйте значение "Access Token"

2. Через curl:
```bash
curl -X POST -d '{"type":"m.login.password", "user":"YOUR_USERNAME", "password":"YOUR_PASSWORD"}' https://matrix.org/_matrix/client/r0/login
```

## Запуск

```bash
./start_bot.sh
```

## Использование

1. Добавьте бота в комнату или начните с ним личную переписку.
2. Отправьте криптовалютный адрес, и бот автоматически определит тип криптовалюты и проверит баланс и транзакции.
3. Для смены языка используйте команды:
   - `/ru` - переключиться на русский язык
   - `/en` - переключиться на английский язык

## Примеры адресов для тестирования

- Bitcoin: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
- Ethereum: 0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae
- Litecoin: LM2WMpR1Rp6j3Sa59cMXMs1SPzj9eXpGc1
- TRON: TRX9gZhpusXkgTbWJ8WfoU2pRkPAJ5jJUX
- Dogecoin: D8vFz4p1L37jdg9xpmmVSuPBXhyjmoQjXA
```

Обновим скрипт запуска:

```bash:start_bot.sh
#!/bin/bash
source venv/bin/activate
export $(grep -v '^#' .env | xargs)
python bot.py
```

Обновим файл requirements.txt, добавив python-dotenv:

```text:requirements.txt
mautrix
requests
python-i18n
python-dotenv
```

## Как получить токен доступа Matrix

Для тех, кто не знает, как получить токен доступа Matrix, вот несколько способов:

### Метод 1: Через Element (или другой Matrix клиент)

1. Войдите в свой аккаунт в Element
2. Перейдите в Настройки -> Помощь и о программе -> Дополнительно
3. Найдите раздел "Доступ к API" и скопируйте значение "Access Token"

### Метод 2: Через curl

```bash
curl -X POST -d '{"type":"m.login.password", "user":"YOUR_USERNAME", "password":"YOUR_PASSWORD"}' https://matrix.org/_matrix/client/r0/login
```

Ответ будет содержать токен доступа:

```json
{
  "user_id": "@username:matrix.org",
  "access_token": "YOUR_ACCESS_TOKEN",
  "home_server": "matrix.org",
  "device_id": "DEVICE_ID"
}
```

### Метод 3: Через Python

Вы также можете получить токен программно с помощью Python:

```python:get_token.py
#!/usr/bin/env python3
import asyncio
from mautrix.client import Client

async def get_token(homeserver, username, password):
    client = Client(homeserver)
    login_response = await client.login(username=username, password=password)
    print(f"Access Token: {login_response.access_token}")
    await client.logout()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python get_token.py homeserver username password")
        print("Example: python get_token.py https://matrix.org myusername mypassword")
        sys.exit(1)
    
    homeserver = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    asyncio.run(get_token(homeserver, username, password))
```

Сохраните этот скрипт как `get_token.py` и запустите:

```bash
python get_token.py https://matrix.org myusername mypassword
```
