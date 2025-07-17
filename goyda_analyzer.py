from pathlib import Path
import random
import logging
import re
import json
from itertools import groupby
from utils import (
    _GOYDA_RE,
    contains_bold,
    contains_underline,
    count_exclamations,
    is_upper,
)
from config import TRIGGERS_PATH


# шаблоны реакций
INSULTS = [
    "выпей ацетона {user}",
    "сидишь скулишь, {user}? а надо киев брать!",
    "{user}, ищи себя на сайте миротворец",
    "Стоит искоренить такую ересь",
    "А не хочешь подкачаться?"
]
FANFARES = [
    "🎉 ЗА НАМИ МОСКВА! {user}!",
    "🚀 _Мать Обамы_ ПРОБИТА: {user}!",
    "🥁 ТАК ДЕРЖАТЬ, _{user}_!",
    "📢 Всем чатам слышим твою оргию — {user}!",
    "🚀Услышал тебя родной – _{user}_!"
]

MAX_BASE = 6
MAX_CONTEXT = 5

# ── загружаем список триггеров один раз при импорте ────────────────────
with open(TRIGGERS_PATH, encoding="utf-8") as fp:
    TRIGGERS: list[str] = [t.lower() for t in json.load(fp)]

def score_message(text: str, username: str) -> tuple[int, str|None]:
    """
    Возвращает (score, reply):
    • Base = 1 +1 за каждую группу подряд идущих одинаковых букв >1 в слове «гойда»;
    • +1 за CAPSLOCK всего слова;
    • +1 за жирный текст;
    • +1 за подчёркнутый текст;
    • +1 за любое триггерное слово в тексте;
    При полном строчном «гойда» штраф -5 и выбор INSULTS.
    """
    # нет «гойды» → 0
    match = _GOYDA_RE.search(text)
    if not match:
        return 0, None

    word = match.group(0)
    # строго строчная «гойда» → штраф
    if word.strip() == word.lower():
        return -5, random.choice(INSULTS).format(user=username)

    # базовая оценка: 1 + группы повторов >1
    base = 1
    for char, grp in groupby(word.lower()):
        if len(list(grp)) > 1:
            base += 1
    # ограничиваем
    base = min(base, MAX_BASE)

    # бонусы: по одному за каждое условие
    bonus = 0
    if word.isupper():
        bonus += 1
    if contains_bold(text):
        bonus += 1
    if contains_underline(text):
        bonus += 1
    lower = text.lower()
    if any(trig in lower for trig in TRIGGERS):
        bonus += 1

    score = base + bonus

    # ответ только для CAPSLOCK
    reply = None
    if is_upper(text):
        reply = random.choice(FANFARES).format(user=username)

    return score, reply


# ----------------------------------------------------------------------
#  Вспомогательный анализ для быстрой «штраф/бонус» без reply
#  Используется в handlers.py как analyse_goyda(text) -> int
# ----------------------------------------------------------------------
def analyse_goyda(text: str) -> int:
    """
    Упрощённая оценка:
    • +5  если вся «гойда» в CAPSLOCK.
    • −5  если сообщение состоит ТОЛЬКО из строчной 'гойда'.
    •  0  иначе.
    """
    if not _GOYDA_RE.search(text):
        return 0

    stripped = text.strip()
    if stripped == stripped.lower():
        # строго маленькая
        return -5
    if stripped.isupper():
        return +5
    return 0