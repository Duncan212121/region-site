#!/usr/bin/env python3
"""Собирает каталог на главной и страницы отдельных авто из data/cars.json.

Запуск:  python3 build.py
Трогает: index.html (блоки между маркерами), <slug>.html, privacy.html, sitemap.xml
"""

import json
import pathlib
import re
from html import escape

ROOT = pathlib.Path(__file__).parent
SITE = "https://region-702.ru"

METRIKA = """<!-- Yandex.Metrika counter -->
<script type="text/javascript">
   (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
   m[i].l=1*new Date();
   for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
   k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
   (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
   ym(109256790, "init", {clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true});
</script>
<noscript><div><img src="https://mc.yandex.ru/watch/109256790" style="position:absolute; left:-9999px;" alt="" /></div></noscript>
<!-- /Yandex.Metrika counter -->"""

COUNTRIES = {
    "cn": ("🇨🇳", "Китай", "30–45 дней"),
    "kr": ("🇰🇷", "Корея", "30–45 дней"),
    "ae": ("🇦🇪", "ОАЭ", "30–45 дней"),
    "kg": ("🇰🇬", "Кыргызстан", "5–10 дней"),
}


def rub(price):
    """3850000 -> '3 850 000 ₽' с неразрывными пробелами."""
    if not price:
        return "по запросу"
    return f"{price:,}".replace(",", " ") + " ₽"


def shared_blocks():
    """Шапку, мобильное меню, кнопки мессенджеров и подвал берём с главной,
    чтобы правка в одном месте расходилась по всем страницам авто."""
    home = (ROOT / "index.html").read_text(encoding="utf-8")

    def grab(pattern):
        m = re.search(pattern, home, re.S)
        if not m:
            raise SystemExit(f"не нашёл блок в index.html: {pattern}")
        return m.group(0)

    blocks = {
        "fab": grab(r'<div class="fab-stack">.*?\n</div>'),
        "nav": grab(r"<nav id=\"nav\">.*?</nav>"),
        "mob": grab(r'<div class="mob" id="mob">.*?\n</div>'),
        "footer": grab(r"<footer>.*?</footer>"),
    }
    # на странице авто якорь #contacts должен вести на главную
    for key in ("nav", "mob", "footer"):
        blocks[key] = re.sub(r'href="#([a-z]+)"', r'href="/#\1"', blocks[key])
    return blocks


def operator_line(company, missing):
    """Как оператор представлен в политике. У самозанятого нет ОГРН — он
    опознаётся по ФИО и ИНН, поэтому строка собирается по-разному."""
    form = company.get("форма", "").strip().lower()

    def need(key):
        val = str(company.get(key, "")).strip()
        if val:
            return escape(val)
        missing.add(key)
        return f'<span class="doc-todo">не заполнено: {escape(key)}</span>'

    if form == "самозанятый":
        return (
            f"{need('фио')}, применяющий специальный налоговый режим "
            f'«Налог на профессиональный доход», ИНН {need("инн")}'
        )
    if form == "ип":
        return f"Индивидуальный предприниматель {need('фио')}, ИНН {need('инн')}, ОГРНИП {need('огрн')}"
    return f"{need('название')}, ИНН {need('инн')}, ОГРН {need('огрн')}"


def fill_company(text, company, missing):
    """Подставляет реквизиты вместо {{ключ}}. Незаполненные подсвечиваем,
    чтобы пустое место было видно и на странице, и в консоли сборки."""

    def sub(m):
        key = m.group(1)
        if key == "оператор":
            return operator_line(company, missing)
        val = company.get(key, "")
        if val:
            return escape(str(val))
        missing.add(key)
        return f'<span class="doc-todo">не заполнено: {escape(key)}</span>'

    return re.sub(r"\{\{([^}]+)\}\}", sub, text)


def simple_page(title, description, slug, content, blocks):
    """Текстовая страница — политика конфиденциальности и подобные."""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{escape(title)} — Регион 702</title>
<meta name="description" content="{escape(description)}">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="{SITE}/{slug}">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=Geologica:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css">
</head>
<body>

{blocks['nav']}

