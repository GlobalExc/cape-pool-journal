#!/usr/bin/env python3
"""The Cape Pool Journal — static site builder.

  python3 build.py                 build the live site into public/ (posts dated in the future stay hidden)
  python3 build.py --preview-ads   also show dashed boxes where ads will go
  python3 build.py --all           also include future-dated (scheduled) posts, for previewing

Posts live in content/*.md with YAML front matter (written by the /admin editor or by hand).
Images live in assets/img/ and are served at /img/.
"""
import hashlib, html, json, os, re, shutil, sys
from datetime import date, datetime, timedelta, timezone
import markdown
import yaml

# ----------------------------------------------------------------- SITE SETTINGS
SITE_NAME = "The Cape Pool Journal"
SITE_URL = "https://cape-pool-journal.netlify.app"  # change to your own domain once bought, e.g. "https://capepooljournal.co.za"
TAGLINE = "Practical pool care, building and fun, written for Cape Town"
BIZ_NAME = "Cape Town Pool Maintenance"
BIZ_URL = "https://capepoolmaintenance.co.za"
PHONE_DISPLAY = "081 422 2181"
PHONE_INTL = "+27814222181"
WHATSAPP = "https://wa.me/27814222181"
AUTHOR = "Success Gray"
AUTHOR_ROLE = "Bookings Manager, Cape Town Pool Maintenance"
AUTHOR_INITIALS = "SG"
HOURS = "Mon–Fri 08:00–17:00 · Sat 08:00–15:00"
CONTACT_EMAIL = ""                                   # e.g. "hello@capepooljournal.co.za" — shown on Contact/Privacy if set

# ----------------------------------------------------------------- ADS & ANALYTICS
# 1. Apply at adsense.google.com once the site is live on its own domain with ~20+ posts.
# 2. When approved, paste your publisher ID below and create ad units in AdSense → Ads → By ad unit,
#    then paste each unit's data-ad-slot number into AD_SLOTS. Rebuild and deploy.
ADSENSE_CLIENT = ""                                  # e.g. "ca-pub-1234567890123456"
AD_SLOTS = {                                         # AdSense ad-unit slot IDs
    "in_article_1": "",                              # in-article unit, after the 2nd section of a post
    "in_article_2": "",                              # in-article unit, deeper in long posts
    "after_article": "",                             # display unit, after the FAQ
    "sidebar": "",                                   # display unit (vertical), sticky sidebar on desktop
    "home_feed": "",                                 # display unit (horizontal), between home sections
    "topic_feed": "",                                # display unit (horizontal), on topic pages
}
GA4_ID = ""                                          # optional Google Analytics 4 ID, e.g. "G-XXXXXXX"
GSC_VERIFICATION = ""                                # optional Google Search Console HTML-tag code
BING_VERIFICATION = ""                               # optional Bing Webmaster Tools code

# ----------------------------------------------------------------- LIVE CHAT (tawk.to)
# tawk.to → Administration → Chat Widget → copy the two IDs from the embed link
# https://embed.tawk.to/<PROPERTY_ID>/<WIDGET_ID>
TAWK_PROPERTY_ID = "6ac14580ae5bb434c47f1f20"
TAWK_WIDGET_ID = "1k41ff0f5"

# ----------------------------------------------------------------- CMS (/admin)
GITHUB_REPO = "GlobalExc/cape-pool-journal"   # set when the GitHub repo exists
GITHUB_BRANCH = "main"

PREVIEW_ADS = "--preview-ads" in sys.argv
INCLUDE_FUTURE = "--all" in sys.argv
TODAY = datetime.now(timezone(timedelta(hours=2))).date()   # Cape Town time (SAST)
ADS_LIVE = bool(ADSENSE_CLIENT)
NEEDS_COOKIE_NOTICE = ADS_LIVE or bool(GA4_ID) or PREVIEW_ADS

# ----------------------------------------------------------------- PATHS
ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "public")

PILLARS = {  # name: (slug, colour, blurb)
    "Care": ("care", "#0e8ba0", "Weekly care, water chemistry and equipment, explained simply."),
    "Problems": ("problems", "#2c8a57", "Green, cloudy, stained or leaking? Diagnose it and fix it."),
    "Seasons": ("seasons", "#c9741f", "What Cape Town's wind, rain and heat do to your pool, month by month."),
    "Building": ("building", "#4f6475", "Building, renovating, heating and making pools safe."),
    "Activities": ("activities", "#cc4b45", "Games, fitness and family days that get the most from your pool."),
}

BRAND = os.path.join(ROOT, "assets", "brand")


def logo_img(white=True, height=44):
    name = "logo-horizontal-white.svg" if white else "logo-horizontal.svg"
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', open(os.path.join(BRAND, name)).read())
    w = round(float(vb.group(1)) * height / float(vb.group(2)))
    return f'<img src="/brand/{name}" alt="{SITE_NAME}" width="{w}" height="{height}">'


def esc(s):
    return html.escape(str(s), quote=True)


def fmt_date(d):
    d = date.fromisoformat(d)
    return f"{d.day} {d.strftime('%B %Y')}"


