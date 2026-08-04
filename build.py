#!/usr/bin/env python3
"""Собирает каталог на главной и страницы отдельных авто из data/cars.json.

Запуск:  python3 build.py
Трогает: index.html (только блок между маркерами КАТАЛОГ), auto/*.html, sitemap.xml
"""

import json
import pathlib
import re
import shutil
from html import escape

ROOT = pathlib.Path(__file__).parent
SITE = "https://region-702.ru"

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


def fill_company(text, company, missing):
    """Подставляет реквизиты вместо {{ключ}}. Незаполненные подсвечиваем,
    чтобы пустое место было видно и на странице, и в консоли сборки."""

    def sub(m):
        key = m.group(1)
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


def card(car):
    """Карточка авто в каталоге на главной."""
    flag, country, days = COUNTRIES[car["country"]]
    photo = f"/img/cars/{car['slug']}/{car['photos'][0]}"
    short = (
        f'<div class="car-short">{escape(car["short"])}</div>' if car.get("short") else ""
    )
    return (
        f'    <a class="car r" href="/auto/{car["slug"]}.html">'
        f'<div class="car-shot"><img class="car-img" src="{photo}" alt="{escape(car["name"])} {car["year"]}" loading="lazy"></div>'
        f'<div class="car-body">'
        f'<div class="car-origin">{flag} {country}</div>'
        f'<div class="car-name">{escape(car["name"])} <span class="car-yr">{car["year"]}</span></div>'
        f"{short}"
        f'<div class="car-foot">'
        f'<div class="price-wrap"><div class="price-from">от</div><div class="price">{rub(car["price"])}</div></div>'
        f'<div class="car-time">⏱ {days}</div>'
        f"</div></div></a>"
    )


