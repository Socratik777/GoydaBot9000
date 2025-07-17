
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from config import BOT_TOKEN, TOP_CRON
from database import get_top, clear_femboy_winners, reset_femboy
from datetime import datetime, timezone, timedelta

scheduler = AsyncIOScheduler(timezone="Europe/Vilnius")
bot = Bot(BOT_TOKEN)

def schedule(app):
    async def weekly_top():
        top = get_top(1)
        if not top:
            return
        user, score = top[0]
        await bot.send_message(chat_id=app.bot.id, text=f"ГОЙДА НЕДЕЛИ: @{user} (+{score})")

    scheduler.add_job(weekly_top, "cron", **TOP_CRON)
    scheduler.start()
    
# 10:00 МСК = 07:00 UTC
scheduler.add_job(
    lambda: (clear_femboy_winners(), reset_femboy()),   # оба сброса
    "cron",
    hour=7, minute=0, timezone=timezone.utc    # 07:00 UTC
)