# ----------------------------------------------------------------- COVER ART
def cover_svg(pillar, seed):
    """Deterministic abstract cover per post — replaced by a real photo when the post sets "image"."""
    slug, col, _ = PILLARS[pillar]
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    r = lambda n, lo=0: lo + (h >> (n * 4)) % 100
    bgs = {"care": ("#0b4f63", "#12a3b8"), "problems": ("#0f4a35", "#3fae74"), "seasons": ("#7a3a0a", "#f0a04b"),
           "building": ("#24323d", "#6f8799"), "activities": ("#7d1f2b", "#f07a5f")}
    a, b = bgs[slug]
    waves = "".join(
        f'<path d="M0 {y} C 200 {y-28} 400 {y+28} 600 {y} S 1000 {y-28} 1200 {y} V 675 H 0 Z" fill="#fff" opacity="{op}"/>'
        for y, op in ((420 + r(1) % 40, .10), (480 + r(2) % 40, .12), (560 + r(3) % 30, .16)))
    motif = {
        "care": "".join(f'<circle cx="{150 + r(i) * 9}" cy="{90 + r(i + 5) * 3}" r="{8 + r(i + 9) % 26}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="3"/>' for i in range(7)),
        "problems": "".join(f'<circle cx="{700 + r(4)}" cy="{230}" r="{40 + k * 46}" fill="none" stroke="#fff" stroke-opacity="{.4 - k * .07}" stroke-width="3"/>' for k in range(5)),
        "seasons": f'<circle cx="{820 + r(4)}" cy="{200}" r="96" fill="#ffd27a" opacity=".9"/><circle cx="{820 + r(4)}" cy="200" r="150" fill="#ffd27a" opacity=".18"/>',
        "building": "".join(f'<rect x="{x}" y="{y}" width="58" height="58" fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="2"/>' for x in range(620, 1200, 64) for y in range(40, 420, 64)),
        "activities": f'<g transform="translate({760 + r(4)} 220)"><circle r="110" fill="#fff" opacity=".92"/><path d="M0-110A110 110 0 0 1 95 55L0 0Z" fill="#ffcf5c"/><path d="M95 55A110 110 0 0 1-95 55L0 0Z" fill="#4fb6d6"/><circle r="16" fill="#fff"/></g>',
    }[slug]
    return (f'<svg viewBox="0 0 1200 675" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(pillar)} illustration" preserveAspectRatio="xMidYMid slice">'
            f'<defs><linearGradient id="g{h % 9999}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'
            f'<rect width="1200" height="675" fill="url(#g{h % 9999})"/>{motif}{waves}</svg>')


# ----------------------------------------------------------------- PHOTOS
PHOTOS = yaml.safe_load(open(os.path.join(ROOT, "photos.yml"), encoding="utf-8"))
PILLAR_PHOTO = {"Care": "how-often-pool-service-cape-town", "Problems": "why-is-my-pool-green", "Seasons": "pool-evaporation-south-easter",
                "Building": "fibreglass-vs-concrete-pool", "Activities": "pool-games-family-activities"}
SEASONS = {  # month: (kicker, heading, text, post slug)
    9: ("September in Cape Town", "Spring clean before the heat arrives.", "Winter rain has diluted everything. A clean-up now means a clear pool in December.", "pool-summer-ready-cape-town"),
    10: ("October in Cape Town", "Spring clean before the heat arrives.", "Winter rain has diluted everything. A clean-up now means a clear pool in December.", "pool-summer-ready-cape-town"),
    11: ("November in Cape Town", "The south-easter is back.", "Expect sand in the baskets, faster evaporation and chlorine that disappears overnight.", "pool-evaporation-south-easter"),
    12: ("December in Cape Town", "Peak season. Keep the chlorine up.", "Heat, holidays and busy pools use chlorine faster than any other month.", "pool-party-checklist"),
    1: ("January in Cape Town", "Hot, dry and windy.", "Top up responsibly and check chlorine after every heatwave.", "pool-evaporation-south-easter"),
    2: ("February in Cape Town", "Late-summer heat waves.", "Green pools appear overnight in February. Here's how to stay ahead.", "why-is-my-pool-green"),
}


def photo_for(p):
    """(src_function, alt, credit_html) for a post: uploaded job photo first, else Unsplash, else None."""
    if p.get("image"):
        src = "/img/" + p["image"]
        return (lambda w: src), p.get("image_alt") or p["title"], ""
    rec = PHOTOS["posts"].get(p["slug"])
    if rec:
        return unsplash(rec)
    return None


def unsplash(rec):
    pid, who, page_id, alt = rec
    src = lambda w: f"https://images.unsplash.com/{pid}?auto=format&fit=crop&w={w}&q=72"
    credit = (f'Photo: <a href="https://unsplash.com/photos/{page_id}?utm_source=cape_pool_journal&utm_medium=referral" rel="noopener">{esc(who)}</a>'
              f' / <a href="https://unsplash.com/?utm_source=cape_pool_journal&utm_medium=referral" rel="noopener">Unsplash</a>')
    return src, alt, credit


def img_tag(ph, sizes="100vw", eager=False, widths=(480, 800, 1200, 1800)):
    src, alt, _ = ph
    srcset = ", ".join(f"{src(w)} {w}w" for w in widths)
    return (f'<img src="{src(widths[-2])}" srcset="{srcset}" sizes="{sizes}" alt="{esc(alt)}" '
            f'loading="{"eager" if eager else "lazy"}" decoding="async" width="1200" height="800"{" fetchpriority=high" if eager else ""}>')


def cover_html(p, eager=False, sizes="(max-width:640px) 100vw, 33vw"):
    ph = photo_for(p)
    if ph:
        return img_tag(ph, sizes, eager)
    return f'<img src="/covers/{p["slug"]}.svg" alt="" loading="{"eager" if eager else "lazy"}" width="1200" height="675">'


def cover_url(p):
    ph = photo_for(p)
    if ph:
        u = ph[0](1200)
        return u if u.startswith("http") else SITE_URL + u
    return f"{SITE_URL}/covers/{p['slug']}.svg"


def site_photo(key):
    return unsplash(PHOTOS["site"][key])


# ----------------------------------------------------------------- ADS
AD_KINDS = {  # slot key: (css kind, AdSense attributes)
    "in_article_1": ("in-article", 'data-ad-layout="in-article" data-ad-format="fluid" style="display:block;text-align:center"'),
    "in_article_2": ("in-article", 'data-ad-layout="in-article" data-ad-format="fluid" style="display:block;text-align:center"'),
    "after_article": ("display", 'data-ad-format="auto" data-full-width-responsive="true" style="display:block"'),
    "sidebar": ("sidebar", 'data-ad-format="vertical" style="display:block"'),
    "home_feed": ("wide", 'data-ad-format="horizontal" data-full-width-responsive="true" style="display:block"'),
    "topic_feed": ("wide", 'data-ad-format="horizontal" data-full-width-responsive="true" style="display:block"'),
}


