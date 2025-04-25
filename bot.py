#!/usr/bin/env python3
import asyncio
import logging
import re
import json
import os
import requests
import i18n
from mautrix.client import Client
from mautrix.types import EventType, MessageType
from mautrix.errors import MNotFound
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crypto_checker_bot")

# Настройка локализации
i18n.load_path.append('./locales')
i18n.set('fallback', 'ru')

# Регулярные выражения для определения типа криптовалюты по адресу
CRYPTO_PATTERNS = {
    'bitcoin': r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$',
    'ethereum': r'^0x[a-fA-F0-9]{40}$',
    'litecoin': r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$',
    'tron': r'^T[a-zA-Z0-9]{33}$',
    'usdt_trc20': r'^T[a-zA-Z0-9]{33}$',  # USDT на сети TRON
    'usdt_erc20': r'^0x[a-fA-F0-9]{40}$',  # USDT на сети Ethereum
    'dogecoin': r'^D{1}[5-9A-HJ-NP-U]{1}[1-9A-HJ-NP-Za-km-z]{32}$',
}

# API ключи
API_KEYS = {
    'etherscan': os.getenv('ETHERSCAN_API_KEY', ''),
    'blockcypher': os.getenv('BLOCKCYPHER_API_KEY', ''),
    'trongrid': os.getenv('TRONGRID_API_KEY', ''),
}

