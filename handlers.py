import logging, random, re
from typing import Any

# временное хранилище незавершённых админ-действий
pending_actions: dict[int, dict[str, Any]] = {}
logging.basicConfig(level=logging.INFO)
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from goyda_analyzer import (
    score_message,
    analyse_goyda,
)

from database import (
    add_score, get_top, get_bottom, get_user_score, reset_scores,
    add_femboy, get_femboy, get_top_femboy, reset_femboy,
    has_femboy_winner_today, set_femboy_winner
)
from utils import (
    detect_topic, has_goyda, femboy_score_delta, progress_bar, WAHA_KEYWORDS
)
from datetime import datetime, timezone

from pathlib import Path

TRIG_DIR = Path(__file__).parent / "triggers"

def _load_trig(filename: str) -> set[str]:
    with open(TRIG_DIR / filename, encoding="utf-8") as fp:
        return {w.lower() for w in json.load(fp)}

LINUX_KEYWORDS     = _load_trig("linux.json")
UA_SUPPORT_PHRASES = _load_trig("ua_support.json")
ADMIN_JOKE_WORDS   = _load_trig("admin_jokes.json")
GIF_DIR = Path(__file__).parent / "gif"

# Гифки для новых пользователей
NEW_USER_GIFS = [
    GIF_DIR / "welcome1.mp4",
    GIF_DIR / "welcome2.mp4",
    GIF_DIR / "welcome3.mp4"
]

# ── Батюшка / Priest triggers ──────────────────────────────────────
TRIG_DIR = Path(__file__).parent / "triggers"
    
BATYUSHKA_TRIGGERS = _load_trig("batyushka.json") 
# список file_unique_id стикеров или file_id’ов
BATYUSHKA_STICKERS = [
    "CAACAgIAAxkBAAEBbgRoeB0l8qdHd2whvkrpPifxuYnY5gAChVQAArLnKUqcbpJ6EA1fVDYE",
    "CAACAgIAAxkBAAEBbgZoeB2e7hEtv2RTeTIQ2eLT4B3PlwAC800AAqB1SUoDUYJt5o80zDYE"
]

# фиксируем момент старта бота в UTC
BOT_START_TIME = datetime.now(timezone.utc)

# Библиотека общих ответов на «гойду»
GOYDA_FALLBACK = [
    "🎉 ЗА НАМИ МОСКВА!!!",
    "🚀 Мать Обамы ПРОБИТА!",
    "🥁 ТАК ДЕРЖАТЬ!",
    "📢 Всем чатам слышим твою оргию!",
    "🚀Услышал тебя родной!"
]
# ------------------------------------------------------------------
# Warhammer / “Ваха” detection
WAHA_PHRASES = [
    "Выучил всех примархов, @{user}?",
    "А как насчёт одолеть титана штык-ножом, еретик?",
    "Император не одобряет таких сообщений…",
    "Очищай чат от ксеносов!",
    "За Империум! Астарты, вперед!",
    "In the grim darkness of the far future, there is only WAR…",
    "Не позволяй Королю Земель померкнуть, @{user}.",
    "Помни Золотой Трон, брат Астартес!",
    "Сквозь сто веков святая цель Империума ведёт нас!",
    "Клянусь кровью помазать этих ксеносов!",
    "Ты не видел Хаоса? Он видит тебя…",
    "Хранил ли ты верность Золотому Трону, @{user}?",
    "Буди свой Болтер, эретик!",
    "Твоя вера — наше оружие!",
    "Приготовься к Высшей Библии Муспека!"
]

# GIF-ы для Linux и «оправдывающих Украину»

LINUX_GIF = GIF_DIR / "linuxoid.mp4"
UA_GIFS = [
    GIF_DIR / "ua1.mp4",
    GIF_DIR / "ua2.mp4",
    GIF_DIR / "ua3.mp4",
    GIF_DIR / "ua4.mp4",
    GIF_DIR / "ua5.mp4",
    GIF_DIR / "ua6.mp4",
    GIF_DIR / "ua7.mp4",
    GIF_DIR / "ua8.mp4",
    GIF_DIR / "ua9.mp4",
    GIF_DIR / "ua10.mp4"
]

ADMIN_GIF = GIF_DIR / "admin.mp4"