def ad(key):
    kind, attrs = AD_KINDS[key]
    if ADS_LIVE and AD_SLOTS.get(key):
        return (f'<div class="ad ad-{kind}"><span class="ad-label">Advertisement</span>'
                f'<ins class="adsbygoogle" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{AD_SLOTS[key]}" {attrs}></ins></div>')
    if PREVIEW_ADS:
        return (f'<div class="ad ad-{kind}"><span class="ad-label">Advertisement</span>'
                f'<div class="ad-placeholder">Ad slot · {key.replace("_", " ")}</div></div>')
    return ""  # nothing rendered until AdSense is set up, so no empty gaps


def insert_in_article_ads(body_html):
    """Place in-article ads before the 3rd and 6th H2 so they sit between sections, never inside one."""
    parts = re.split(r"(?=<h2)", body_html)
    out = []
    for i, part in enumerate(parts):
        if i == 3:
            out.append(ad("in_article_1"))
        if i == 6:
            out.append(ad("in_article_2"))
        out.append(part)
    return "".join(out)


# ----------------------------------------------------------------- PAGE SHELL
def head_scripts():
    s = ""
    if ADS_LIVE:
        s += f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>\n'
        s += f'<meta name="google-adsense-account" content="{ADSENSE_CLIENT}">\n'
    if GA4_ID:
        s += (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>'
              f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{GA4_ID}');</script>\n")
    return s


def tawk_script():
    if not TAWK_PROPERTY_ID:
        return ""
    # Loaded 4 seconds after the page so it doesn't slow down the first view (good for Google rankings)
    return ("<script>var Tawk_API=Tawk_API||{},Tawk_LoadStart=new Date();window.addEventListener('load',function(){setTimeout(function(){"
            "var s=document.createElement('script');s.async=true;"
            f"s.src='https://embed.tawk.to/{TAWK_PROPERTY_ID}/{TAWK_WIDGET_ID}';s.charset='UTF-8';s.setAttribute('crossorigin','*');"
            "document.body.appendChild(s);},4000);});</script>")


def nav_html(active=""):
    links = [(f"/topics/{s}/", n) for n, (s, _, _) in PILLARS.items()] + [("/about/", "About")]
    return "".join(f'<a href="{u}"{" aria-current=page" if n == active else ""}>{n}</a>' for u, n in links)


def page(title, description, path, body, jsonld=None, og_type="website", active="", progress=False, og_image=None):
    canonical = SITE_URL + path
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    cookie = ""
    if NEEDS_COOKIE_NOTICE:
        cookie = ('<div class="cookie" role="region" aria-label="Cookie notice"><p>We use cookies for ads and to understand what readers find useful. '
                  '<a href="/privacy/">Privacy policy</a></p><button class="btn" type="button">OK</button></div>')
    footer_topics = "".join(f'<li><a href="/topics/{s}/">{n}</a></li>' for n, (s, _, _) in PILLARS.items())
    og = og_image or "/brand/og-default.png"
    og = og if og.startswith("http") else SITE_URL + og
    og_img = f'<meta property="og:image" content="{og}"><meta property="og:image:alt" content="{esc(title)}">'
    verify = (f'<meta name="google-site-verification" content="{GSC_VERIFICATION}">' if GSC_VERIFICATION else "") + \
             (f'<meta name="msvalidate.01" content="{BING_VERIFICATION}">' if BING_VERIFICATION else "")
    today = TODAY.strftime("%A, %-d %B %Y")
    return f"""<!doctype html>
<html lang="en-ZA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{og_type}"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="{SITE_NAME}"><meta property="og:locale" content="en_ZA">{og_img}
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f7f3ec">{verify}
<link rel="icon" href="/favicon.ico" sizes="32x32"><link rel="icon" href="/brand/mark.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/brand/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="/feed.xml">
<link rel="preconnect" href="https://images.unsplash.com">
<link rel="preload" href="/fonts/fraunces-latin-600-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/newsreader-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/inter-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css?v={ASSET_VER}">
{head_scripts()}{ld}
</head>
<body>
<a class="skip" href="#content">Skip to content</a>
<div class="topbar"><div class="wrap"><span>{today} <span class="tag-line">· Cape Town, South Africa</span></span><a href="{WHATSAPP}">Pool trouble? WhatsApp {PHONE_DISPLAY}</a></div></div>
<header class="site"><div class="wrap">
<a class="brand" href="/" aria-label="{SITE_NAME} home">{logo_img(white=False)}</a>
<button class="menu-btn" type="button" aria-label="Menu" aria-expanded="false"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
<nav class="main" aria-label="Main">{nav_html(active)}</nav>
<a class="btn dark hbtn" href="{BIZ_URL}" rel="noopener">Book a service</a>
</div>{'<div class="progress"></div>' if progress else ''}</header>
<main id="content">{body}</main>
<footer class="site"><div class="wrap">
<div class="cols">
<div class="about">{logo_img(white=True)}<p>{TAGLINE}. Written by the team at {BIZ_NAME}, who look after pools across Cape Town every week.</p></div>
<div><strong>Topics</strong><ul>{footer_topics}</ul></div>
<div><strong>The Journal</strong><ul><li><a href="/about/">About</a></li><li><a href="/contact/">Ask a question</a></li><li><a href="/privacy/">Privacy policy</a></li><li><a href="/terms/">Terms &amp; disclaimer</a></li><li><a href="/feed.xml">RSS feed</a></li></ul></div>
<div><strong>Need a pool pro?</strong><ul><li><a href="{WHATSAPP}">WhatsApp {PHONE_DISPLAY}</a></li><li><a href="{BIZ_URL}">{BIZ_NAME}</a></li><li>{HOURS}</li></ul></div>
</div>
<div class="legal"><span>© {date.today().year} {BIZ_NAME}. All rights reserved.</span><span>Advice is general. Always follow chemical product labels. Photos credited where used.</span></div>
</div></footer>
{cookie}
<script src="/site.js?v={ASSET_VER}" defer></script>
{tawk_script()}
</body></html>"""


def cta_box():
    ph = site_photo("capetown")
    return f"""<aside class="cta"><div class="bg">{img_tag(ph, "700px", widths=(480, 800, 1200, 1600))}</div><div class="in">
<span class="kicker">From the team behind the journal</span>
<h2>Rather swim than scrub?</h2>
<p>{BIZ_NAME} keeps Cape Town pools clear all year with weekly services, green-pool rescues and spring clean-ups.</p>
<div class="actions"><a class="btn light" href="{BIZ_URL}">See service plans</a><a class="btn ghost" href="{WHATSAPP}">WhatsApp {PHONE_DISPLAY}</a></div>
<small>{HOURS}</small></div></aside>"""


def org_ld():
    return {"@context": "https://schema.org", "@type": "LocalBusiness", "@id": BIZ_URL + "/#business",
            "name": BIZ_NAME, "url": BIZ_URL, "telephone": PHONE_INTL,
            "logo": SITE_URL + "/brand/mark-512.png", "image": SITE_URL + "/brand/mark-512.png",
            "areaServed": {"@type": "City", "name": "Cape Town"},
            "address": {"@type": "PostalAddress", "addressLocality": "Cape Town", "addressRegion": "Western Cape", "addressCountry": "ZA"},
            "openingHoursSpecification": [
                {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "opens": "08:00", "closes": "17:00"},
                {"@type": "OpeningHoursSpecification", "dayOfWeek": "Saturday", "opens": "08:00", "closes": "15:00"}]}


# ----------------------------------------------------------------- CONTENT
def load_posts():
    posts, scheduled = [], []
    for fn in sorted(os.listdir(CONTENT)):
        if not fn.endswith(".md"):
            continue
        raw = open(os.path.join(CONTENT, fn), encoding="utf-8").read()
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
        if not m:
            print(f"  ! skipped {fn}: no front matter"); continue
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
        if meta.get("draft"):
            continue
        meta["slug"] = fn[:-3]
        for k in ("date", "updated"):
            if isinstance(meta.get(k), (date, datetime)):
                meta[k] = (meta[k].date() if isinstance(meta[k], datetime) else meta[k]).isoformat()
            elif meta.get(k):
                meta[k] = str(meta[k])[:10]
        meta["updated"] = meta.get("updated") or meta["date"]
        if date.fromisoformat(meta["date"]) > TODAY and not INCLUDE_FUTURE:
            scheduled.append(meta); continue
        md = markdown.Markdown(extensions=["tables", "sane_lists", "toc"], extension_configs={"toc": {"toc_depth": "2"}})
        h = md.convert(body)
        h = h.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
        h = re.sub(r"<p>(<img [^>]+>)</p>", r"<figure>\1</figure>", h)
        h = h.replace("<img ", '<img loading="lazy" decoding="async" ')
        h = h.replace("<li>[ ] ", '<li class="check">').replace("<li>[x] ", '<li class="check done">')
        h = re.sub(r"<ul>(\s*<li class=\"check)", r'<ul class="checklist">\1', h)
        meta["html"] = h
        meta["toc"] = [(t["id"], t["name"]) for t in md.toc_tokens]
        meta["url"] = f"{SITE_URL}/{meta['slug']}/"
        meta["words"] = len(re.sub("<[^>]+>", " ", h).split())
        meta["read"] = f"{max(2, round(meta['words'] / 200))} min"
        meta["faqs"] = [(f["q"], f["a"]) for f in (meta.get("faqs") or [])]
        meta["image"] = (meta.get("image") or "").replace("/img/", "", 1).lstrip("/")
        posts.append(meta)
    posts.sort(key=lambda p: (p["date"], p["title"]), reverse=True)
    for p in sorted(scheduled, key=lambda p: p["date"]):
        print(f"  scheduled {p['date']}  {p['title']}")
    return posts


def card(p, sizes="(max-width:640px) 100vw, (max-width:900px) 50vw, 380px"):
    search = esc(f"{p['title']} {p['description']} {p['pillar']}".lower())
    return f"""<a class="story" href="/{p['slug']}/" data-search="{search}"><div class="ph">{cover_html(p, sizes=sizes)}</div>
<span class="kicker">{p['pillar']}</span><h3>{esc(p['title'])}</h3><p>{esc(p['description'])}</p><span class="meta">{fmt_date(p['updated'])} · {p['read']} read</span></a>"""


def lead_story(p):
    search = esc(f"{p['title']} {p['description']} {p['pillar']}".lower())
    return f"""<a class="lead-story" href="/{p['slug']}/" data-search="{search}"><div class="ph">{cover_html(p, sizes="(max-width:900px) 100vw, 680px")}</div>
<div><span class="kicker">Latest · {p['pillar']}</span><h3>{esc(p['title'])}</h3><p>{esc(p['answer'])}</p><span class="meta">By {AUTHOR} · {fmt_date(p['updated'])} · {p['read']} read</span></div></a>"""


def toc_list(p):
    return "<ol>" + "".join(f'<li><a href="#{i}">{esc(n)}</a></li>' for i, n in p["toc"]) + "</ol>"


def build_post(p, posts):
    slug = PILLARS[p["pillar"]][0]
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in p["faqs"])
    same = [x for x in posts if x["slug"] != p["slug"] and x["pillar"] == p["pillar"]]
    other = [x for x in posts if x["slug"] != p["slug"] and x["pillar"] != p["pillar"]]
    related = (same + other)[:3]
    share_text = esc(f"{p['title']} {p['url']}")
    ph = photo_for(p)
    figure = ""
    if ph:
        cap = f"<figcaption>{esc(ph[1])}{'. ' + ph[2] if ph[2] else ''}</figcaption>"
        figure = f'<figure class="post-figure"><div class="ph">{img_tag(ph, "(max-width:1200px) 100vw, 1200px", eager=True, widths=(640, 960, 1400, 2000))}</div>{cap}</figure>'
    verb = "Updated" if p["updated"] != p["date"] else "Published"
    body = f"""<header class="post-head"><div class="wrap"><div class="inner">
<a class="kicker" href="/topics/{slug}/">{p['pillar']}</a>
<h1>{esc(p['title'])}</h1>
<p class="dek">{esc(p['description'])}</p>
<div class="byline"><span class="avatar">{AUTHOR_INITIALS}</span><span>By <strong>{AUTHOR}</strong> · {verb} <time datetime="{p['updated']}">{fmt_date(p['updated'])}</time> · {p['read']} read</span></div>
</div></div></header>
{figure}
<div class="wrap"><div class="post-layout">
<article class="post-main">
<div class="answer"><b>In short</b><p>{esc(p['answer'])}</p></div>
<details class="toc-mobile toc"><summary>In this guide</summary>{toc_list(p)}</details>
<div class="prose">{insert_in_article_ads(p['html'])}</div>
<section class="faq"><h2 id="faq">Questions readers ask</h2>{faq_html}</section>
{cta_box()}
<div class="share">Share this guide:
<a href="https://wa.me/?text={share_text}" rel="noopener">WhatsApp</a>
<a href="https://www.facebook.com/sharer/sharer.php?u={esc(p['url'])}" rel="noopener">Facebook</a>
<button type="button" data-copy>Copy link</button></div>
<div class="author-box"><span class="avatar">{AUTHOR_INITIALS}</span><div><strong>{AUTHOR}</strong>{AUTHOR_ROLE}. Writes the journal with the service technicians who look after pools across Cape Town every week. <a href="/about/">About the journal</a></div></div>
{ad("after_article")}
</article>
<aside class="sidebar" aria-label="Sidebar">
<div class="side-box toc"><h4>In this guide</h4>{toc_list(p)}</div>
{ad("sidebar")}
<div class="side-cta"><strong>Pool giving you trouble?</strong><p>Send us a photo on WhatsApp and we'll tell you what's wrong.</p><a class="btn" href="{WHATSAPP}">WhatsApp us</a></div>
</aside>
</div></div>
<section class="related"><div class="wrap"><div class="section-head"><h2>Keep reading</h2><p>More from the journal</p></div><div class="grid">{''.join(card(r) for r in related)}</div></div></section>"""
    ld = [
        {"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"], "description": p["description"],
         "image": cover_url(p),
         "datePublished": p["date"], "dateModified": p["updated"], "mainEntityOfPage": p["url"], "inLanguage": "en-ZA",
         "articleSection": p["pillar"], "abstract": p["answer"], "wordCount": p["words"],
         "author": {"@type": "Person", "name": AUTHOR, "jobTitle": AUTHOR_ROLE, "url": SITE_URL + "/about/", "worksFor": {"@id": BIZ_URL + "/#business"}},
         "publisher": {"@type": "Organization", "name": BIZ_NAME, "url": BIZ_URL, "logo": {"@type": "ImageObject", "url": SITE_URL + "/brand/mark-512.png"}},
         "about": {"@type": "Thing", "name": "Swimming pools in Cape Town"}},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in p["faqs"]]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": p["pillar"], "item": f"{SITE_URL}/topics/{slug}/"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": p["url"]}]},
        org_ld(),
    ]
    return page(f"{p['title']} | {SITE_NAME}", p["description"], f"/{p['slug']}/", body, ld, "article", active=p["pillar"],
                progress=True, og_image=cover_url(p))


