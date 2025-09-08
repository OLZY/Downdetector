import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import asyncio
from aiohttp import web
import threading
import signal
import os
import datetime

# Настройки
TOKEN = "токен телеграм"
API_URL = "https://ваш-домен.ру/api/service_monitor.php"
WEB_SERVER_PORT = 8080

# Глобальная переменная для Application
application = None

# Категории и сервисы
SERVICES = {
    "💰 Финансы": [
        "Т-банк", "Банк ВТБ", "Сбербанк", "Альфа-Банк", "Промсвязьбанк",
        "Московская Биржа", "СБП", "Яндекс Пей", "Газпромбанк", "OZON Банк",
        "МТС Банк", "Почта Банк", "МТС Деньги", "Bybit", "Россельхозбанк",
        "Райффайзен Банк", "Банк Санкт-Петербург", "Совкомбанк", "Telegram Wallet",
        "Золотая Корона", "Банк Уралсиб", "Binance", "Юmoney", "Мир",
        "БКС Мир Инвестиций", "Альфа-Инвестиции", "ВТБ Мои Инвестиции", "ЮKassa",
        "Robokassa", "Т-Инвестиции", "Т-Бизнес", "VK Pay"
    ],
    "📡 Телеком": [
        "TELE2", "МТС", "Билайн", "Мегафон", "Ростелеком", "YOTA", "Т-Мобайл",
        "Дом.ру", "СберМобайл", "МГТС", "Скайнет"
    ],
    "💬 Общение": [
        "Telegram", "ВКонтакте", "Discord", "Instagram", "Whatsapp", "Mail.ru",
        "Reddit", "Одноклассники", "X (Twitter)", "Facebook", "Viber", "Gmail",
        "VK Мессенджер"
    ],
    "🛒 E-commerce": [
        "Wildberries", "OZON", "Золотое Яблоко", "Яндекс Маркет", "Купер", "Lamoda",
        "Аптека.Ру", "Лэтуаль", "Flowwow", "Кассир.ру", "Exist", "Петрович"
    ],
    "🌐 Другие сайты": [
        "Яндекс", "Яндекс Почта", "Яндекс Еда", "Яндекс GO", "Яндекс Драйв", "Алиса",
        "Дом с Алисой", "SberDevices", "Авито", "Auto.ru", "Вкусно и точка", "Самокат",
        "Красное&Белое", "Госуслуги", "ФНС", "Четный знак", "Госключ", "2ГИС",
        "Мои документы", "РЖД", "СДЭК", "Делимобиль", "Почта России", "Google",
        "DeepSeek", "ChatGPT | OpenAI", "Grok", "GigaChat", "GitHub", "Figma",
        "App Store", "Steam", "Fortnite", "Roblox", "Twitch", "YouTube", "TikTok",
        "Dota 2", "PlayStation Network", "Epik Games", "DonationAlerts", "Battle.Net",
        "Counter-Strike 2", "Rockstar Games", "War Thunder", "PUBG Mobile", "Animedia Online"
    ]
}

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Paginator:
    def __init__(self, items, per_page=10):
        self.items = items
        self.per_page = per_page
        self.total_pages = (len(items) // per_page) + (1 if len(items) % per_page else 0)
    
    def get_page(self, page):
        start = (page - 1) * self.per_page
        end = start + self.per_page
        return self.items[start:end]

async def send_message_to_user(context: ContextTypes.DEFAULT_TYPE, user_id: int, message: str):
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML"
        )
        logger.info(f"Сообщение отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")