BATYUSHKA_GIF = GIF_DIR / "batyushka.mp4"
BATYUSHKA_PHRASES = [
    "Батюшка причастился — наша вера укрепилась. ☦🙏",
    "Батюшка причастился — Русь в молитве освятилась. ☦",
]

# helper: стираем сообщение-команду, чтобы его не видели остальные
async def _delete_invoking_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception:
            # нет прав удалять, или сообщение уже исчезло
            pass

# Обработчик новых участников чата
async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        gif_path = random.choice(NEW_USER_GIFS)
        try:
            with open(gif_path, "rb") as gif:
                await update.message.reply_animation(gif, caption=f"Добро пожаловать, {user.mention_html()}!", parse_mode="HTML")
        except FileNotFoundError:
            await update.message.reply_text(f"Добро пожаловать, {user.mention_html()}!", parse_mode="HTML")
# ------------------------------------------------------------------
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    # не отвечаем на старые сообщения
    if update.message.date and update.message.date < BOT_START_TIME:
        return

    chat_id = update.effective_chat.id

    text = update.message.text
    user = update.effective_user
    low  = text.lower()

    # 1) базовые очки и markdown/контекст (score + reply)
    delta2, reply2 = score_message(text, user.first_name)
    if delta2:
    # сохраняем очки
        add_score(chat_id, user.id, user.username or user.full_name, delta2)
    # reply2 содержит либо фанфару (CAPSLOCK) либо оскорбление (lowercase penalty)
    if reply2:
        await update.message.reply_markdown(reply2)
    # если положительный счёт без custom reply, отвечаем простым «Гойда!»
    elif delta2 > 0:
    # случайный ответ из библиотеки
        reply = random.choice(GOYDA_FALLBACK)
        await update.message.reply_text(reply)


    # 2) анализ (extra)
    extra = analyse_goyda(text)
    if extra:
        add_score(chat_id, user.id, user.username or user.full_name, extra)

    # 3) автотревоги
    if any(w in low for w in ("свинорейх", "свиналенд", "саловейх", "салорейх")):
        mentions = await _tag_all(context, update.effective_chat.id)
        await update.message.reply_text(f"🚨 СВИННАЯ ТРЕВОГА 🚨 {mentions}")
    if any(w in low for w in ("хохол", "Хохол", "хахол", "хохлы", "хахлы", "хохлюга", "хахлюга", "Хахол", "хахлы", "пидор")):
        mentions = await _tag_all(context, update.effective_chat.id)
        await update.message.reply_text("🛡️ Упоимянут хохол, правда за нами!")

    topic = detect_topic(text)         
    if topic == "hoi4":
        await update.message.reply_text("😔 Бог оставил этот мир (Хойка detected).")
    elif topic == "wt":
        await update.message.reply_text("🔥 War Thunder detected — укрывайтесь!")
    if "кокаколя" in low:
        await update.message.reply_text("Не произноси в суе имя Вождя!")

    # 5) Warhammer-детектор
    if any(kw in low for kw in WAHA_KEYWORDS):
        phrase = random.choice(WAHA_PHRASES).format(user=user.username or user.first_name)
        await update.message.reply_text(phrase)

    # 6) Фембой-детектор
    delta_fb = femboy_score_delta(text)
    if delta_fb:
        # accumulate points
        add_femboy(chat_id, user.id, delta_fb)
        # check for winner only
        perc = get_femboy(chat_id, user.id)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if perc >= 100 and not has_femboy_winner_today(chat_id, today):
            await update.message.reply_text(
                f"🌸🌸🌸 Главный фембой дня: @{user.username or user.first_name} — 100%! 🎉"
            )
            set_femboy_winner(chat_id, today)
            reset_femboy(chat_id)
    
    # 0) Детектор украинской мовы
    if re.search(r"[ґҐєЄіІїЇ]", text):
        with open(GIF_DIR / "ukr.mp4", "rb") as gif:
            await update.message.reply_animation(gif)
        return
    # 0-A) Сообщения про Linux
    if any(kw in low for kw in LINUX_KEYWORDS):
        with open(LINUX_GIF, "rb") as gif:
            await update.message.reply_animation(gif)
        return

    # 0-B) Поддержка Украины — случайная гифка
    if any(phrase in low for phrase in UA_SUPPORT_PHRASES):
        if UA_GIFS:                    
            path = random.choice(UA_GIFS)
            try:
                with open(path, "rb") as gif:
                    await update.message.reply_animation(gif)
            except FileNotFoundError:
                # файл пропал — ничего не шлём
                pass
        return
    # 0-C) Шутки про админа/создателя
    if any(w in low for w in ADMIN_JOKE_WORDS):
        with open(ADMIN_GIF, "rb") as gif:
            await update.message.reply_animation(gif)
        return
    # 0-D) Упоминание батюшки
    if "@kotionochekkk" in low:
        msg = random.choice(BATYUSHKA_PHRASES)
        try:
            with open(BATYUSHKA_GIF, "rb") as gif:
                await update.message.reply_animation(gif, caption=msg)
        except FileNotFoundError:
            await update.message.reply_text(msg)
        return

    # 0-E) Упоминание админа
    if "@ardoran_wolperlinger" in low:
        try:
            with open(GIF_DIR / "adminGoida.mp4", "rb") as gif:
                await update.message.reply_animation(
                    gif, caption="Ох зря ты пинганул админа, пока он трогает траву, без бана решения не будет..."
                )
        except FileNotFoundError:
            await update.message.reply_text(
                "Ох зря ты пинганул админа, пока он трогает траву, без бана решения не будет..."
            )
        return
    # 0-d-1) → стикер
    if any(b in low for b in BATYUSHKA_TRIGGERS):
        sticker_id = random.choice(BATYUSHKA_STICKERS)
        try:
            # Явно указываем named-аргумент sticker
            await update.message.reply_sticker(sticker=sticker_id)
        except Exception as e:
            logging.error(f"Ошибка отправки стикера {sticker_id}: {e}")
        return
