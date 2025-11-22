import os
import random
import glob

from telegram import Bot, InputSticker
from telegram.error import BadRequest


def pick_random_image() -> str:
    """
    Берёт случайный PNG из папки IMAGE_DIR (по умолчанию: ./image)
    и возвращает путь к файлу.
    """
    image_dir = os.getenv("IMAGE_DIR", "image")

    # Ищем все PNG в папке
    pattern = os.path.join(image_dir, "*.png")
    files = [f for f in glob.glob(pattern) if os.path.isfile(f)]

    if not files:
        raise RuntimeError(f"No PNG files found in directory: {image_dir}")

    path = random.choice(files)
    print(f"Picked image: {path}")
    return path


async def update_sticker() -> None:
    """
    - выбирает случайную картинку из папки image,
    - загружает её в Telegram,
    - если набора нет — создаёт,
    - если набор есть — удаляет старый стикер и добавляет новый.
    """
    token = os.environ["BOT_TOKEN"]
    set_name = os.environ["STICKER_SET_NAME"]
    set_title = os.environ["STICKER_SET_TITLE"]
    owner_user_id = int(os.environ["TELEGRAM_USER_ID"])

    # 1) случайный PNG из репозитория
    image_path = pick_random_image()

    bot = Bot(token)

    # 2) загружаем файл как sticker-file, получаем file_id
    with open(image_path, "rb") as f:
        uploaded_file = await bot.upload_sticker_file(
            user_id=owner_user_id,
            sticker=f,
            sticker_format="static",
        )

    file_id = uploaded_file.file_id

    # 3) собираем InputSticker
    new_sticker = InputSticker(
        sticker=file_id,
        emoji_list=["🎲"],  # можно поменять на любую эмодзи
        format="static",
    )

    # 4) пробуем получить набор
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

    # 5) набор есть — удаляем старый стикер (если есть)
    if sticker_set.stickers:
        old_id = sticker_set.stickers[0].file_id
        try:
            await bot.delete_sticker_from_set(old_id)
            print(f"Deleted old sticker {old_id} from set {set_name}")
        except BadRequest as e:
            print("delete_sticker_from_set error:", getattr(e, "message", str(e)))

    # 6) добавляем новый стикер в набор
    await bot.add_sticker_to_set(
        user_id=owner_user_id,
        name=set_name,
        sticker=new_sticker,
    )
    print(f"Added new sticker to set {set_name}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(update_sticker())
