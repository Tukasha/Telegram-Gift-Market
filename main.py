import asyncio
import aiohttp
from aiogram import Bot

# Введите токен и получателя
BOT_TOKEN = input("Введите токен бота: ").strip()
TARGET_USER_ID = int(input("Введите ID получателя: ").strip())

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Официальные цены Premium в звёздах
PREMIUM_PRICE = {3: 1000, 6: 1500, 12: 2500}

async def call_raw_api(method: str, payload: dict | None = None):
    """Вызов Bot API напрямую для методов, которых может не быть в SDK."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/{method}", json=payload or {}) as resp:
            data = await resp.json()
            if not data.get("ok"):
                raise RuntimeError(f"{method} failed: {data}")
            return data["result"]

async def fetch_star_balance(bot: Bot) -> int:
    """Получить баланс звёзд бота (официальный метод из SDK, если поддерживается)."""
    balance_info = await bot.get_my_star_balance()
    return getattr(balance_info, "amount", 0)

async def fetch_available_gifts() -> list[dict]:
    """Получить доступные подарки-стикеры через Bot API."""
    result = await call_raw_api("getAvailableGifts")
    gifts = []
    for g in result.get("gifts", []):
        gifts.append({
            "id": g["id"],
            "type": "стикер",
            "name": g["sticker"]["emoji"],
            "price": g["star_count"],
        })
    return gifts

async def send_gift_sticker(gift_id: str | int, user_id: int, text: str | None = None):
    """Отправить подарок-стикер через Bot API."""
    payload = {
        "gift_id": gift_id,
        "user_id": user_id,
    }
    if text:
        payload["text"] = text
    return await call_raw_api("sendGift", payload)

async def main():
    bot = Bot(token=BOT_TOKEN)

    try:
        # Авторизация
        me = await bot.get_me()
        print(f"✅ Бот авторизован: @{me.username}")

        # Баланс
        print("🌟 Проверяем баланс звёзд...")
        stars_balance = await fetch_star_balance(bot)
        print(f"💰 Баланс: {stars_balance} ⭐")

        # Премиум (официальные 3/6/12 мес.)
        premium_options = [
            {"id": months, "type": "Premium", "name": f"Подписка на {months} мес.", "price": PREMIUM_PRICE[months]}
            for months in (3, 6, 12)
        ]

        # Подарки-стикеры из API
        print("🎁 Загружаем доступные подарки...")
        try:
            sticker_gifts = await fetch_available_gifts()
        except Exception as e:
            print(f"⚠ Не удалось получить подарки-стикеры: {e}")
            sticker_gifts = []

        available_options = premium_options + sticker_gifts
        if not available_options:
            print("❌ Нет доступных опций для подарков.")
            return

        # Вывод
        print("\n✅ Доступные опции:")
        for opt in available_options:
            afford = "✅ хватает" if stars_balance >= opt["price"] else "❌ мало звёзд"
            print(f"- ID: {opt['id']} | {opt['type']}: {opt['name']} | Цена: {opt['price']} ⭐ | {afford}")

        # Выбор
        choice = input("\nВведите ID опции (3/6/12 для Premium или ID подарка-стикера): ").strip()
        selected = next((o for o in available_options if str(o["id"]) == choice), None)
        if not selected:
            print("❌ Такой опции нет.")
            return

        if stars_balance < selected["price"]:
            print(f"❌ Недостаточно звёзд. Нужно: {selected['price']} ⭐, доступно: {stars_balance} ⭐.")
            return

        # Покупка
        print(f"⏳ Покупаем {selected['type']} {selected['name']}...")
        if selected["type"] == "Premium":
            months = int(selected["id"])
            star_count = PREMIUM_PRICE[months]
            ok = await bot.gift_premium_subscription(
                user_id=TARGET_USER_ID,
                month_count=months,
                star_count=star_count,
                text=f"by tukasha"
            )
            if ok:
                print("🎉 Premium успешно подарен!")
            else:
                print("❌ Не удалось отправить Premium.")
        else:
            result = await send_gift_sticker(
                gift_id=selected["id"],
                user_id=TARGET_USER_ID,
                text="by tukasha"
            )
            print(f"🎉 Стикер-подарок отправлен: {result}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    while True: asyncio.run(main())