def guide_count(posts, name):
    n = sum(1 for p in posts if p["pillar"] == name)
    return "Guides coming soon" if n == 0 else f"{n} guide{'s' if n != 1 else ''}"


def pillar_photo(name, posts):
    slug = PILLAR_PHOTO.get(name)
    rec = PHOTOS["posts"].get(slug)
    return unsplash(rec) if rec else site_photo("capetown")


def build_index(posts):
    feat = posts[0]
    hero_ph = photo_for(feat) or site_photo("home")
    lead, rest = (posts[1], posts[2:]) if len(posts) > 1 else (posts[0], [])
    tiles = "".join(
        f'<a class="tile" href="/topics/{s}/">{img_tag(pillar_photo(n, posts), "(max-width:640px) 100vw, 240px", widths=(400, 600, 800, 1000))}'
        f'<div class="t"><strong>{n}</strong><span>{esc(b)}</span><em>{guide_count(posts, n)}</em></div></a>'
        for n, (s, c, b) in PILLARS.items())
    chips = "".join(f'<a class="chip" href="/topics/{s}/">{n}</a>' for n, (s, _, _) in PILLARS.items())
    se = SEASONS.get(TODAY.month)
    season = ""
    live_slugs = {p["slug"] for p in posts}
    if se and se[3] in live_slugs:
        sp = site_photo("blouberg")
        season = f"""<section class="season"><div class="bg">{img_tag(sp, "100vw", widths=(800, 1200, 1800, 2400))}</div><div class="wrap">
<span class="kicker">{se[0]}</span><h2>{se[1]}</h2><p>{se[2]}</p><a class="btn light" href="/{se[3]}/">Read the guide</a></div>
<div class="credit">{sp[2]}</div></section>"""
    body = f"""<section class="hero"><div class="bg">{img_tag(hero_ph, "100vw", eager=True, widths=(800, 1200, 1800, 2400))}</div><div class="wrap">
<span class="kicker">Featured · {feat['pillar']}</span>
<h1>{esc(feat['title'])}</h1>
<p class="dek">{esc(feat['description'])}</p>
<div class="actions"><a class="btn light" href="/{feat['slug']}/">Read the guide</a><a class="btn ghost" href="{WHATSAPP}">Ask us on WhatsApp</a></div>
</div><div class="credit">{hero_ph[2]}</div></section>
<div class="searchband"><div class="wrap">
<form class="search" role="search" action="/" onsubmit="return false"><label for="q" class="skip">Search guides</label><input id="q" type="search" placeholder="Search {len(posts)} guides: green pool, pH, pump…" autocomplete="off"><button class="btn" type="submit">Search</button></form>
<div class="chips">{chips}</div></div></div>
<section class="section" id="latest"><div class="wrap">
<div class="section-head"><h2>The latest</h2><p>Straight answers from Cape Town's pool technicians</p></div>
{lead_story(lead) if rest or lead is not feat else ''}
<div class="grid">{''.join(card(p) for p in rest)}</div>
<p class="empty">No guides match that yet. <a href="/contact/">Ask us the question</a> and we'll write it.</p>
</div></section>
{season}
<div class="wrap" style="padding-top:40px">{ad("home_feed")}</div>
<section class="section" id="topics"><div class="wrap">
<div class="section-head"><h2>Browse by topic</h2><p>Five areas, one goal: a pool you enjoy</p></div>
<div class="tiles">{tiles}</div></div></section>
<section class="section" style="padding-top:0"><div class="wrap"><div class="ask">
<div><span class="kicker">Reader questions</span><h2>Got a pool question?</h2><p>Send it in. We answer every one, and the best questions become guides on the journal.</p></div>
{question_form("home")}
</div></div></section>"""
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/", "description": TAGLINE,
           "inLanguage": "en-ZA", "publisher": {"@id": BIZ_URL + "/#business"}},
          {"@context": "https://schema.org", "@type": "Blog", "name": SITE_NAME, "url": SITE_URL + "/",
           "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": p["url"], "datePublished": p["date"]} for p in posts]},
          org_ld()]
    return page(f"{SITE_NAME}: Pool care, building and fun in Cape Town", TAGLINE + ".", "/", body, ld, og_image=cover_url(feat))