# ------------------------------------------------------------------
#  /goyda — объединённый рейтинг
async def cmd_goyda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    top = get_top(chat_id, 3)
    bottom = get_bottom(chat_id, 3)

    ranks_top = ["🏆 Гойда!", "🥰 Поднагойди", "😘 Гойди"]
    ranks_bot = ["😡 Антигойда", "😠 почти прогойдил", "😔 не угойдил"]

    lines = []
    for (u, s), rank in zip(top, ranks_top):
        lines.append(f"{rank}: {u} ({s})")

    lines.append("———")

    for (u, s), rank in zip(bottom, ranks_bot):
        lines.append(f"{rank}: {u} ({s})")

    await update.message.reply_text("\n".join(lines))

# ------------------------------------------------------------------
#  /admin  – панель
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (is_main_admin(update) or is_creator(update)):
        return

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("↻ Рестарт", callback_data="admin_restart"),
        InlineKeyboardButton("👁 Статистика", callback_data="admin_stats"),
    ]])
    await update.message.reply_text("🔧 Admin panel:", reply_markup=kb)

async def admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    # only allow creator or main admins
    if not (is_main_admin(update) or is_creator(update)):
        await q.answer()  # silently acknowledge, no rights
        return

    admin_id = update.effective_user.id
    if q.data == "admin_restart":
        await q.answer(text="Перезапуск инициирован 🔄", show_alert=True)
        import sys, os, signal
        os.kill(os.getpid(), signal.SIGINT)
        return
    elif q.data == "admin_kaznit":
        pending_actions[admin_id]["action"] = "kaznit"
        await q.answer()
        await context.bot.send_message(admin_id, "Кого казнить? Пришлите @username в ответ.")
    elif q.data == "admin_titul":
        pending_actions[admin_id]["action"] = "titul"
        await q.answer()
        await context.bot.send_message(admin_id, "Формат: @user новый_титул")
    elif q.data == "admin_femprocent":
        pending_actions[admin_id]["action"] = "femprocent"
        await q.answer()
        await context.bot.send_message(admin_id, "Формат: @user ±N (например +10)")
    elif q.data == "admin_iskazi":
        pending_actions[admin_id]["action"] = "iskazi"
        await q.answer()
        await context.bot.send_message(admin_id, "Кого искажать? Пришлите @username.")
    elif q.data == "admin_bot_say":
        pending_actions[admin_id]["action"] = "bot_say"
        await q.answer()
        await context.bot.send_message(admin_id, "Что сказать от имени бота?")
    elif q.data == "admin_ukaz":
        pending_actions[admin_id]["action"] = "ukaz"
        await q.answer()
        await context.bot.send_message(admin_id, "Введите текст указа.")
    elif q.data == "admin_v_podval":
        pending_actions[admin_id]["action"] = "v_podval"
        await q.answer()
        await context.bot.send_message(admin_id, "Кто сослан в подвал? Введите @username.")
    elif q.data == "admin_ochistit":
        pending_actions[admin_id]["action"] = "ochistit"
        await q.answer()
        await context.bot.send_message(admin_id, "Кто очищен святой гойдой? Введите @username.")
    elif q.data == "admin_pokaisa":
        pending_actions[admin_id]["action"] = "pokaisa"
        await q.answer()
        await context.bot.send_message(admin_id, "Введите имя кающегося.")
    elif q.data == "admin_femboy_random":
        pending_actions[admin_id]["action"] = "femboy_random"
        await q.answer()
        await context.bot.send_message(admin_id, "Выполняется случайный выбор фембоя.")
    elif q.data == "admin_experiment":
        pending_actions[admin_id]["action"] = "experiment"
        await q.answer()
        await context.bot.send_message(admin_id, "Введите экспериментальные данные.")