{blocks['mob']}

<main class="doc">
  <nav class="crumbs" aria-label="Хлебные крошки">
    <a href="/">Главная</a><span>/</span><span class="crumb-now">{escape(title)}</span>
  </nav>
  <h1 class="doc-title">{escape(title)}</h1>
  {content}
  <div class="cp-back"><a href="/">← На главную</a></div>
</main>

{blocks['footer']}

<script>
const nav=document.getElementById('nav');
window.addEventListener('scroll',()=>nav.classList.toggle('s',scrollY>50));
function toggleMob(){{document.getElementById('mob').classList.toggle('on')}}
</script>
</body>
</html>
"""


def car_meta(car):
    """Страна, срок доставки и подпись года — в одном месте, чтобы карточка
    и страница машины не разъезжались."""
    flag, country, default_days = COUNTRIES[car["country"]]
    days = car.get("days") or default_days
    year = car.get("year") or 0
    title = f'{car["name"]} {year}'.strip() if year else car["name"]
    return flag, country, days, year, title


def small(path):
    """Путь к уменьшенной копии, если она есть рядом с крупной."""
    sm = path.replace(".jpg", "-sm.jpg")
    return sm if (ROOT / sm.lstrip("/")).exists() else path


def price_block(car, prefix="от"):
    if not car.get("price"):
        return f'<div class="price-wrap"><div class="price">Договорная</div></div>'
    return (
        f'<div class="price-wrap"><div class="price-from">{prefix}</div>'
        f'<div class="price">{rub(car["price"])}</div></div>'
    )


def card(car):
    """Карточка авто в каталоге на главной."""
    flag, country, days, year, title = car_meta(car)
    if car.get("photos"):
        src = small(f'/img/cars/{car["slug"]}/{car["photos"][0]}')
        shot = (
            f'<div class="car-shot"><img class="car-img" src="{src}" '
            f'alt="{escape(title)}" loading="lazy"></div>'
        )
    else:
        shot = '<div class="car-shot car-nophoto"><span>Фото готовится</span></div>'

    yr = f' <span class="car-yr">{year}</span>' if year else ""
    state = (f'<span class="car-state">{escape(car["состояние"])}</span>'
             if car.get("состояние") else "")
    short = f'<div class="car-short">{escape(car["short"])}</div>' if car.get("short") else ""
    return (
        f'    <a class="car r" href="/{car["slug"]}.html">'
        f"{shot}"
        f'<div class="car-body">'
        f'<div class="car-origin">{flag} {country}{state}</div>'
        f'<div class="car-name">{escape(car["name"])}{yr}</div>'
        f"{short}"
        f'<div class="car-foot">{price_block(car)}'
        f'<div class="car-time">⏱ {days}</div>'
        f"</div></div></a>"
    )


def cta_tile(count):
    """Карточка-призыв в конце каталога. Растягивается ровно на пустые ячейки
    трёхколоночной сетки, поэтому каталог всегда остаётся ровным прямоугольником."""
    span = 3 - (count % 3) if count % 3 else 3
    return (
        f'    <div class="car car-cta r" style="grid-column:span {span}">'
        f'<div class="cta-in">'
        f'<div class="cta-t">Не нашли свою модель?</div>'
        f'<p class="cta-d">Привезём любой автомобиль под ваш запрос и бюджет — '
        f'от подбора и видеопроверки до ключей в руках.</p>'
        f'<div class="cta-btns">'
        f'<a href="#contacts" class="btn-g">Рассчитать стоимость</a>'
        f'<a href="https://t.me/region_702auto" target="_blank" rel="noopener" class="btn-o">Смотреть в Telegram</a>'
        f'</div></div></div>'
    )


def car_page(car, blocks):
    """Отдельная страница автомобиля."""
    flag, country, days, year, title = car_meta(car)
    slug, name = car["slug"], car["name"]
    photos = [f"/img/cars/{slug}/{p}" for p in car["photos"]]

    seo_title = car.get("seo_title") or f"{title} под ключ из {country} — Регион 702, Уфа"
    meta_desc = car.get("seo_description") or car.get("short") or (
        f"{title} под ключ из {country} — импорт с доставкой по России. Регион 702, Уфа."
    )
    keywords = (
        f'\n<meta name="keywords" content="{escape(car["keywords"])}">'
        if car.get("keywords") else ""
    )

    if photos:
        main_shot = f'<div class="cg-main"><img id="cgShot" src="{photos[0]}" alt="{escape(title)}"></div>'
        og_image = f'\n<meta property="og:image" content="{SITE}{photos[0]}">'
    else:
        main_shot = '<div class="cg-main cg-nophoto"><span>Фотографии готовятся</span></div>'
        og_image = ""

    gallery = ""
    if len(photos) > 1:
        thumbs = "\n        ".join(
            f'<button class="cg-thumb{" on" if i == 0 else ""}" onclick="showShot(this,\'{p}\')" '
            f'aria-label="Фото {i + 1}">'
            f'<img src="{small(p)}" alt="{escape(title)} — фото {i + 1}" loading="lazy"></button>'
            for i, p in enumerate(photos)
        )
        gallery = f'\n      <div class="cg-thumbs">\n        {thumbs}\n      </div>'

    blocks_html = []

    if car.get("description") or car.get("кому подходит"):
        paras = "\n        ".join(f"<p>{escape(p)}</p>" for p in car.get("description", []))
        aside = ""
        if car.get("кому подходит"):
            aside = (
                f'\n      <div class="cp-aside"><span class="cp-aside-t">Кому подходит</span>'
                f'<p>{escape(car["кому подходит"])}</p></div>'
            )
        blocks_html.append(
            f'\n  <div class="cp-block">\n    <h2 class="cp-h2">Как привозим</h2>\n'
            f'    <div class="cp-text">\n        {paras}\n    </div>{aside}\n  </div>'
        )

    if car.get("options"):
        items = "\n        ".join(f"<li>{escape(o)}</li>" for o in car["options"])
        blocks_html.append(
            f'\n  <div class="cp-block">\n    <h2 class="cp-h2">Сильные стороны</h2>\n'
            f'    <ul class="opts">\n        {items}\n    </ul>\n  </div>'
        )

    if car.get("specs"):
        first = next(iter(car["specs"].values()))
        groups = car["specs"] if isinstance(first, dict) else {"": car["specs"]}
        parts = []
        for group_name, rows in groups.items():
            head = f'\n    <h3 class="specs-h3">{escape(group_name)}</h3>' if group_name else ""
            body = "\n        ".join(
                f'<div class="spec"><div class="spec-k">{escape(k)}</div>'
                f'<div class="spec-v">{escape(str(v))}</div></div>'
                for k, v in rows.items()
            )
            parts.append(f'{head}\n    <div class="specs">\n        {body}\n    </div>')
        blocks_html.append(
            f'\n  <div class="cp-block">\n    <h2 class="cp-h2">Характеристики</h2>'
            f'{"".join(parts)}\n  </div>'
        )

    if car.get("faq"):
        items = "\n      ".join(
            f'<div class="fq"><button class="fq-q" onclick="toggleFq(this)">'
            f'<span class="fq-qt">{escape(f["вопрос"])}</span><div class="fq-ico">+</div></button>'
            f'<div class="fq-ans"><div class="fq-ai">{escape(f["ответ"])}</div></div></div>'
            for f in car["faq"]
        )
        blocks_html.append(
            f'\n  <div class="cp-block">\n    <h2 class="cp-h2">Частые вопросы</h2>\n'
            f'    <div class="faq-list">\n      {items}\n    </div>\n  </div>'
        )

    schema = {
        "@context": "https://schema.org",
        "@type": "Car",
        "name": title,
        "brand": name.split()[0],
        "description": meta_desc,
        "offers": {
            "@type": "Offer",
            "priceCurrency": "RUB",
            "availability": "https://schema.org/PreOrder",
            "seller": {"@type": "AutoDealer", "name": "Регион 702", "areaServed": "RU"},
        },
    }
    if year:
        schema["modelDate"] = year
    if photos:
        schema["image"] = SITE + photos[0]
    if car.get("price"):
        schema["offers"]["price"] = car["price"]

    state_badge = (f'<span class="car-state">{escape(car["состояние"])}</span>'
                   if car.get("состояние") else "")

    highlights = ""
    if car.get("highlights"):
        cells = "\n        ".join(
            f'<div class="hl"><div class="hl-v">{escape(str(v))}</div>'
            f'<div class="hl-k">{escape(k)}</div></div>'
            for k, v in car["highlights"].items()
        )
        highlights = f'\n      <div class="hls">\n        {cells}\n      </div>'

    wa = escape(f"Здравствуйте, интересует {name} из {country}")
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{escape(seo_title)}</title>
<meta name="description" content="{escape(meta_desc)}">{keywords}
<link rel="canonical" href="{SITE}/{slug}.html">
<meta property="og:type" content="product">
<meta property="og:title" content="{escape(seo_title)}">
<meta property="og:description" content="{escape(meta_desc)}">{og_image}
<meta property="og:url" content="{SITE}/{slug}.html">
<meta property="og:site_name" content="Регион 702">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=Geologica:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css">
<script type="application/ld+json">
{json.dumps(schema, ensure_ascii=False, indent=2)}
</script>
{METRIKA}
</head>
<body>

{blocks['fab']}

{blocks['nav']}

{blocks['mob']}

<main class="cp">
  <nav class="crumbs" aria-label="Хлебные крошки">
    <a href="/">Главная</a><span>/</span><a href="/#catalog">Каталог</a><span>/</span><span class="crumb-now">{escape(title)}</span>
  </nav>

  <div class="cp-top">
    <div class="cp-gallery">
      {main_shot}{gallery}
    </div>

    <div class="cp-side">
      <div class="car-origin">{flag} {country}{state_badge}</div>
      <h1 class="cp-title">{escape(name)}{f' <em>{year}</em>' if year else ''}</h1>
      <div class="cp-price">{price_block(car, prefix="Под ключ от")}</div>
      <p class="cp-note">Покупка + логистика + таможня + утильсбор + документы.
      Точную стоимость рассчитаем под вашу комплектацию.</p>
      <div class="cp-facts">
        <div class="cp-fact"><div class="cp-fact-k">Срок доставки</div><div class="cp-fact-v">{days}</div></div>
        <div class="cp-fact"><div class="cp-fact-k">Видеопроверка</div><div class="cp-fact-v">Бесплатно</div></div>
      </div>{highlights}
      <a href="/#contacts" class="btn-g cp-cta">Рассчитать стоимость</a>
      <a href="https://wa.me/79378561566?text={wa}" target="_blank" rel="noopener" class="btn-o cp-cta">Спросить в WhatsApp</a>
    </div>
  </div>
{''.join(blocks_html)}
  <div class="cp-back"><a href="/#catalog">← Ко всем автомобилям</a></div>
</main>

{blocks['footer']}

<script>
const nav=document.getElementById('nav');
window.addEventListener('scroll',()=>nav.classList.toggle('s',scrollY>50));
function toggleMob(){{document.getElementById('mob').classList.toggle('on')}}
function showShot(btn,src){{
  document.getElementById('cgShot').src=src;
  document.querySelectorAll('.cg-thumb').forEach(t=>t.classList.remove('on'));
  btn.classList.add('on');
}}
function toggleFq(btn){{
  const it=btn.closest('.fq'),wasOpen=it.classList.contains('open');
  document.querySelectorAll('.fq.open').forEach(f=>f.classList.remove('open'));
  if(!wasOpen)it.classList.add('open');
}}
const observer=new IntersectionObserver(e=>e.forEach(x=>{{if(x.isIntersecting)x.target.classList.add('on')}}),{{threshold:.08}});
document.querySelectorAll('.r').forEach(el=>observer.observe(el));
</script>
</body>
</html>
"""