def question_form(src):
    return f"""<form class="stack" name="questions" method="POST" action="/thanks/" data-netlify="true" netlify-honeypot="bot-field">
<input type="hidden" name="form-name" value="questions"><input type="hidden" name="source" value="{src}">
<p class="hp"><label>Leave empty <input name="bot-field"></label></p>
<label>Your question<textarea name="question" required placeholder="e.g. Why does my pool go cloudy every time it rains?"></textarea></label>
<label>Suburb (optional)<input name="suburb" placeholder="e.g. Durbanville"></label>
<label>Email or WhatsApp number, if you'd like a direct reply (optional)<input name="contact"></label>
<button class="btn" type="submit">Send question</button></form>"""


def build_topic(name, posts):
    slug, col, blurb = PILLARS[name]
    items = [p for p in posts if p["pillar"] == name]
    grid = "".join(card(p) for p in items) or '<p class="empty" style="display:block">New guides on this topic are on the way.</p>'
    ph = pillar_photo(name, posts)
    body = f"""<section class="topic-hero"><div class="bg">{img_tag(ph, "100vw", eager=True, widths=(800, 1200, 1800, 2400))}</div><div class="wrap">
<div class="crumbs"><a href="/">Home</a> › Topics</div><h1>{name}</h1><p>{esc(blurb)}</p></div></section>
<section class="section"><div class="wrap"><div class="section-head"><h2>{guide_count(posts, name)}</h2><p>Newest first</p></div><div class="grid">{grid}</div>{ad("topic_feed")}</div></section>"""
    ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{name} guides", "url": f"{SITE_URL}/topics/{slug}/",
           "description": blurb, "hasPart": [{"@type": "BlogPosting", "headline": p["title"], "url": p["url"]} for p in items]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
              {"@type": "ListItem", "position": 2, "name": name, "item": f"{SITE_URL}/topics/{slug}/"}]}]
    return page(f"{name}: Cape Town pool guides | {SITE_NAME}", blurb, f"/topics/{slug}/", body, ld, active=name)