# ------------------------------------------------------------------
#  /femboy – случайный «главный фембой»
async def cmd_femboy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    members = [m.user for m in await chat.get_administrators()] + \
              [update.effective_user]
    winner = random.choice(members)
    await update.message.reply_text(f"🌸 Сегодня главный фембой чата — @{winner.username or winner.first_name}!")

# ------------------------------------------------------------------
async def cmd_femboy_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    perc = get_femboy(chat_id, user_id)
    bar = progress_bar(perc)
    await update.message.reply_text(f"🌸 Твоя фембойность: {bar} {perc}%")

# ------------------------------------------------------------------
# асинхронная версия: собираем @username админов/участников
async def _tag_all(ctx, chat_id: int) -> str:
    members = await ctx.bot.get_chat_administrators(chat_id)
    names = [f"@{m.user.username}" for m in members if m.user.username]
    return " ".join(names)

# ------------------------------------------------------------------


# ─────────────────────────────────────────────────────────────────
# Админские команды
# ─────────────────────────────────────────────────────────────────
CREATOR_ID: int = 2629375962          # id @KOKAKOLYA24
MAIN_ADMIN_IDS: set[int] = {1239146968, 5100009483}  # id DiplomastersRU, Ardoran…

def is_creator(update: Update) -> bool:
    return update.effective_user.id == CREATOR_ID

def is_main_admin(update: Update) -> bool:
    return update.effective_user.id in MAIN_ADMIN_IDS or is_creator(update)

# helper to delete invoking message
async def _delete_invoking_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception:
            pass

async def cmd_bot_say(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (is_main_admin(update) or is_creator(update)):
        return
    await _delete_invoking_message(update, context)
    user = update.effective_user
    text = update.message.text.partition(" ")[2].strip()
    if not text:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="…"
        )
        return
    # лимит: только Царь без ограничений, админы — до 100 в сутки
    key = f"say_count:{user.id}:{datetime.utcnow().date()}"
    count = context.chat_data.get(key, 0)
    if not is_creator(update) and count >= 1999:
        await update.message.reply_text("Лимит команд /бот_скажи исчерпан на сегодня.")
        return
    context.chat_data[key] = count + 1
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

async def cmd_kaznit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_main_admin(update):
        return
    await _delete_invoking_message(update, context)
    args = context.args
    if not args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Кого казнить? Укажи @username.")
        return
    chat_id = update.effective_chat.id
    target_id = await resolve_user_by_username(chat_id, args[0], context.bot)
    if not target_id:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Не нашёл пользователя.")
        return

    # 20% шанс извиниться
    if random.random() < 0.2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Извините, @{args[0].lstrip('@')} оказался неприкосновенным.")
    else:
        reset_scores(chat_id)               # сброс гойды
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🩸 @{args[0].lstrip('@')} обвинён в ереси. Очки обнулены."
        )

async def cmd_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_main_admin(update):
        return
    await _delete_invoking_message(update, context)
    if len(context.args) < 2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Используй: /титул @user <название>")
        return
    chat_id = update.effective_chat.id
    target_mention = context.args[0]
    title = " ".join(context.args[1:])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🎖 {target_mention} — {title}")

