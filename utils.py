import re
from functools import lru_cache
import regex as re, random, math

# ---  Гойда-ядро  -------------------------------------------------
_GOYDA_CORE = r"[гg]+[оo0]+[йyу]+[дd]+"        # без 'а' пока
# 'а' (или её лат. аналоги) может быть, а может и нет
_GOYDA_OPT_A = r"(?:[аa@]+)?"

# --- глагольные/прочие суффиксы ----------------------------------
_GOYDA_SUFFIX = r"(?:ть|ить|им|ит|ём|ем|те|ете|и)?"

_GOYDA_RE = re.compile(
    rf"(?<!@)\b{_GOYDA_CORE}{_GOYDA_OPT_A}{_GOYDA_SUFFIX}\b",
    re.IGNORECASE | re.UNICODE,
)

MD_BOLD  = re.compile(r"\*(.+?)\*|__(.+?)__", re.S)
MD_UNDER = re.compile(r"_(.+?)_", re.S)
UPPER_TOKEN = re.compile(r"^\p{Lu}+$", re.U)
_BOLD_RE      = re.compile(r"\*(.*?)\*")
_UNDER_RE     = re.compile(r"__([^_]+)__")

def contains_bold(text: str) -> bool:
    return bool(_BOLD_RE.search(text))

def contains_underline(text: str) -> bool:
    return bool(_UNDER_RE.search(text))

def count_exclamations(txt: str) -> int:
    return min(3, txt.count("!"))

def is_upper(txt: str) -> bool:
    words = txt.split()
    return words and all(UPPER_TOKEN.match(w) for w in words)

# === 2.2 -очистка для «украинского детекта» ===
CYR_CHARS = re.compile(r"\p{IsCyrillic}+", re.U)
def is_ukrainian(text: str) -> bool:
    return CYR_CHARS.search(text) and ("ї" in text.lower() or "є" in text.lower())

_BOLD_RE = re.compile(r"\*(.*?)\*|__(.*?)__")         
_EXCLAM_RE = re.compile(r"!+")                       
_UPPER_WORD_RE = re.compile(r"^[^\W\d_]+$")          

def has_goyda(text: str) -> bool:
    return bool(_GOYDA_RE.search(text))

def count_exclamations(text: str) -> int:
    """Return min(3, number of '!') for scoring."""
    return min(3, len(_EXCLAM_RE.findall(text)))

def contains_bold(text: str) -> bool:
    return bool(_BOLD_RE.search(text))

def is_upper(text: str) -> bool:
    words = text.split()
    return words and all(_UPPER_WORD_RE.match(w) for w in words)

HOI4_WORDS = {"хойка", "hoi4", "hearts of iron", "хойке"}
WT_WORDS   = {"war thunder", "вт", "вар тандер", "wartunder"}

def detect_topic(text: str) -> str | None:
    low = text.lower()
    if any(w in low for w in HOI4_WORDS):
        return "hoi4"
    if any(w in low for w in WT_WORDS):
        return "wt"
    return None
# --- фембой инцелы –––––
FEM_TRIGGERS = {
    # Самоидентификация и признания
    "я фембой", "я фембойчик", "я трап", "я трапик", "я маленький", "я мальчик в платьице",
    "девочка по паспорту", "мальчик в юбке", "мальчик-девочка", "девочка с членом", "самоидентификация",
    "фемка", "фембой", "фембойка", "фемик", "femboy", "femboi", "trap", "трапик", "sissy",
    
    # Тело, внешний вид, повадки
    "нюдс", "нюдсы", "у меня силикон", "у меня попка", "маленькая попка", "гладкий животик",
    "гладкий", "пушистик", "лапочки", "гладить", "шлёпать", "обнять", "обнимашки", "тактильность",
    "шлёпни меня", "приласкай", "поцелуйчик", "писюн", "пиписечка", "мяу", "мяук", "кяу", "ня", "ня~",
    "платьице", "юбочка", "косички", "бусики", "губки бантиком", "реснички", "ушки", "хвостик",
    
    # Поведение, речь
    "аниме-девочка", "анимешка", "я няшка", "няшка", "я ня", "эмоция", "эмоции переполняют", "у меня стрессик",
    "токсик", "я токсик", "тикток", "делаю тиктоки", "я тиктокер", "кусь", "ляпка", "милота", "угрозик",
    "погладь", "поняшка", "кофточка", "тянка", "шрамки", "не хочу жить", "поплачу", "ангст", "онлайн-депрессия",
    
    # Ирония и сетевой фембой-флуд
    "ботик", "котик", "котик мяу", "котик умер", "я котик", "грустный фембой", "фембой плачет", 
    "хочу на ручки", "погладь меня", "раздень", "шлёпни", "дай обнимашку", "дай обнимашки", 
    "заскринь попку", "контент для бусти", "попа на камеру", "ты бы меня трахнул?", "я бы себя трахнул",
    "мне 15", "я в чулках", "у меня шрамы", "у меня депрессия", "у меня тревожность", "независимая фемка"
}

def femboy_score_delta(text: str) -> int:
    """+10% за каждое уникальное триггер-слово (макс +20 за одно сообщение)."""
    low = text.lower()
    hits = {w for w in FEM_TRIGGERS if w in low}
    return min(20, 10 * len(hits))

def progress_bar(percent: int, width: int = 10) -> str:
    """█-бар длиной width символов."""
    filled = int(percent / 100 * width)
    return "▮" * filled + "▯" * (width - filled)

# === Warhammer-ключи ===
WAHA_KEYWORDS = {
    # Основные термины
    "ваха", "вархаммер", "вархамер", "вархаммэр", "вархаммир", "вархаммер 40к", "40k", "40к", "wh40k",
    "империум", "империум человечества", "император", "император человечества",
    "примарх", "примархи", "примарха", "примархи империума",
    "астартес", "спейс марин", "спейсмарин", "космодесант", "космодесантник", "адептус астартес",
    
    # Фракции и расовые термины
    "хаос", "хаоситы", "хаосит", "еретик", "еретики", "корн", "тзинч", "нургл", "сланеш",
    "орки", "орк", "гретчин", "эльдар", "дарки", "дарк эльдар", "тёмные эльдары", "крафтуэльдар",
    "тау", "империя тау", "некроны", "некрон", "тираниды", "жнецы", "левиафан", "генокрады",
    
    # Лор и термины вселенной
    "терра", "механикус", "адептус механикус", "сервитор", "инквизиция", "инквизитор", "ересь", 
    "ересь хоруса", "хорус", "лоялисты", "титаны", "имперский титан", "варлорд", "банеблейд",
    "сакрарий", "екклезиархия", "псайкер", "навигатор", "астропат", "варп", "имматериум", "варп-путь",
    
    # Игровые и мемные формы
    "вафля", "вашечка", "варпфля", "мехваха", "лолвах", "мехаваха", "вахастик", "вафхаммер", 
    "ваха-кек", "гримдарк", "grimdark", "grim dark", "40k memes", "изваха", "из-вахи", "флэшгит",
    
    # Мисспеллинги и шумовые формы
    "вввархаммер", "ввваха", "вахах", "ваххамер", "вархаммерр", "спейссмммаринн", "пппримарх", 
    "асттартес", "астартэс", "астратес", "вахаааа", "ваахаа", "варпп", "ерессь", "империииум"
}

def detect_waha(text: str) -> bool:
    """
    Возвращает True, если в тексте встречается любое Warhammer-ключевое слово.
    """
    low = text.lower()
    return any(kw in low for kw in WAHA_KEYWORDS)