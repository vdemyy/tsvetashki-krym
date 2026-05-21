"""Идемпотентное наполнение БД: явления, места, события."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from database import SessionLocal
from models import Event, Phenomenon, Place
from services.icon_map import DEFAULT_BY_KIND


def _get_or_create_place(
    db,
    name: str,
    *,
    region: str | None,
    subregion: str | None,
    latitude: float,
    longitude: float,
) -> Place:
    pl = db.scalars(select(Place).where(Place.name == name)).first()
    if pl:
        return pl
    pl = Place(
        name=name,
        region=region,
        subregion=subregion,
        latitude=latitude,
        longitude=longitude,
    )
    db.add(pl)
    db.flush()
    return pl


def _get_or_create_phenomenon(
    db,
    slug: str,
    *,
    name: str,
    kind: str,
    category: str | None,
    description: str | None,
    typical_season: str | None,
    icon_lucide: str | None,
    main_photo_url: str = "",
    website_url: str | None = None,
    water_temp_c: float | None = None,
) -> Phenomenon:
    ph = db.scalars(select(Phenomenon).where(Phenomenon.slug == slug)).first()
    if ph:
        return ph
    ph = Phenomenon(
        slug=slug,
        name=name,
        kind=kind,
        category=category,
        description=description,
        typical_season=typical_season,
        icon_emoji="",
        icon_lucide=icon_lucide or DEFAULT_BY_KIND.get(kind, "sparkles"),
        main_photo_url=main_photo_url or "",
        website_url=website_url or "",
        water_temp_c=water_temp_c,
    )
    db.add(ph)
    db.flush()
    return ph


def _ensure_event(
    db,
    phenomenon: Phenomenon,
    place: Place,
    *,
    start_date: date,
    peak_date: date,
    end_date: date,
    intensity: int = 3,
    phase_history: list | None = None,
    notes: str | None = None,
) -> None:
    ex = db.scalars(
        select(Event).where(
            Event.phenomenon_id == phenomenon.id,
            Event.place_id == place.id,
            Event.start_date == start_date,
        )
    ).first()
    if ex:
        return
    db.add(
        Event(
            phenomenon_id=phenomenon.id,
            place_id=place.id,
            start_date=start_date,
            peak_date=peak_date,
            end_date=end_date,
            intensity=intensity,
            phase_history=phase_history,
            notes=notes,
        )
    )


def _backfill_icons(db) -> None:
    for ph in db.scalars(select(Phenomenon)).all():
        if not ph.icon_lucide:
            ph.icon_lucide = DEFAULT_BY_KIND.get(ph.kind or "", "sparkles")
    db.commit()


def ensure_seed() -> None:
    db = SessionLocal()
    try:
        # --- места ---
        places = {
            "kerch": _get_or_create_place(
                db,
                "Сады у Керчи",
                region="Восточный Крым",
                subregion="Керчь",
                latitude=45.357,
                longitude=36.468,
            ),
            "turg": _get_or_create_place(
                db,
                "Тургеневка (лавандовые поля)",
                region="Южный Крым",
                subregion="Бахчисарайский район",
                latitude=44.724,
                longitude=33.905,
            ),
            "nbs": _get_or_create_place(
                db,
                "Никитский ботанический сад",
                region="Южный Крым",
                subregion="Ялта",
                latitude=44.508,
                longitude=34.235,
            ),
            "lug": _get_or_create_place(
                db,
                "Степь у Керчи",
                region="Восточный Крым",
                subregion="Керченский полуостров",
                latitude=45.298,
                longitude=35.772,
            ),
            "kok": _get_or_create_place(
                db,
                "Коктебель (холмы)",
                region="Южный Крым",
                subregion="Феодосия",
                latitude=44.962,
                longitude=35.238,
            ),
            "laspi": _get_or_create_place(
                db,
                "Ласпи (тропа и скалы)",
                region="Южный Крым",
                subregion="Балаклавский округ",
                latitude=44.468,
                longitude=33.598,
            ),
            "fiolent": _get_or_create_place(
                db,
                "Мыс Фиолент",
                region="Севастополь",
                subregion="Геройский район",
                latitude=44.593,
                longitude=33.468,
            ),
            "ai_petri": _get_or_create_place(
                db,
                "Яйла Ай-Петри",
                region="Южный Крым",
                subregion="Ялта",
                latitude=44.452,
                longitude=34.058,
            ),
            "sev_bay": _get_or_create_place(
                db,
                "Севастопольская бухта",
                region="Севастополь",
                subregion="Центр",
                latitude=44.616,
                longitude=33.525,
            ),
            "sudak": _get_or_create_place(
                db,
                "Берег у Судакской крепости",
                region="Южный Крым",
                subregion="Судак",
                latitude=44.838,
                longitude=34.973,
            ),
            "bahch": _get_or_create_place(
                db,
                "Бахчисарай (Ханский двор)",
                region="Южный Крым",
                subregion="Бахчисарай",
                latitude=44.748,
                longitude=33.876,
            ),
            "yevp": _get_or_create_place(
                db,
                "Окрестности Евпатории",
                region="Западный Крым",
                subregion="Евпатория",
                latitude=45.190,
                longitude=33.364,
            ),
            "alushta": _get_or_create_place(
                db,
                "Алупка (Воронцовский парк)",
                region="Южный Крым",
                subregion="Ялта",
                latitude=44.419,
                longitude=34.055,
            ),
            "foros": _get_or_create_place(
                db,
                "Форос (смотровые)",
                region="Южный Крым",
                subregion="Ялта",
                latitude=44.392,
                longitude=33.787,
            ),
            "sudak_bay": _get_or_create_place(
                db,
                "Бухта Судак",
                region="Южный Крым",
                subregion="Судак",
                latitude=44.845,
                longitude=34.985,
            ),
            "catalchauk": _get_or_create_place(
                db,
                "Чатал-Чауш (ущелье)",
                region="Южный Крым",
                subregion="Бахчисарайский район",
                latitude=44.698,
                longitude=33.812,
            ),
            "kapchik": _get_or_create_place(
                db,
                "Мыс Капчик",
                region="Восточный Крым",
                subregion="Керченский полуостров",
                latitude=45.032,
                longitude=35.312,
            ),
            "tajron": _get_or_create_place(
                db,
                "Тарханкут (мыс)",
                region="Западный Крым",
                subregion="Черноморский район",
                latitude=45.315,
                longitude=32.985,
            ),
            "melas": _get_or_create_place(
                db,
                "Мелас (бухта)",
                region="Восточный Крым",
                subregion="Феодосия",
                latitude=44.912,
                longitude=35.318,
            ),
            "uchan_su": _get_or_create_place(
                db,
                "Водопад Учан-Су",
                region="Южный Крым",
                subregion="Ялта",
                latitude=44.438,
                longitude=34.132,
            ),
            "massandra": _get_or_create_place(
                db,
                "Массандра (парки)",
                region="Южный Крым",
                subregion="Ялта",
                latitude=44.485,
                longitude=34.215,
            ),
            "gurzuf": _get_or_create_place(
                db,
                "Гурзуф (Аю-Даг)",
                region="Южный Крым",
                subregion="Ялта",
                latitude=44.618,
                longitude=34.412,
            ),
            "kara_dag": _get_or_create_place(
                db,
                "Кара-Даг (заповедник)",
                region="Восточный Крым",
                subregion="Феодосия",
                latitude=44.872,
                longitude=35.485,
            ),
            "salgir": _get_or_create_place(
                db,
                "Салгир (долина)",
                region="Восточный Крым",
                subregion="Симферополь",
                latitude=44.912,
                longitude=34.128,
            ),
            "balaklava": _get_or_create_place(
                db,
                "Балаклава (бухта)",
                region="Севастополь",
                subregion="Балаклавский округ",
                latitude=44.482,
                longitude=33.612,
            ),
            "hermon": _get_or_create_place(
                db,
                "Чатыр-Даг (пещеры)",
                region="Южный Крым",
                subregion="Бахчисарайский район",
                latitude=44.712,
                longitude=34.218,
            ),
            "novy_svet": _get_or_create_place(
                db,
                "Новый Свет (тропа)",
                region="Южный Крым",
                subregion="Судак",
                latitude=44.892,
                longitude=35.112,
            ),
        }

        lavanda = _get_or_create_phenomenon(
            db,
            "lavanda-turgenevka",
            name="Лаванда (Тургеневка)",
            kind="flowering",
            category="цветы · популярное",
            description="Фиолетовые поля — один из самых узнаваемых сезонов Южного берега.",
            typical_season="Середина июня — начало июля.",
            icon_lucide="flower-2",
            website_url="",
        )
        sakura = _get_or_create_phenomenon(
            db,
            "sakura-nikitsky",
            name="Сакура и декоративные вишни (НБС)",
            kind="flowering",
            category="деревья",
            description="Цветение в коллекциях Никитского ботанического сада.",
            typical_season="Конец марта — апрель.",
            icon_lucide="tree-deciduous",
            website_url="https://nikitasad.ru/",
        )
        demo_may = _get_or_create_phenomenon(
            db,
            "demo-lugovye-travy",
            name="Луговые цветы (весна)",
            kind="flowering",
            category="популярное",
            description="Демо-событие «в разгаре» для весенней ленты.",
            typical_season="Апрель — май.",
            icon_lucide="sprout",
        )
        maki = _get_or_create_phenomenon(
            db,
            "maki-koktebel",
            name="Маки и степные мотивы",
            kind="flowering",
            category="цветы",
            description="Красные акценты на фоне вулканических холмов.",
            typical_season="Конец апреля — май.",
            icon_lucide="flower-2",
        )
        glycine = _get_or_create_phenomenon(
            db,
            "glycine-alupka",
            name="Глициния (Воронцовский парк)",
            kind="flowering",
            category="лианы",
            description="Каскады глицинии на беседках и стенах парка.",
            typical_season="Май — начало июня.",
            icon_lucide="flower-2",
        )
        pions = _get_or_create_phenomenon(
            db,
            "piony-nbs",
            name="Пионы (НБС)",
            kind="flowering",
            category="цветы · коллекции",
            description="Пик цветения пионов в коллекционных участках.",
            typical_season="Конец мая — июнь.",
            icon_lucide="flower-2",
        )
        pods = _get_or_create_phenomenon(
            db,
            "podsnezhniki-laspi",
            name="Подснежники и ранние лесные цветы",
            kind="flowering",
            category="редкое",
            description="Тенистые склоны у моря — ранние лесные эфемероиды.",
            typical_season="Март — апрель.",
            icon_lucide="snowflake",
        )
        zakat = _get_or_create_phenomenon(
            db,
            "zakat-fiorent",
            name="Закаты с «зелёным лучом» (шанс)",
            kind="visual",
            category="небо · оптика",
            description="Ясная морская дымка и горизонт — редкий оптический эффект.",
            typical_season="Тёплые сезоны, ясные вечера.",
            icon_lucide="sunset",
        )
        tuman = _get_or_create_phenomenon(
            db,
            "tuman-more",
            name="Туман и море облаков",
            kind="visual",
            category="пейзаж",
            description="Слоистая дымка над водой и низкая облачность у берега.",
            typical_season="Весна и осень, штилевая погода.",
            icon_lucide="cloud-fog",
        )
        vin = _get_or_create_phenomenon(
            db,
            "festival-vina-yalta",
            name="Фестиваль вина (пример)",
            kind="activity",
            category="фестивали",
            description="Демо-событие: проверьте даты на официальных сайтах перед поездкой.",
            typical_season="Осень.",
            icon_lucide="grape",
            website_url="https://yalta.rk.gov.ru/",
        )
        chery = _get_or_create_phenomenon(
            db,
            "cherry-kerch",
            name="Черешня (сады)",
            kind="harvest",
            category="урожай",
            description="Ранние сорта на востоке полуострова — ориентир по сезону.",
            typical_season="Конец мая — июнь.",
            icon_lucide="cherry",
        )
        delf = _get_or_create_phenomenon(
            db,
            "delfiny-sudak",
            name="Дельфины у берега (шанс)",
            kind="animals",
            category="море",
            description="Спокойное море, утро или вечер — чаще стаи афалин.",
            typical_season="Тёплые месяцы.",
            icon_lucide="waves",
        )
        lavr = _get_or_create_phenomenon(
            db,
            "lavrovoshhok-sevastopol",
            name="Цветение лавровишни",
            kind="flowering",
            category="деревья",
            description="Белые гроздья соцветий в городских садах и на набережных.",
            typical_season="Апрель — май.",
            icon_lucide="leaf",
        )
        tulip = _get_or_create_phenomenon(
            db,
            "tulipany-yevpatoriya",
            name="Тюльпаны (поля и парки)",
            kind="flowering",
            category="цветы",
            description="Весенние посадки и декоративные поля — даты зависят от погоды.",
            typical_season="Апрель.",
            icon_lucide="flower-2",
        )
        halo = _get_or_create_phenomenon(
            db,
            "halo-ai-petri",
            name="Гало и перистые облака (высокогорье)",
            kind="visual",
            category="небо",
            description="На яйле чаще встречаются перистые перья и оптические кольца.",
            typical_season="Круглый год при ясной атмосфере.",
            icon_lucide="sun",
        )
        med = _get_or_create_phenomenon(
            db,
            "yarmarka-meda",
            name="Ярмарка мёда (пример)",
            kind="activity",
            category="ярмарки",
            description="Демо-даты — уточняйте у организаторов.",
            typical_season="Лето.",
            icon_lucide="store",
        )
        rose = _get_or_create_phenomenon(
            db,
            "rozovyj-sad-massandra",
            name="Розовый сад (Массандра)",
            kind="flowering",
            category="цветы · парки",
            description="Коллекционные розы в Массандровском парке.",
            typical_season="Май — июнь.",
            icon_lucide="flower",
        )
        iris = _get_or_create_phenomenon(
            db,
            "касатики-тарханкут",
            name="Касатики (ирисы) на Тарханкуте",
            kind="flowering",
            category="цветы · редкое",
            description="Дикорастущие ирисы на степных склонах.",
            typical_season="Май.",
            icon_lucide="flower-2",
        )
        magnolia = _get_or_create_phenomenon(
            db,
            "магнолия-гурзуф",
            name="Магнолии (Гурзуф)",
            kind="flowering",
            category="деревья",
            description="Цветение крупнолистных магнолий в парках.",
            typical_season="Апрель — май.",
            icon_lucide="tree-deciduous",
        )
        peony_wild = _get_or_create_phenomenon(
            db,
            "дикие-пионы-чатал-чауш",
            name="Дикие пионы (ущелья)",
            kind="flowering",
            category="цветы · редкое",
            description="Лесные пионы в тенистых ущельях.",
            typical_season="Май.",
            icon_lucide="flower-2",
        )
        sea_anemone = _get_or_create_phenomenon(
            db,
            "актинии-тарханкут",
            name="Актинии на мелководье (Тарханкут)",
            kind="animals",
            category="море · редкое",
            description="При ясной воде видны на камнях у берега.",
            typical_season="Июнь — сентябрь.",
            icon_lucide="waves",
        )
        stork = _get_or_create_phenomenon(
            db,
            "аисты-симферополь",
            name="Гнездование аистов",
            kind="animals",
            category="птицы",
            description="Белые аисты возвращаются к гнездовьям.",
            typical_season="Март — август.",
            icon_lucide="bird",
        )
        lilac = _get_or_create_phenomenon(
            db,
            "сирень-симферополь",
            name="Сирень (Симферополь и окрестности)",
            kind="flowering",
            category="кустарники",
            description="Массовое цветение сирени в садах и парках.",
            typical_season="Апрель — май.",
            icon_lucide="leaf",
        )
        night_bloom = _get_or_create_phenomenon(
            db,
            "ночное-цветение-кара-даг",
            name="Ночное цветение (степные растения)",
            kind="flowering",
            category="редкое",
            description="Некоторые степные растения цветут ночью с ароматом.",
            typical_season="Июнь — июль.",
            icon_lucide="moon",
        )
        dolphin_sudak = _get_or_create_phenomenon(
            db,
            "дельфины-судак",
            name="Дельфины у Судака",
            kind="animals",
            category="море",
            description="Прохождение стай у побережья.",
            typical_season="Июль — сентябрь.",
            icon_lucide="waves",
        )
        chestnut = _get_or_create_phenomenon(
            db,
            "каштан-ялта",
            name="Конский каштан (Ялта)",
            kind="flowering",
            category="деревья",
            description="Цветение каштанов в городских насаждениях.",
            typical_season="Апрель — май.",
            icon_lucide="tree-deciduous",
        )
        cactus = _get_or_create_phenomenon(
            db,
            "кактусы-новы-свет",
            name="Дикорастущие кактусы (Новый Свет)",
            kind="flowering",
            category="редкое",
            description="Уникальные локальные популяции на скалах.",
            typical_season="Июнь.",
            icon_lucide="flower",
        )
        mist_morning = _get_or_create_phenomenon(
            db,
            "утренний-туман-балклава",
            name="Утренний туман над бухтой (Балаклава)",
            kind="visual",
            category="пейзаж",
            description="Рассветный туман создает мистическую атмосферу.",
            typical_season="Осень — весна.",
            icon_lucide="cloud-fog",
        )
        falcon = _get_or_create_phenomenon(
            db,
            "сокол-чатыр-даг",
            name="Гнездование соколов (Чатыр-Даг)",
            kind="animals",
            category="птицы · редкое",
            description="Соколы-сапсаны и кречеты на скалах.",
            typical_season="Апрель — июль.",
            icon_lucide="bird",
        )

        lavanda_history = [
            {"year": 2021, "start": "2021-06-16", "peak": "2021-06-25", "end": "2021-07-07"},
            {"year": 2022, "start": "2022-06-10", "peak": "2022-06-22", "end": "2022-07-04"},
            {"year": 2023, "start": "2023-06-12", "peak": "2023-06-24", "end": "2023-07-06"},
        ]

        _ensure_event(
            db,
            lavanda,
            places["turg"],
            start_date=date(2026, 6, 14),
            peak_date=date(2026, 6, 25),
            end_date=date(2026, 7, 6),
            intensity=4,
            phase_history=lavanda_history,
            notes="Прогноз по трём годам.",
        )
        _ensure_event(
            db,
            sakura,
            places["nbs"],
            start_date=date(2026, 3, 28),
            peak_date=date(2026, 4, 8),
            end_date=date(2026, 4, 20),
            intensity=3,
            phase_history=[
                {"year": 2024, "start": "2024-03-30", "peak": "2024-04-06", "end": "2024-04-18"},
                {"year": 2025, "start": "2025-03-26", "peak": "2025-04-05", "end": "2025-04-17"},
            ],
        )
        _ensure_event(
            db,
            demo_may,
            places["lug"],
            start_date=date(2026, 5, 1),
            peak_date=date(2026, 5, 15),
            end_date=date(2026, 5, 28),
            intensity=3,
            phase_history=[
                {"year": 2024, "start": "2024-05-03", "peak": "2024-05-14", "end": "2024-05-27"},
                {"year": 2025, "start": "2025-04-28", "peak": "2025-05-12", "end": "2025-05-25"},
            ],
        )
        _ensure_event(
            db,
            maki,
            places["kok"],
            start_date=date(2026, 5, 5),
            peak_date=date(2026, 5, 18),
            end_date=date(2026, 5, 30),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            glycine,
            places["alushta"],
            start_date=date(2026, 5, 10),
            peak_date=date(2026, 5, 22),
            end_date=date(2026, 6, 5),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            pions,
            places["nbs"],
            start_date=date(2026, 5, 20),
            peak_date=date(2026, 6, 3),
            end_date=date(2026, 6, 18),
            intensity=4,
            phase_history=None,
        )
        _ensure_event(
            db,
            pods,
            places["laspi"],
            start_date=date(2026, 3, 15),
            peak_date=date(2026, 3, 28),
            end_date=date(2026, 4, 12),
            intensity=2,
            phase_history=None,
        )
        _ensure_event(
            db,
            zakat,
            places["fiolent"],
            start_date=date(2026, 5, 1),
            peak_date=date(2026, 8, 15),
            end_date=date(2026, 9, 20),
            intensity=2,
            notes="Длинное «окно» для визуального сезона закатов.",
            phase_history=None,
        )
        _ensure_event(
            db,
            tuman,
            places["sev_bay"],
            start_date=date(2026, 4, 1),
            peak_date=date(2026, 5, 12),
            end_date=date(2026, 10, 1),
            intensity=2,
            phase_history=None,
        )
        _ensure_event(
            db,
            vin,
            places["nbs"],
            start_date=date(2026, 9, 25),
            peak_date=date(2026, 10, 2),
            end_date=date(2026, 10, 8),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            chery,
            places["kerch"],
            start_date=date(2026, 5, 25),
            peak_date=date(2026, 6, 8),
            end_date=date(2026, 6, 25),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            delf,
            places["sudak"],
            start_date=date(2026, 5, 1),
            peak_date=date(2026, 7, 20),
            end_date=date(2026, 9, 15),
            intensity=2,
            phase_history=None,
        )
        _ensure_event(
            db,
            lavr,
            places["sev_bay"],
            start_date=date(2026, 4, 20),
            peak_date=date(2026, 5, 8),
            end_date=date(2026, 5, 22),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            tulip,
            places["yevp"],
            start_date=date(2026, 4, 10),
            peak_date=date(2026, 4, 22),
            end_date=date(2026, 5, 5),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            halo,
            places["ai_petri"],
            start_date=date(2026, 1, 1),
            peak_date=date(2026, 6, 15),
            end_date=date(2026, 12, 31),
            intensity=1,
            notes="Условное «всегда возможно» при ясной погоде.",
            phase_history=None,
        )
        _ensure_event(
            db,
            med,
            places["bahch"],
            start_date=date(2026, 6, 10),
            peak_date=date(2026, 6, 14),
            end_date=date(2026, 6, 16),
            intensity=2,
            phase_history=None,
        )
        _ensure_event(
            db,
            rose,
            places["massandra"],
            start_date=date(2026, 5, 15),
            peak_date=date(2026, 5, 28),
            end_date=date(2026, 6, 12),
            intensity=4,
            phase_history=None,
        )
        _ensure_event(
            db,
            iris,
            places["tajron"],
            start_date=date(2026, 5, 8),
            peak_date=date(2026, 5, 18),
            end_date=date(2026, 5, 28),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            magnolia,
            places["gurzuf"],
            start_date=date(2026, 4, 15),
            peak_date=date(2026, 4, 28),
            end_date=date(2026, 5, 12),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            peony_wild,
            places["catalchauk"],
            start_date=date(2026, 5, 1),
            peak_date=date(2026, 5, 12),
            end_date=date(2026, 5, 22),
            intensity=2,
            phase_history=None,
        )
        _ensure_event(
            db,
            sea_anemone,
            places["tajron"],
            start_date=date(2026, 6, 1),
            peak_date=date(2026, 7, 20),
            end_date=date(2026, 9, 15),
            intensity=2,
            phase_history=None,
        )
        _ensure_event(
            db,
            stork,
            places["salgir"],
            start_date=date(2026, 3, 15),
            peak_date=date(2026, 5, 20),
            end_date=date(2026, 8, 25),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            lilac,
            places["salgir"],
            start_date=date(2026, 4, 20),
            peak_date=date(2026, 5, 5),
            end_date=date(2026, 5, 18),
            intensity=4,
            phase_history=None,
        )
        _ensure_event(
            db,
            night_bloom,
            places["kara_dag"],
            start_date=date(2026, 6, 10),
            peak_date=date(2026, 7, 5),
            end_date=date(2026, 7, 25),
            intensity=1,
            phase_history=None,
        )
        _ensure_event(
            db,
            dolphin_sudak,
            places["sudak_bay"],
            start_date=date(2026, 7, 1),
            peak_date=date(2026, 8, 10),
            end_date=date(2026, 9, 20),
            intensity=2,
            phase_history=None,
        )
        _ensure_event(
            db,
            chestnut,
            places["uchan_su"],
            start_date=date(2026, 4, 12),
            peak_date=date(2026, 4, 25),
            end_date=date(2026, 5, 8),
            intensity=3,
            phase_history=None,
        )
        _ensure_event(
            db,
            cactus,
            places["novy_svet"],
            start_date=date(2026, 6, 5),
            peak_date=date(2026, 6, 18),
            end_date=date(2026, 6, 28),
            intensity=2,
            phase_history=None,
        )
        _ensure_event(
            db,
            mist_morning,
            places["balaklava"],
            start_date=date(2026, 9, 1),
            peak_date=date(2026, 10, 20),
            end_date=date(2026, 11, 30),
            intensity=2,
            phase_history=None,
        )
        _ensure_event(
            db,
            falcon,
            places["hermon"],
            start_date=date(2026, 4, 1),
            peak_date=date(2026, 5, 15),
            end_date=date(2026, 7, 20),
            intensity=2,
            phase_history=None,
        )

        db.commit()
        _backfill_icons(db)
    finally:
        db.close()