async def cmd_femboy_adjust(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_main_admin(update):
        return
    await _delete_invoking_message(update, context)
    if len(context.args) != 2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Используй: /фемпроцент @user +10")
        return
    chat_id = update.effective_chat.id
    target = context.args[0]
    delta = int(context.args[1])
    target_id = await resolve_user_by_username(chat_id, target, context.bot)
    if not target_id:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Не нашёл пользователя.")
        return
    # применяем
    add_femboy(chat_id, target_id, delta)
    perc = get_femboy(chat_id, target_id)
    bar = progress_bar(perc)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{target} стал более фембоем на {delta}%. Сейчас: {bar} {perc}%"
    )

async def cmd_twist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_main_admin(update):
        return
    await _delete_invoking_message(update, context)
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Кого искажать? /искази @user")
        return
    chat_id = update.effective_chat.id
    target = context.args[0]
    uid = await resolve_user_by_username(chat_id, target, context.bot)
    if not uid:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Не нашёл пользователя.")
        return
    # достаём последнее сообщение из context.chat_data (нужно сохранять в on_message)
    last = context.chat_data.get(f"last_msg:{uid}")
    if not last:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Нет последнего сообщения.")
        return
    # примитивная замена слов
    twisted = last.replace("гойда", "хойда").replace("Гойда", "Хойда")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"«{twisted}»")

async def cmd_ukaz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_creator(update):
        return
    await _delete_invoking_message(update, context)
    text = update.message.text.partition(" ")[2].strip()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"📜 Царский указ от @{CREATOR}:\n«{text}»"
    )

async def cmd_to_dungeon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_creator(update):
        return
    await _delete_invoking_message(update, context)
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Кого сослать? /в_подвал @user")
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{context.args[0]} сослан в подвал размышлять над анти-гойдовской сущностью.")

async def cmd_cleanse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_creator(update):
        return
    await _delete_invoking_message(update, context)
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Кого очищать? /очистить @user")
        return
    # сброс фембойности
    cid = update.effective_chat.id
    uname = context.args[0].lstrip("@")
    member = await context.bot.get_chat_member(cid, uname)
    reset_femboy(cid, member.user.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{context.args[0]} очищен святой гойдой. Фембой-налёт 0%.")

async def cmd_repent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_creator(update):
        return
    await _delete_invoking_message(update, context)
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Команда: /покайся @user")
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Напиши: «Я грешен, ибо не произносил “Гойду” как следует.»")

# 7) Панель админа /админка
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # проверка прав
    if not (is_main_admin(update) or is_creator(update)):
        return

    # запоминаем, из какого группового чата вызвали панель
    pending_actions[update.effective_user.id] = {
        "chat_id": update.effective_chat.id,
        "action": None,
    }

    # Кнопки панели
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("↻ Restart",     callback_data="admin_restart"),
            InlineKeyboardButton("👁 Stats",      callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton("⚡ Казнить",     callback_data="admin_kaznit"),
            InlineKeyboardButton("🏷 Титул",       callback_data="admin_titul"),
        ],
        [
            InlineKeyboardButton("💯 Фемпроцент",  callback_data="admin_femprocent"),
            InlineKeyboardButton("🔀 Искази",      callback_data="admin_iskazi"),
        ],
        [
            InlineKeyboardButton("🎭 Сказать",     callback_data="admin_bot_say"),
            InlineKeyboardButton("📜 Указ",        callback_data="admin_ukaz"),
        ],
        [
            InlineKeyboardButton("⛓ В подвал",     callback_data="admin_v_podval"),
            InlineKeyboardButton("🧼 Очистить",    callback_data="admin_ochistit"),
        ],
        [
            InlineKeyboardButton("🙏 Покайся",     callback_data="admin_pokaisa"),
            InlineKeyboardButton("🌸 Фембой дня",  callback_data="admin_femboy_random"),
        ],
        [
            InlineKeyboardButton("🧪 Эксперимент", callback_data="admin_experiment"),
        ],
    ])

    # если команда вызвана из группового чата ─ удаляем оригинальное сообщение
    if update.effective_chat.type != "private":
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception:
            pass  # нет прав удалить ─ игнорируем

    # отправляем панель в личку администратору
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="🔧 Admin Panel:",
        reply_markup=kb
    )


