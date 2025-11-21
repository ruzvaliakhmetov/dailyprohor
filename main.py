import os
import random

import requests
from telegram import Bot, InputSticker
from telegram.error import BadRequest


# === Настройки картинок ===

BASE_DIR_URL = os.getenv(
    "BASE_DIR_URL",
    "https://valiakhmetov.com/images/tg/dailyprohor",
)

# Сколько у тебя файлов sticker512x512_01.png, sticker512x512_02.png, ...
# Можно задать через переменную окружения IMAGE_COUNT
IMAGE_COUNT = int(os.getenv("IMAGE_COUNT", "15"))


def download_random_image(output_path: str = "sticker.png") -> None:
    """
    Выбирает случайную картинку из BASE_DIR_URL вида:
    sticker512x512_01.png ... sticker512x512_N.png
    и сохраняет локально как output_path.
    """
    if IMAGE_COUNT < 1:
        raise ValueError("IMAGE_COUNT must be >= 1")

    idx = random.randint(1, IMAGE_COUNT)
    filename = f"sticker512x512_{idx:02d}.png"
    url = f"{BASE_DIR_URL.rstrip('/')}/{filename}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(resp.content)

    print(f"Downloaded {url} -> {output_path}")


async def update_sticker() -> None:
    """
    - качает случайную картинку,
    - загружает её в Telegram,
    - если набора нет — создаёт,
    - если набор есть — удаляет старый стикер и добавляет новый.
    """
    token = os.environ["BOT_TOKEN"]
    set_name = os.environ["STICKER_SET_NAME"]
    set_title = os.environ["STICKER_SET_TITLE"]
    owner_user_id = int(os.environ["TELEGRAM_USER_ID"])

    # 1) Качаем PNG
    download_random_image("sticker.png")

    bot = Bot(token)

    # 2) Загружаем файл как sticker-file, получаем file_id
    with open("sticker.png", "rb") as f:
        uploaded_file = await bot.upload_sticker_file(
            user_id=owner_user_id,
            sticker=f,
            sticker_format="static",
        )

    file_id = uploaded_file.file_id

    # 3) Собираем InputSticker
    new_sticker = InputSticker(
        sticker=file_id,
        emoji_list=["🎲"],  # можешь поставить любую эмодзи
        format="static",
    )

    # 4) Пробуем получить набор
    try:
        sticker_set = await bot.get_sticker_set(set_name)
    except BadRequest as e:
        msg = getattr(e, "message", str(e)).lower()
        print("get_sticker_set error:", msg)
        # Набор ещё не создан — создаём новый
        if "stickerset_invalid" in msg or "stickerset not found" in msg:
            await bot.create_new_sticker_set(
                user_id=owner_user_id,
                name=set_name,
                title=set_title,
                stickers=[new_sticker],
                sticker_type="regular",
            )
            print(f"Created new sticker set {set_name}")
            return
        else:
            raise

    # 5) Набор есть — удаляем старый стикер (если есть)
    if sticker_set.stickers:
        old_id = sticker_set.stickers[0].file_id
        try:
            await bot.delete_sticker_from_set(old_id)
            print(f"Deleted old sticker {old_id} from set {set_name}")
        except BadRequest as e:
            print("delete_sticker_from_set error:", getattr(e, "message", str(e)))

    # 6) Добавляем новый стикер в набор
    await bot.add_sticker_to_set(
        user_id=owner_user_id,
        name=set_name,
        sticker=new_sticker,
    )
    print(f"Added new sticker to set {set_name}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(update_sticker())