class CryptoCheckerBot:
    def __init__(self, homeserver, access_token):
        self.client = Client(homeserver)
        self.access_token = access_token
        self.user_languages = {}
        self.crypto_apis = {
            'bitcoin': self.check_bitcoin,
            'ethereum': self.check_ethereum,
            'litecoin': self.check_litecoin,
            'tron': self.check_tron,
            'usdt_trc20': self.check_tron_usdt,
            'usdt_erc20': self.check_ethereum_usdt,
            'dogecoin': self.check_dogecoin,
        }

    async def login(self):
        """Авторизация бота по токену"""
        try:
            # Используем токен доступа вместо логина/пароля
            self.client.access_token = self.access_token
            whoami = await self.client.whoami()
            logger.info(f"Logged in as {whoami.user_id}")
        except Exception as e:
            logger.error(f"Failed to log in: {e}")
            raise

    async def start(self):
        """Запуск бота"""
        await self.login()
        
        # Регистрация обработчика сообщений
        self.client.add_event_handler(EventType.ROOM_MESSAGE, self.handle_message)
        
        # Синхронизация с сервером
        await self.client.sync_forever(timeout=30000)

    async def handle_message(self, event):
        """Обработка входящих сообщений"""
        if event.content.msgtype != MessageType.TEXT:
            return
        
        # Получаем текст сообщения
        message = event.content.body
        room_id = event.room_id
        sender = event.sender
        
        # Если сообщение от самого бота, игнорируем
        if sender == self.client.mxid:
            return
        
        # Проверяем, является ли сообщение командой для смены языка
        if message.lower() in ['/ru', '/en']:
            lang = message.lower().replace('/', '')
            await self.set_language(room_id, sender, lang)
            return
        
        # Проверяем, является ли сообщение криптовалютным адресом
        crypto_type = self.detect_crypto_type(message)
        if crypto_type:
            await self.check_address(room_id, message, crypto_type, sender)
        else:
            # Если не удалось определить тип криптовалюты
            await self.client.send_text(room_id, i18n.t('messages.invalid_address', locale=self.get_user_language(sender)))

    def detect_crypto_type(self, address):
        """Определение типа криптовалюты по адресу"""
        for crypto_type, pattern in CRYPTO_PATTERNS.items():
            if re.match(pattern, address):
                return crypto_type
        return None

    async def check_address(self, room_id, address, crypto_type, sender):
        """Проверка адреса и получение информации о транзакциях"""
        user_lang = self.get_user_language(sender)
        
        # Отправляем сообщение о начале проверки
        await self.client.send_text(
            room_id, 
            i18n.t('messages.checking', 
                   address=address, 
                   crypto=i18n.t(f'crypto.{crypto_type}', locale=user_lang),
                   locale=user_lang)
        )
        
        try:
            # Вызываем соответствующий метод для проверки адреса
            if crypto_type in self.crypto_apis:
                result = await self.crypto_apis[crypto_type](address)
                await self.client.send_text(room_id, result)
            else:
                await self.client.send_text(
                    room_id, 
                    i18n.t('messages.unsupported_crypto', locale=user_lang)
                )
        except Exception as e:
            logger.error(f"Error checking address {address}: {e}")
            await self.client.send_text(
                room_id, 
                i18n.t('messages.error', locale=user_lang)
            )

    async def check_bitcoin(self, address):
        """Проверка Bitcoin адреса"""
        url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            balance = data.get('balance', 0) / 100000000  # Конвертация из сатоши в BTC
            total_received = data.get('total_received', 0) / 100000000
            total_sent = data.get('total_sent', 0) / 100000000
            n_tx = data.get('n_tx', 0)
            
            return f"Bitcoin Address: {address}\nBalance: {balance} BTC\nTotal Received: {total_received} BTC\nTotal Sent: {total_sent} BTC\nTransactions: {n_tx}"
        else:
            return f"Error checking Bitcoin address: {response.status_code}"

    async def check_ethereum(self, address):
        """Проверка Ethereum адреса"""
        if not API_KEYS['etherscan']:
            return "Etherscan API key is not set"
        
        url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={API_KEYS['etherscan']}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1':
                balance = int(data['result']) / 1e18  # Конвертация из wei в ETH
                
                # Получаем информацию о транзакциях
                tx_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={API_KEYS['etherscan']}"
                tx_response = requests.get(tx_url)
                tx_data = tx_response.json()
                tx_count = len(tx_data.get('result', [])) if tx_data['status'] == '1' else 0
                
                return f"Ethereum Address: {address}\nBalance: {balance} ETH\nTransactions: {tx_count}"
            else:
                return f"Error checking Ethereum address: {data['message']}"
        else:
            return f"Error checking Ethereum address: {response.status_code}"

    async def check_litecoin(self, address):
        """Проверка Litecoin адреса"""
        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            balance = data.get('balance', 0) / 100000000  # Конвертация из литоши в LTC
            total_received = data.get('total_received', 0) / 100000000
            total_sent = data.get('total_sent', 0) / 100000000
            n_tx = data.get('n_tx', 0)
            
            return f"Litecoin Address: {address}\nBalance: {balance} LTC\nTotal Received: {total_received} LTC\nTotal Sent: {total_sent} LTC\nTransactions: {n_tx}"
        else:
            return f"Error checking Litecoin address: {response.status_code}"

    async def check_tron(self, address):
        """Проверка TRON адреса"""
        url = f"https://api.trongrid.io/v1/accounts/{address}"
        headers = {}
        if API_KEYS['trongrid']:
            headers['TRON-PRO-API-KEY'] = API_KEYS['trongrid']
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('success', False) and data.get('data', []):
                account_data = data['data'][0]
                balance = account_data.get('balance', 0) / 1e6  # Конвертация в TRX
                
                return f"TRON Address: {address}\nBalance: {balance} TRX"
            else:
                return f"No data found for TRON address: {address}"
        else:
            return f"Error checking TRON address: {response.status_code}"

    async def check_tron_usdt(self, address):
        """Проверка USDT на сети TRON (TRC20)"""
        # USDT TRC20 контракт
        contract_address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        
        url = f"https://api.trongrid.io/v1/accounts/{address}/tokens?contract_address={contract_address}"
        headers = {}
        if API_KEYS['trongrid']:
            headers['TRON-PRO-API-KEY'] = API_KEYS['trongrid']
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('success', False) and data.get('data', []):
                token_data = data['data']
                usdt_balance = 0
                for token in token_data:
                    if token.get('tokenId') == contract_address:
                        usdt_balance = int(token.get('balance', 0)) / 1e6
                        break
                
                return f"USDT (TRC20) Address: {address}\nBalance: {usdt_balance} USDT"
            else:
                return f"No USDT (TRC20) tokens found for address: {address}"
        else:
            return f"Error checking USDT (TRC20) address: {response.status_code}"

    async def check_ethereum_usdt(self, address):
        """Проверка USDT на сети Ethereum (ERC20)"""
        if not API_KEYS['etherscan']:
            return "Etherscan API key is not set"
        
        # USDT ERC20 контракт
        contract_address = "0xdac17f958d2ee523a2206206994597c13d831ec7"
        
        url = f"https://api.etherscan.io/api?module=account&action=tokenbalance&contractaddress={contract_address}&address={address}&tag=latest&apikey={API_KEYS['etherscan']}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1':
                balance = int(data['result']) / 1e6  # USDT имеет 6 десятичных знаков
                
                return f"USDT (ERC20) Address: {address}\nBalance: {balance} USDT"
            else:
                return f"Error checking USDT (ERC20) address: {data['message']}"
        else:
            return f"Error checking USDT (ERC20) address: {response.status_code}"

    async def check_dogecoin(self, address):
        """Проверка Dogecoin адреса"""
        url = f"https://api.blockcypher.com/v1/doge/main/addrs/{address}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            balance = data.get('balance', 0) / 100000000  # Конвертация в DOGE
            total_received = data.get('total_received', 0) / 100000000
            total_sent = data.get('total_sent', 0) / 100000000
            n_tx = data.get('n_tx', 0)
            
            return f"Dogecoin Address: {address}\nBalance: {balance} DOGE\nTotal Received: {total_received} DOGE\nTotal Sent: {total_sent} DOGE\nTransactions: {n_tx}"
        else:
            return f"Error checking Dogecoin address: {response.status_code}"

    async def set_language(self, room_id, user_id, lang):
        """Установка языка для пользователя"""
        self.user_languages[user_id] = lang
        
        await self.client.send_text(
            room_id, 
            i18n.t('messages.language_changed', locale=lang)
        )

    def get_user_language(self, user_id):
        """Получение языка пользователя"""

        return self.user_languages.get(user_id, 'ru')  # По умолчанию русский

async def main():
    # Параметры подключения к Matrix серверу
    homeserver = os.getenv("MATRIX_HOMESERVER")
    user_id = os.getenv("MATRIX_USER_ID")
    access_token = os.getenv("MATRIX_ACCESS_TOKEN")
    
    # Выводим значения для отладки
    logger.info(f"Homeserver: {homeserver}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Access Token: {'*' * 10 if access_token else 'Not set'}")
    
    if not user_id or not access_token or not homeserver:
        logger.error("Matrix homeserver, user_id or access_token not set")
        return
    
    # Проверяем, что user_id начинается с @
    if not user_id.startswith('@'):
        logger.error(f"User ID must start with @, got: {user_id}")
        return
    
    bot = CryptoCheckerBot(homeserver, user_id, access_token)
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