# ---- Обработка ответов в личке на действия админа ----
async def on_private_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in pending_actions:
        return
    info = pending_actions[uid]
    action = info.get("action")
    group_id = info.get("chat_id")
    if not action or not group_id:
        return

    arg = update.message.text.strip()

    if action == "kaznit":
        await context.bot.send_message(group_id, f"🩸 {arg} обвинён в ереси. Очки обнулены.")
    elif action == "titul":
        parts = arg.split(maxsplit=1)
        if len(parts) == 2:
            await context.bot.send_message(group_id, f"🎖 {parts[0]} — {parts[1]}")
    elif action == "femprocent":
        await context.bot.send_message(group_id, f"Команда /femprocent: {arg}")
    elif action == "iskazi":
        await context.bot.send_message(group_id, f"Команда /iskazi: {arg}")
    elif action == "bot_say":
        await context.bot.send_message(group_id, arg)
    elif action == "ukaz":
        await context.bot.send_message(group_id, f"📜 Царский указ: \n«{arg}»")
    elif action == "v_podval":
        await context.bot.send_message(group_id, f"{arg} сослан в подвал.")
    elif action == "ochistit":
        await context.bot.send_message(group_id, f"{arg} очищен святой гойдой.")
    elif action == "pokaisa":
        await context.bot.send_message(group_id, "Напиши: ‘Я грешен, ибо не произносил Гойду как следует.’")
    elif action == "femboy_random":
        await context.bot.send_message(group_id, "🌸 Главный фембой выбран случайно! 🌸")
    elif action == "experiment":
        await context.bot.send_message(group_id, random.choice(["Эксперимент 1", "Эксперимент 2"]))

    pending_actions.pop(uid, None)

async def cmd_experiment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (is_main_admin(update) or is_creator(update)):
        return
    await _delete_invoking_message(update, context)
    ans = random.choice([
        "Фембой превращён в гойдобота.",
        "Генерал Гойда в строю!",
        "Вы активировали секретный уровень: Мавзолей Мяу."
    ])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=ans)

async def cmd_femboy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (is_main_admin(update) or is_creator(update)):
        return
    await _delete_invoking_message(update, context)
    chat = update.effective_chat
    members = [m.user for m in await chat.get_administrators()] + \
              [update.effective_user]
    winner = random.choice(members)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🌸 Сегодня главный фембой чата — @{winner.username or winner.first_name}!")

async def cmd_femboy_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete_invoking_message(update, context)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    perc = get_femboy(chat_id, user_id)
    bar = progress_bar(perc)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🌸 Твоя фембойность: {bar} {perc}%")


# ------------------------------------------------------------------
# Unified handler registration
def register_handlers(app):
    # Обработка всех текстовых сообщений
    # обрабатываем текст ТОЛЬКО из групп/супергрупп
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
            on_message
        )
    )

    # Команда общего рейтинга
    app.add_handler(CommandHandler("goyda", cmd_goyda))
    app.add_handler(MessageHandler(filters.Regex(r"^/goyda(_топ)?"), cmd_goyda))

    # Панель админа и callback
    app.add_handler(CommandHandler("admin", show_admin_panel))
    # Handle all admin_* callback buttons
    app.add_handler(CallbackQueryHandler(admin_cb, pattern=r"^admin_"))

    # Обработка ответов в личке для админских действий
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, on_private_reply))

    # Админские (и царские) команды
    app.add_handler(CommandHandler("kaznit", cmd_kaznit))
    app.add_handler(CommandHandler("titul", cmd_title))
    app.add_handler(CommandHandler("femprocent", cmd_femboy_adjust))
    app.add_handler(CommandHandler("iskazi", cmd_twist))
    app.add_handler(CommandHandler("bot_skazhi", cmd_bot_say))
    app.add_handler(CommandHandler("ukaz", cmd_ukaz))
    app.add_handler(CommandHandler("v_podval", cmd_to_dungeon))
    app.add_handler(CommandHandler("ochistit", cmd_cleanse))
    app.add_handler(CommandHandler("pokaisa", cmd_repent))
    app.add_handler(CommandHandler("experiment", cmd_experiment))
    app.add_handler(CommandHandler("femboy", cmd_femboy_self))
    app.add_handler(CommandHandler("femboy_random", cmd_femboy))

    # Обработчик новых участников
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