def static_page(path, title, desc, inner, ld_type="WebPage", updated=None, photo=None):
    up = f'<p class="updated">Last updated {fmt_date(updated)}</p>' if updated else ""
    fig = ""
    if photo:
        ph = site_photo(photo)
        fig = f'<figure><div class="page-figure">{img_tag(ph, "720px", eager=True)}</div><figcaption class="caption">{ph[2]}</figcaption></figure>'
    body = f'<div class="wrap"><div class="page"><div class="crumbs"><a href="/">Home</a></div><h1>{title}</h1>{up}{fig}<div class="prose">{inner}</div></div></div>'
    ld = [{"@context": "https://schema.org", "@type": ld_type, "name": title, "url": SITE_URL + path}]
    return page(f"{title} | {SITE_NAME}", desc, path, body, ld, active="About" if path == "/about/" else "")


def about_html():
    return f"""<p>{SITE_NAME} is written by the team at <a href="{BIZ_URL}">{BIZ_NAME}</a>. We service residential pools across Cape Town every week, so we see first-hand what the south-easter, winter fronts, soft municipal water and load-shedding do to a pool.</p>
<p>Every guide answers one real question that clients ask us. We keep the advice practical and local, and we update posts when the seasons or the rules change.</p>
<h2>Who writes it</h2><p><strong>{AUTHOR}</strong>, {AUTHOR_ROLE}, with input from our service technicians.</p>
<h2>How we keep it accurate</h2><ul><li>Chemical ranges follow widely used pool-industry guidelines. Always follow the label on any product you use.</li>
<li>Electrical, gas and structural work should be done by qualified, registered professionals.</li>
<li>Posts show the date they were last updated. Spot an error? <a href="/contact/">Tell us</a> and we'll fix it.</li></ul>
<h2>Advertising</h2><p>The journal may show ads to cover its running costs. Ads are labelled "Advertisement" and never change what we recommend. We link to {BIZ_NAME} because it's our own business, and we say so.</p>
{cta_box()}"""