def replace_block(html, marker, content):
    return re.sub(
        rf"(  *<!-- {marker}:НАЧАЛО[^\n]*-->\n).*?( *<!-- {marker}:КОНЕЦ -->)",
        lambda m: f"{m.group(1)}{content}{m.group(2)}",
        html,
        flags=re.S,
    )


def gallery(folder, css_class, alt, onclick=""):
    """Собирает галерею из всего, что лежит в папке. Порядок — по имени файла,
    поэтому фотографии удобно называть 01.jpg, 02.jpg и так далее."""
    files = sorted(
        f.name for f in (ROOT / folder).iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if not files:
        return "", 0
    click = f' onclick="{onclick}"' if onclick else ""
    rows = "\n".join(
        f'    <div class="{css_class}"{click}>'
        f'<img src="/{folder}/{f}" alt="{alt}" loading="lazy"></div>'
        for f in files
    )
    return rows + "\n", len(files)


def main():
    data = json.loads((ROOT / "data/cars.json").read_text(encoding="utf-8"))
    cars = data["cars"]
    blocks = shared_blocks()

    # страницы собираем для всех, включая черновики — чтобы было что смотреть
    for car in cars:
        (ROOT / f"{car['slug']}.html").write_text(car_page(car, blocks), encoding="utf-8")

    # в каталог попадает всё, кроме явно скрытого
    published = [c for c in cars if c.get("status") != "скрыто"]
    grid = "\n".join(card(c) for c in published)
    grid += "\n" + cta_tile(len(published))
    home_path = ROOT / "index.html"
    home = home_path.read_text(encoding="utf-8")
    home = replace_block(home, "КАТАЛОГ", f'  <div class="cars-grid">\n{grid}\n  </div>\n')

    clients, n_clients = gallery("img/clients", "cli-photo", "Клиент Регион 702 со своим автомобилем")
    home = replace_block(home, "КЛИЕНТЫ", f'  <div class="cli-grid r">\n{clients}  </div>\n')

    hidden = [c for c in cars if c.get("status") == "скрыто"]
    if hidden:
        links = ", ".join(
            f'<a href="/{c["slug"]}.html">{escape(c["name"])}</a>' for c in hidden
        )
        more = (f'  <p class="cat-more r">Также возим под заказ: {links} — '
                f'фотографии этих моделей готовим, стоимость назовём по запросу.</p>\n')
    else:
        more = ""
    home = replace_block(home, "ЕЩЁ", more)

    reviews, n_reviews = gallery(
        "img/reviews", "rv-card", "Отзыв клиента на Авито", onclick="openLB(this)"
    )
    home = replace_block(home, "ОТЗЫВЫ", f'      <div class="rv-grid r">\n{reviews}      </div>\n')

    home_path.write_text(home, encoding="utf-8")

    # политика конфиденциальности
    company = json.loads((ROOT / "data/company.json").read_text(encoding="utf-8"))
    missing = set()
    body = fill_company(
        (ROOT / "data/privacy.html").read_text(encoding="utf-8"), company, missing
    )
    (ROOT / "privacy.html").write_text(
        simple_page(
            "Политика конфиденциальности",
            "Как Регион 702 обрабатывает и защищает персональные данные посетителей сайта.",
            "privacy.html",
            body,
            blocks,
        ),
        encoding="utf-8",
    )

    # в карту сайта попадают все страницы машин, даже скрытые из каталога:
    # они существуют по своим адресам и уже проиндексированы
    urls = ["/", "/china.html", "/korea.html", "/kyrgyzstan.html"]
    urls += [f"/{c['slug']}.html" for c in cars]
    body = "\n".join(
        f"  <url><loc>{SITE}{u}</loc></url>" for u in urls
    )
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n',
        encoding="utf-8",
    )

    drafts = [c["slug"] for c in cars if not c.get("photos")]
    print(f"страниц авто: {len(cars)} | в каталоге: {len(published)}")
    print(f"фото клиентов: {n_clients} | скриншотов отзывов: {n_reviews}")
    if drafts:
        print("ждут фотографий:")
        for d in drafts:
            print(f"  · {d}")
    if missing:
        print("\nВ политике конфиденциальности не заполнены реквизиты — data/company.json:")
        for key in sorted(missing):
            print(f"  · {key}")


if __name__ == "__main__":
    main()
