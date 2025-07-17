
# ГойдаБот9000

Telegram‑бот, измеряющий «гойдовость» сообщений.

## Быстрый старт

```bash
git clone https://example.com/GoydaBot9000.git
cd GoydaBot9000
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export GOYDA_BOT_TOKEN="123456789:AAFGz0F2vslK0a_ZwV-Gj56rtySgX2xDLhg"  # или измените config.py
python main.py
```

## Команды

| Команда | Описание |
|---------|----------|
| `/гойда_топ` | Топ‑5 гойдовых |
| `/мой_гойд_рейтинг` | Мой счёт |
| `/гойда_днище` | Последние места |
| `/гойда_reset` | Сброс статистики (админ) |

## Планировщик

APScheduler публикует «ГОЙДА НЕДЕЛИ» каждую **понедельник 09:00** по Europe/Vilnius. Настройте параметр `TOP_CRON` в `config.py`.

## Обработка медиа

* **Голос** — `ffmpeg` + Vosk (`vosk-transcriber` CLI).  
* **Картинки** — `pytesseract` OCR.  

## Обновление триггеров

Добавьте новые слова в `triggers.json` и перезапустите бота.

## Безопасность

* `/гойда_reset` доступен только Telegram‑ID из `ADMIN_IDS` в `handlers.py`.
* SQL‑инъекции неподдерживаемы: используются параметризованные запросы.