def contact_html():
    email = f'<li>Email: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></li>' if CONTACT_EMAIL else ""
    return f"""<p>Have a pool question, a correction or a topic you'd like us to cover? Use the form below. For a quote or a service booking, WhatsApp is fastest.</p>
<ul><li>WhatsApp: <a href="{WHATSAPP}">{PHONE_DISPLAY}</a></li>{email}<li>Hours: {HOURS}</li><li>Service bookings: <a href="{BIZ_URL}">{BIZ_NAME}</a></li></ul>
<h2>Ask a question</h2>{question_form("contact")}"""


def privacy_html():
    who = f"{BIZ_NAME}" + (f" (<a href='mailto:{CONTACT_EMAIL}'>{CONTACT_EMAIL}</a>)" if CONTACT_EMAIL else f" (WhatsApp {PHONE_DISPLAY})")
    return f"""<p>This policy explains what information {SITE_NAME} ("we") collects, why, and your choices. We follow South Africa's Protection of Personal Information Act (POPIA).</p>
<h2>Who is responsible</h2><p>The journal is run by {who}. Our Information Officer is {AUTHOR}.</p>
<h2>What we collect</h2><ul>
<li><strong>Questions you send us:</strong> your question, and your suburb, email or phone number if you choose to give them. We use these only to reply and to decide which guides to write.</li>
<li><strong>Usage data:</strong> pages viewed, device type and approximate location, collected through cookies by analytics and advertising services.</li></ul>
<h2>Cookies and advertising</h2>
<p>We may use Google AdSense to show ads. Third-party vendors, including Google, use cookies to serve ads based on your previous visits to this and other websites. Google's use of advertising cookies lets it and its partners serve ads based on your visits to this site and others on the internet.</p>
<p>You can opt out of personalised advertising in <a href="https://adssettings.google.com" rel="noopener">Google Ads Settings</a>, or visit <a href="https://www.aboutads.info" rel="noopener">aboutads.info</a> to opt out of some third-party vendors' cookies. Read <a href="https://policies.google.com/technologies/partner-sites" rel="noopener">how Google uses information from sites that use its services</a>.</p>
<p>We may use tawk.to for live chat. If you start a chat, tawk.to processes the messages and details you type so we can reply.</p>
<p>We may use Google Analytics to understand which guides are useful. You can block cookies in your browser settings. The site still works without them.</p>
<h2>Sharing</h2><p>We don't sell your personal information. We share it only with the service providers that run this site (hosting, forms, live chat, analytics and ads), or when the law requires it.</p>
<h2>How long we keep it</h2><p>We keep questions and contact details for up to 24 months, then delete them.</p>
<h2>Your rights</h2><p>You may ask to see, correct or delete the personal information we hold about you, or object to us using it. Contact us using the details on our <a href="/contact/">contact page</a>. You can also complain to the <a href="https://inforegulator.org.za" rel="noopener">Information Regulator</a>.</p>
<h2>Changes</h2><p>We'll update this page if anything changes and show the new date at the top.</p>"""


def terms_html():
    return f"""<h2>General advice only</h2><p>Guides on {SITE_NAME} are general information for typical residential pools in Cape Town. Every pool is different. You use the advice at your own risk, and we're not liable for loss or damage arising from it.</p>
<h2>Chemicals and safety</h2><p>Pool chemicals can be dangerous. Always read and follow the product label, never mix chemicals, and store them away from children. Electrical, gas and structural work must be done by qualified, registered professionals.</p>
<h2>Children and water safety</h2><p>No guide replaces active adult supervision. Always have a responsible adult watching children in and around water.</p>
<h2>Advertising and our own business</h2><p>This site may show third-party ads, which are labelled. We don't endorse advertised products. We link to {BIZ_NAME}, which owns and writes this journal.</p>
<h2>Copyright</h2><p>All content © {BIZ_NAME}. You may quote short extracts with a link back to the original guide.</p>
<h2>Links</h2><p>We aren't responsible for the content of external websites we link to.</p>"""


