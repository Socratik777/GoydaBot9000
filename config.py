
BOT_TOKEN = "8144180443:AAFxdcvF0WUomB1CTdtYUJtgfo8V9ahrT6M"

DB_PATH = "goyda.db"
TRIGGERS_PATH = "triggers.json"
LOG_LEVEL = "INFO"
YOUR_GROUP_CHAT_ID = 4801302164

# роли
CREATOR   =  814418044        #  @KOKAKOLYA24
ADMINS    = {508812345, 777777777}   # @DiplomastersRU, @Ardoran_Wolperlinger
ADMIN_IDS = {CREATOR, *ADMINS}

# таймеры упоминаний (сек)
MENTION_COOLDOWN = {
    CREATOR: 3600,          # — 1 ч
    508812345: 1800,        # «100-ый с нами»  — 30 мин
    777777777: 1200         # «Ксеносов на чистку…» — 20 мин
}

# APScheduler cron for weekly top (Monday 09:00 Europe/Vilnius)
TOP_CRON = {"day_of_week": "mon", "hour": 9, "minute": 0}