def car_page(car, blocks):
    """Отдельная страница автомобиля."""
    flag, country, days = COUNTRIES[car["country"]]
    slug, name, year = car["slug"], car["name"], car["year"]
    title = f"{name} {year}"
    photos = [f"/img/cars/{slug}/{p}" for p in car["photos"]]

    if car.get("description"):
        desc_html = "\n        ".join(
            f"<p>{escape(p)}</p>" for p in car["description"]
        )
    else:
        desc_html = "<p>Описание готовится. Напишите нам — расскажем всё про эту машину и рассчитаем стоимость под ваш бюджет.</p>"

    meta_desc = car.get("short") or f"{title} под ключ из {country} — импорт с доставкой по России. Регион 702, Уфа."

    gallery = ""
    if len(photos) > 1:
        thumbs = "\n        ".join(
            f'<button class="cg-thumb{" on" if i == 0 else ""}" onclick="showShot(this,\'{p}\')">'
            f'<img src="{p}" alt="{escape(title)} — фото {i + 1}" loading="lazy"></button>'
            for i, p in enumerate(photos)
        )
        gallery = f'\n      <div class="cg-thumbs">\n        {thumbs}\n      </div>'

    specs = ""
    if car.get("specs"):
        rows = "\n        ".join(
            f'<div class="spec"><div class="spec-k">{escape(k)}</div><div class="spec-v">{escape(str(v))}</div></div>'
            for k, v in car["specs"].items()
        )
        specs = f"""
    <div class="cp-block">
      <h2 class="cp-h2">Характеристики</h2>
      <div class="specs">
        {rows}
      </div>
    </div>"""

    options = ""
    if car.get("options"):
        items = "\n        ".join(
            f"<li>{escape(o)}</li>" for o in car["options"]
        )
        options = f"""
    <div class="cp-block">
      <h2 class="cp-h2">Комплектация</h2>
      <ul class="opts">
        {items}
      </ul>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{escape(title)} под ключ из {country} — Регион 702, Уфа</title>
<meta name="description" content="{escape(meta_desc)}">
<link rel="canonical" href="{SITE}/auto/{slug}.html">
<meta property="og:type" content="product">
<meta property="og:title" content="{escape(title)} — от {rub(car['price'])} под ключ">
<meta property="og:description" content="{escape(meta_desc)}">
<meta property="og:image" content="{SITE}{photos[0]}">
<meta property="og:url" content="{SITE}/auto/{slug}.html">
<meta property="og:site_name" content="Регион 702">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=Geologica:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css">
<script type="application/ld+json">
{json.dumps({
    "@context": "https://schema.org",
    "@type": "Car",
    "name": title,
    "brand": name.split()[0],
    "modelDate": year,
    "image": SITE + photos[0],
    "description": meta_desc,
    "offers": {
        "@type": "Offer",
        "price": car["price"],
        "priceCurrency": "RUB",
        "availability": "https://schema.org/PreOrder",
        "seller": {"@type": "AutoDealer", "name": "Регион 702", "areaServed": "RU"},
    },
}, ensure_ascii=False, indent=2)}
</script>
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
      <div class="cg-main"><img id="cgShot" src="{photos[0]}" alt="{escape(title)}"></div>{gallery}
    </div>

    <div class="cp-side">
      <div class="car-origin">{flag} {country}</div>
      <h1 class="cp-title">{escape(name)} <em>{year}</em></h1>
      <div class="cp-price"><span class="price-from">Под ключ от</span><div class="price">{rub(car['price'])}</div></div>
      <p class="cp-note">Покупка + логистика + таможня + утильсбор + документы. Точную стоимость рассчитаем под вашу комплектацию.</p>
      <div class="cp-facts">
        <div class="cp-fact"><div class="cp-fact-k">Срок доставки</div><div class="cp-fact-v">{days}</div></div>
        <div class="cp-fact"><div class="cp-fact-k">Год выпуска</div><div class="cp-fact-v">{year}</div></div>
      </div>
      <a href="/#contacts" class="btn-g cp-cta">Рассчитать стоимость</a>
      <a href="https://wa.me/79378561566?text={escape(f'Здравствуйте, интересует {title}')}" target="_blank" rel="noopener" class="btn-o cp-cta">Спросить в WhatsApp</a>
    </div>
  </div>

  <div class="cp-block">
    <h2 class="cp-h2">Об автомобиле</h2>
    <div class="cp-text">
        {desc_html}
    </div>
  </div>
{specs}{options}
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
    out = ROOT / "auto"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    for car in cars:
        (out / f"{car['slug']}.html").write_text(car_page(car, blocks), encoding="utf-8")

    # в каталог на главной пускаем только готовые
    published = [c for c in cars if c.get("status") == "готово"] or cars
    grid = "\n".join(card(c) for c in published)
    home_path = ROOT / "index.html"
    home = home_path.read_text(encoding="utf-8")
    home = replace_block(home, "КАТАЛОГ", f'  <div class="cars-grid">\n{grid}\n  </div>\n')

    clients, n_clients = gallery("img/clients", "cli-photo", "Клиент Регион 702 со своим автомобилем")
    home = replace_block(home, "КЛИЕНТЫ", f'  <div class="cli-grid r">\n{clients}  </div>\n')

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

    urls = ["/", "/china.html", "/korea.html", "/kyrgyzstan.html"]
    urls += [f"/auto/{c['slug']}.html" for c in published]
    body = "\n".join(
        f"  <url><loc>{SITE}{u}</loc></url>" for u in urls
    )
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n',
        encoding="utf-8",
    )

    drafts = [c["slug"] for c in cars if c.get("status") != "готово"]
    print(f"страниц авто: {len(cars)} | в каталоге: {len(published)}")
    print(f"фото клиентов: {n_clients} | скриншотов отзывов: {n_reviews}")
    if drafts:
        print("черновики (не попадут в каталог, когда появится хоть одно готовое):")
        for d in drafts:
            print(f"  · {d}")
    if missing:
        print("\nВ политике конфиденциальности не заполнены реквизиты — data/company.json:")
        for key in sorted(missing):
            print(f"  · {key}")


if __name__ == "__main__":
    main()
