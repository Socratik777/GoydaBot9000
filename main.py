"""
main.py — точка входа ГойдаБот9000
----------------------------------
* добавлен runtime-патч, устраняющий конфликт PTB 20.7 с CPython 3.13
* остальная логика осталась прежней
"""

import logging
import sys

# ---------------------------------------------------------------------------
#  💉  Runtime-патч для python-telegram-bot 20.7 на Python 3.13
# ---------------------------------------------------------------------------
#
# В CPython 3.13 изменилось поведение name-mangling для __slots__,
# из-за чего в объекте telegram.ext.Updater отсутствует атрибут
# `__polling_cleanup_cb`.  Библиотека пытается записать его и
# получает AttributeError. Ниже «дозарегистрируем» слот, если нужно.
#
# После выхода PTB ≥ 20.8 (или отката на Python ≤ 3.12) блок можно удалить.
#
if sys.version_info >= (3, 13):
    try:
        import telegram.ext._updater as _updater

        # добавляем слот, если его нет
        if "__polling_cleanup_cb" not in getattr(_updater.Updater, "__slots__", ()):
            _updater.Updater.__slots__ += ("__polling_cleanup_cb",)

    except Exception as err:  # noqa: BLE001
        # Патч не критичен: если что-то пошло не так — просто логируем
        logging.warning("PTB 3.13-compat patch failed: %s", err)

# ---------------------------------------------------------------------------
#  Основная часть приложения
# ---------------------------------------------------------------------------
from telegram.ext import Application  # noqa: E402 (импорт после патча)

from config import BOT_TOKEN, LOG_LEVEL
from handlers import register_handlers
from scheduler import schedule


def setup_logging() -> None:
    """Единообразная настройка логирования для всего проекта."""
    logging.basicConfig(
        format="%(asctime)s — %(levelname)s — %(name)s — %(message)s",
        level=getattr(logging, LOG_LEVEL, logging.INFO),
    )


def main() -> None:
    """Инициализация и запуск поллинга."""
    setup_logging()

    app = Application.builder().token(BOT_TOKEN).build()

    register_handlers(app)
    schedule(app)

    logging.info("ГойдаБот9000 запущен. Ждём гойд…")
    app.run_polling()


if __name__ == "__main__":
    main()