# ----------------------------------------------------------------- CMS
def build_admin():
    pillar_opts = list(PILLARS.keys())
    config = {
        "backend": {"name": "github", "repo": GITHUB_REPO, "branch": GITHUB_BRANCH,
                    "commit_messages": {"create": "New post: {{slug}}", "update": "Edit post: {{slug}}", "delete": "Delete post: {{slug}}",
                                        "uploadMedia": "Upload image {{path}}", "deleteMedia": "Delete image {{path}}"}},
        "site_url": SITE_URL, "display_url": SITE_URL, "logo_url": "/brand/logo-horizontal.svg",
        "locale": "en", "media_folder": "assets/img", "public_folder": "/img",
        "collections": [{
            "name": "posts", "label": "Posts", "label_singular": "Post", "folder": "content", "create": True,
            "slug": "{{slug}}", "extension": "md", "format": "yaml-frontmatter",
            "sortable_fields": ["date", "title", "pillar"], "view_filters": [{"label": p, "field": "pillar", "pattern": p} for p in pillar_opts],
            "summary": "{{date | date('YYYY-MM-DD')}} · {{pillar}} · {{title}}",
            "fields": [
                {"label": "Title (phrase it as the question people ask)", "name": "title", "widget": "string"},
                {"label": "Publish date (post goes live automatically on this day)", "name": "date", "widget": "datetime",
                 "format": "YYYY-MM-DD", "date_format": "YYYY-MM-DD", "time_format": False},
                {"label": "Topic", "name": "pillar", "widget": "select", "options": pillar_opts},
                {"label": "Short description (shown on Google, 140–160 characters)", "name": "description", "widget": "text"},
                {"label": "Quick answer (2–3 sentences that fully answer the title)", "name": "answer", "widget": "text"},
                {"label": "Cover photo (landscape, real job photos work best)", "name": "image", "widget": "image", "required": False},
                {"label": "Cover photo description (e.g. 'Green pool in Bellville before treatment')", "name": "image_alt", "widget": "string", "required": False},
                {"label": "Article", "name": "body", "widget": "markdown"},
                {"label": "FAQs", "name": "faqs", "widget": "list", "required": False,
                 "fields": [{"label": "Question", "name": "q", "widget": "string"}, {"label": "Answer", "name": "a", "widget": "text"}]},
                {"label": "Last updated (set when you refresh an old post)", "name": "updated", "widget": "datetime",
                 "format": "YYYY-MM-DD", "date_format": "YYYY-MM-DD", "time_format": False, "required": False},
                {"label": "Draft (tick to hide this post completely)", "name": "draft", "widget": "boolean", "default": False, "required": False},
            ]}],
    }
    os.makedirs(os.path.join(OUT, "admin"), exist_ok=True)
    open(os.path.join(OUT, "admin", "config.yml"), "w", encoding="utf-8").write(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
    open(os.path.join(OUT, "admin", "index.html"), "w", encoding="utf-8").write(f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Editor | {SITE_NAME}</title>
<link rel="icon" href="/favicon.ico"></head>
<body><script src="https://unpkg.com/decap-cms@^3.0.0/dist/decap-cms.js"></script>
<script>CMS.registerPreviewStyle('/style.css');</script></body></html>""")


# ----------------------------------------------------------------- BUILD
ASSET_VER = "1"


def main():
    global ASSET_VER
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    posts = load_posts()
    css, js = (open(os.path.join(ASSETS, f), encoding="utf-8").read() for f in ("style.css", "site.js"))
    ASSET_VER = hashlib.md5((css + js).encode()).hexdigest()[:8]

    def w(path, s):
        full = os.path.join(OUT, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8").write(s)

    w("style.css", css)
    w("site.js", js)
    shutil.copytree(BRAND, os.path.join(OUT, "brand"))
    shutil.copy(os.path.join(BRAND, "favicon.ico"), os.path.join(OUT, "favicon.ico"))
    shutil.copytree(os.path.join(ASSETS, "fonts"), os.path.join(OUT, "fonts"))
    build_admin()
    if os.path.isdir(os.path.join(ASSETS, "img")):
        shutil.copytree(os.path.join(ASSETS, "img"), os.path.join(OUT, "img"))
    for p in posts:
        w(f"covers/{p['slug']}.svg", cover_svg(p["pillar"], p["slug"]))
        w(f"{p['slug']}/index.html", build_post(p, posts))
    w("index.html", build_index(posts))
    for name in PILLARS:
        w(f"topics/{PILLARS[name][0]}/index.html", build_topic(name, posts))
    latest = posts[0]["updated"]
    w("about/index.html", static_page("/about/", f"About {SITE_NAME}", f"Who writes {SITE_NAME} and how we keep our pool advice accurate.", about_html(), "AboutPage", photo="capetown"))
    w("contact/index.html", static_page("/contact/", "Contact &amp; questions", "Ask a pool question or get in touch with the Cape Pool Journal team.", contact_html(), "ContactPage"))
    w("privacy/index.html", static_page("/privacy/", "Privacy policy", f"How {SITE_NAME} collects and uses information, including cookies and advertising.", privacy_html(), updated="2026-10-03"))
    w("terms/index.html", static_page("/terms/", "Terms &amp; disclaimer", f"Terms of use and disclaimer for {SITE_NAME}.", terms_html(), updated="2026-10-03"))
    w("thanks/index.html", static_page("/thanks/", "Thanks, we've got your question", "Question received.", f"<p>We read every question. If you left contact details, we'll reply within one working day. Need help sooner? <a href='{WHATSAPP}'>WhatsApp {PHONE_DISPLAY}</a>.</p><p><a href='/'>Back to the journal</a></p>"))
    w("404.html", page(f"Page not found | {SITE_NAME}", "Page not found.", "/404.html",
                       '<div class="wrap"><div class="page"><h1>That page has gone for a swim.</h1><p><a href="/">Back to the journal</a> or <a href="/contact/">ask us your question</a>.</p></div></div>'))

    urls = [("/", latest)] + [(f"/topics/{s}/", latest) for s, _, _ in PILLARS.values()] + \
           [(f"/{p['slug']}/", p["updated"]) for p in posts] + [(u, "2026-10-03") for u in ("/about/", "/contact/", "/privacy/", "/terms/")]
    w("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
      "".join(f"<url><loc>{SITE_URL}{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n")
    w("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /thanks/\nDisallow: /admin/\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    w("llms.txt", f"# {SITE_NAME}\n\n> {TAGLINE}. Written by {BIZ_NAME} ({BIZ_URL}), a pool service company in Cape Town, South Africa. Contact: WhatsApp {PHONE_DISPLAY}.\n\n## Guides\n\n" +
      "".join(f"- [{p['title']}]({p['url']}): {p['answer']}\n" for p in posts) +
      f"\n## Service\n\n- [{BIZ_NAME}]({BIZ_URL}): weekly pool servicing, green-pool rescues and clean-ups across Cape Town. Hours: {HOURS}.\n")
    items = "".join(f"<item><title>{esc(p['title'])}</title><link>{p['url']}</link><guid>{p['url']}</guid>"
                    f"<pubDate>{date.fromisoformat(p['date']).strftime('%a, %d %b %Y')} 08:00:00 +0200</pubDate><description>{esc(p['answer'])}</description></item>" for p in posts)
    w("feed.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{SITE_NAME}</title><link>{SITE_URL}/</link>'
                  f'<description>{esc(TAGLINE)}</description><language>en-za</language>{items}</channel></rss>')
    if ADS_LIVE:
        pub = ADSENSE_CLIENT.replace("ca-", "")
        w("ads.txt", f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    w("_headers", "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
                  "/style.css\n  Cache-Control: public, max-age=31536000, immutable\n/site.js\n  Cache-Control: public, max-age=31536000, immutable\n"
                  "/covers/*\n  Cache-Control: public, max-age=604800\n")
    mode = "ads LIVE" if ADS_LIVE else ("ad placeholders shown" if PREVIEW_ADS else "ads off until ADSENSE_CLIENT is set")
    print(f"Built {len(posts)} posts, {len(PILLARS)} topic pages ({mode}) into {OUT}")


if __name__ == "__main__":
    main()