async def broadcast_message(context: ContextTypes.DEFAULT_TYPE, message: str):
    try:
        response = requests.post(
            API_URL,
            json={"action": "get_all_users_services"},
            timeout=15
        )
        response.raise_for_status()
        users_data = response.json().get("data", [])
        
        user_ids = list({user['id'] for user in users_data})
        
        for user_id in user_ids:
            try:
                await send_message_to_user(context, int(user_id), message)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка при массовой рассылке: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("➕ Добавить сервис", callback_data="add_service")],
        [InlineKeyboardButton("📋 Мои сервисы", callback_data="my_services")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для мониторинга сервисов. Вы можете добавить до 3 сервисов для отслеживания.",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "add_service":
        await show_categories(query)
    elif data == "my_services":
        await show_user_services(user_id, query)
    elif data == "back_to_main":
        await back_to_main_menu(query)
    elif data.startswith("category_"):
        category = data.split("_")[1]
        await show_services(category, 1, query)
    elif data.startswith("page_"):
        parts = data.split("_")
        category = parts[1]
        page = int(parts[2])
        await show_services(category, page, query)
    elif data.startswith("select_"):
        service = data.split("_")[1]
        await add_service(user_id, service, query)
    elif data.startswith("remove_"):
        service = data.split("_")[1]
        await remove_service(user_id, service, query)

async def back_to_main_menu(query):
    keyboard = [
        [InlineKeyboardButton("➕ Добавить сервис", callback_data="add_service")],
        [InlineKeyboardButton("📋 Мои сервисы", callback_data="my_services")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🖥️ Главное меню мониторинга",
        reply_markup=reply_markup
    )

async def show_categories(query):
    keyboard = [
        [InlineKeyboardButton(category, callback_data=f"category_{category}")]
        for category in SERVICES.keys()
    ]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📂 Выберите категорию:",
        reply_markup=reply_markup
    )

async def show_services(category, page, query):
    services = SERVICES[category]
    paginator = Paginator(services)
    page_services = paginator.get_page(page)
    
    keyboard = [
        [InlineKeyboardButton(service, callback_data=f"select_{service}")]
        for service in page_services
    ]
    
    pagination = []
    if page > 1:
        pagination.append(InlineKeyboardButton("◀️ Назад", callback_data=f"page_{category}_{page-1}"))
    if page < paginator.total_pages:
        pagination.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"page_{category}_{page+1}"))
    
    if pagination:
        keyboard.append(pagination)
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад к категориям", callback_data="add_service"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"📋 Категория: {category}\n"
        f"📄 Страница {page}/{paginator.total_pages}\n"
        "Выберите сервис:",
        reply_markup=reply_markup
    )

async def add_service(user_id, service, query):
    try:
        username = query.from_user.username or query.from_user.first_name
        
        # Проверяем существующие сервисы пользователя
        check_response = requests.post(
            API_URL,
            json={
                "action": "get",
                "user_id": str(user_id)
            },
            timeout=10
        )
        check_response.raise_for_status()
        check_data = check_response.json()
        
        if not check_data.get("success"):
            raise Exception("Ошибка при проверке существующих сервисов")
        
        # Определяем свободное поле для добавления сервиса
        field_to_update = None
        if not check_data.get("user_service"):
            field_to_update = "user_service"
        elif not check_data.get("user_service_2"):
            field_to_update = "user_service_2"
        elif not check_data.get("user_service_3"):
            field_to_update = "user_service_3"
        else:
            await query.edit_message_text(
                "❌ Вы уже добавили максимальное количество сервисов (3).",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🗑️ Удалить сервис", callback_data="my_services")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
            return
        
        # Проверяем, не добавлен ли уже этот сервис
        existing_services = [
            check_data.get("user_service"),
            check_data.get("user_service_2"), 
            check_data.get("user_service_3")
        ]
        if service in existing_services:
            await query.edit_message_text(
                f"❌ Сервис <b>{service}</b> уже добавлен!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
            return
        
        # Добавляем или обновляем сервис
        if check_data.get("exists"):
            update_response = requests.post(
                API_URL,
                json={
                    "action": "update",
                    "user_id": str(user_id),
                    "field": field_to_update,
                    "service": service,
                    "username": username
                },
                timeout=10
            )
        else:
            update_response = requests.post(
                API_URL,
                json={
                    "action": "add",
                    "user_id": str(user_id),
                    "username": username,
                    "service": service
                },
                timeout=10
            )
        
        update_response.raise_for_status()
        update_data = update_response.json()
        
        if update_data.get("success"):
            await check_service_for_outage(user_id, service, query)
        else:
            error_msg = update_data.get("error", "Неизвестная ошибка сервера")
            await query.edit_message_text(
                f"❌ Ошибка: {error_msg}\nПопробуйте позже."
            )
            
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка соединения с сервером: {str(e)}\n"
            "Попробуйте позже или сообщите администратору."
        )
        logger.error(f"Ошибка в add_service: {str(e)}")

async def check_service_for_outage(user_id, service, query):
    try:
        # Получаем список сервисов с проблемами
        down_response = requests.post(
            API_URL,
            json={"action": "get_down_services"},
            timeout=10
        )
        down_response.raise_for_status()
        down_data = down_response.json()
        
        down_services = down_data.get("services", [])
        
        keyboard = [
            [
                InlineKeyboardButton("📋 Мои сервисы", callback_data="my_services"),
                InlineKeyboardButton("ℹ️ О сервисе", url="https://ваш-домен.ру/about.html")
            ],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if service in down_services:
            await query.edit_message_text(
                f"✅ Сервис <b>{service}</b> добавлен в мониторинг!\n\n"
                "⚠️ <b>Внимание!</b> Сейчас этот сервис имеет проблемы с доступностью.",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                f"✅ Сервис <b>{service}</b> добавлен в мониторинг!\n\n"
                "Теперь вы будете получать уведомления о сбоях этого сервиса.",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Ошибка при проверке сервиса на сбой: {e}")

async def show_user_services(user_id, query):
    try:
        response = requests.post(
            API_URL,
            json={
                "action": "get",
                "user_id": str(user_id)
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            services = []
            if data.get("user_service"):
                services.append(data["user_service"])
            if data.get("user_service_2"):
                services.append(data["user_service_2"])
            if data.get("user_service_3"):
                services.append(data["user_service_3"])
            
            if services:
                message = "📋 Ваши сервисы в мониторинге:\n\n" + "\n".join(f"• {service}" for service in services)
                keyboard = [
                    [InlineKeyboardButton(f"🗑️ Удалить {service}", callback_data=f"remove_{service}")]
                    for service in services
                ]
                keyboard.append([
                    InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main"),
                    InlineKeyboardButton("ℹ️ О сервисе", url="https://ваш-домен.ру/about.html")
                ])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"{message}\n\n"
                    "Выберите сервис для удаления:",
                    reply_markup=reply_markup
                )
            else:
                keyboard = [
                    [InlineKeyboardButton("➕ Добавить сервис", callback_data="add_service")],
                    [
                        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main"),
                        InlineKeyboardButton("ℹ️ О сервисе", url="https://ваш-домен.ру/about.html")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "ℹ️ Вы еще не добавили ни одного сервиса в мониторинг.\n\n"
                    "Вы можете добавить новый сервис (максимум 3):",
                    reply_markup=reply_markup
                )
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка соединения с сервером: {str(e)}\n"
            "Попробуйте позже или сообщите администратору."
        )

async def remove_service(user_id, service, query):
    try:
        get_response = requests.post(
            API_URL,
            json={
                "action": "get",
                "user_id": str(user_id)
            },
            timeout=10
        )
        get_response.raise_for_status()
        get_data = get_response.json()
        
        if not get_data.get("success"):
            raise Exception("Не удалось получить данные пользователя")
        
        field_to_clear = None
        if get_data.get("user_service") == service:
            field_to_clear = "user_service"
        elif get_data.get("user_service_2") == service:
            field_to_clear = "user_service_2"
        elif get_data.get("user_service_3") == service:
            field_to_clear = "user_service_3"
        
        if not field_to_clear:
            await query.edit_message_text(
                f"❌ Сервис <b>{service}</b> не найден в вашем мониторинге!",
                parse_mode="HTML"
            )
            return
        
        response = requests.post(
            API_URL,
            json={
                "action": "delete",
                "user_id": str(user_id),
                "field": field_to_clear
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            keyboard = [
                [
                    InlineKeyboardButton("📋 Мои сервисы", callback_data="my_services"),
                    InlineKeyboardButton("ℹ️ О сервисе", url="https://ваш-домен.ру/about.html")
                ],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Сервис <b>{service}</b> успешно удален из мониторинга!",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            error_msg = data.get("error", "Неизвестная ошибка сервера")
            await query.edit_message_text(
                f"❌ Ошибка: {error_msg}\nПопробуйте позже."
            )
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка соединения с сервером: {str(e)}\n"
            "Попробуйте позже или сообщите администратору."
        )

async def check_services_for_outages(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔍 Проверка сервисов на сбои...")
    try:
        # 1. Получаем список проблемных сервисов
        down_response = requests.post(
            API_URL,
            json={"action": "get_down_services"},
            timeout=15
        )
        down_response.raise_for_status()
        down_data = down_response.json()
        
        if not down_data.get("success"):
            logger.error(f"API Error: {down_data.get('error')}")
            return

        down_services = down_data.get("services", [])
        logger.info(f"Сбойные сервисы: {down_services}")

        # 2. Получаем подписки пользователей
        users_response = requests.post(
            API_URL,
            json={"action": "get_all_users_services"},
            timeout=15
        )
        users_response.raise_for_status()
        users_data = users_response.json()
        
        if not users_data.get("success"):
            logger.error(f"API Error: {users_data.get('error')}")
            return

        # 3. Сравниваем и отправляем уведомления
        for user in users_data.get("data", []):
            user_id = user["id"]
            user_services = [
                user.get("user_service"),
                user.get("user_service_2"),
                user.get("user_service_3")
            ]
            user_services = list(filter(None, user_services))  # Убираем пустые
            
            problematic = list(set(user_services) & set(down_services))
            if problematic:
                message = (
                    "⚠️ <b>Обнаружены проблемы у сервиса/ов:</b>\n\n"
                    + "\n".join(f"▪️ {s}" for s in problematic)
                    + "\n\n💡 Проверить их работоспособность.\n"
                    "Нажмите <b>Открыть монитор</b>\n\n"
                    "🔕 Чтобы перестать получать уведомления, удалите сервис из мониторинга."
                )
                
                await context.bot.send_message(
                    user_id, 
                    message, 
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                logger.info(f"Уведомление отправлено {user_id}: {problematic}")

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")

async def handle_send_message(request):
    global application
    try:
        data = await request.json()
        user_id = data.get('user_id')
        message = data.get('message')
        is_broadcast = data.get('broadcast', False)
        
        if not message:
            return web.json_response({'status': 'error', 'message': 'No message provided'})
        
        if is_broadcast:
            await broadcast_message(application, message)
            return web.json_response({'status': 'success', 'message': 'Broadcast started'})
        elif user_id:
            await send_message_to_user(application, int(user_id), message)
            return web.json_response({'status': 'success'})
        else:
            return web.json_response({'status': 'error', 'message': 'Provide user_id or set broadcast=True'})
    except Exception as e:
        logger.error(f"Error in handle_send_message: {e}")
        return web.json_response({'status': 'error', 'message': str(e)})

async def on_shutdown(app):
    if application:
        await application.shutdown()
        await application.stop()
        await application.updater.stop()

def run_http_server():
    app = web.Application()
    app.add_routes([web.post('/send', handle_send_message)])
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, port=WEB_SERVER_PORT)

def main():
    global application
    
    application = Application.builder() \
        .token(TOKEN) \
        .connect_timeout(30) \
        .read_timeout(30) \
        .build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    job_queue = application.job_queue
    job_queue.run_repeating(
        callback=check_services_for_outages,
        interval=300.0,
        first=10.0
    )
    
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    def signal_handler(signum, frame):
        logger.info("Получен сигнал завершения")
        loop = asyncio.get_event_loop()
        loop.create_task(shutdown())
    
    async def shutdown():
        await application.shutdown()
        await application.stop()
        os._exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("🤖 Бот запущен")
        application.run_polling()
    except Exception as e:
        logger.error(f"❌ Ошибка при работе бота: {e}")
    finally:
        logger.info("🛑 Бот остановлен")

if __name__ == "__main__":
    main()