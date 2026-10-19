"""Ayhoo! profile card image API.

GET /api/card?name=..&avatar=..&level=..&xp=..&nextxp=..&coins=..&roles=A|B|C
Returns a 1000x420 PNG. Hosted on Vercel (Python runtime) or run locally.
"""
import io
import os
import re
import urllib.request
from flask import Flask, request, Response

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
W, H, S = 1000, 420, 2  # output size and supersampling factor
ALLOWED_AVATAR_HOSTS = ("cdn.discordapp.com", "media.discordapp.net")
ORANGE = (255, 122, 0)


def font(name, size):
    return ImageFont.truetype(os.path.join(ROOT, "fonts", name), size * S)


def clean(text, limit):
    """Drop emoji and odd symbols the font cannot draw, then trim."""
    text = re.sub(r"[^\w\s\-'.!&()+]", "", text or "", flags=re.UNICODE).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:limit].rstrip()


def to_int(value, default=0, lo=0, hi=10 ** 12):
    try:
        return max(lo, min(hi, int(float(value))))
    except (TypeError, ValueError):
        return default


def fetch_avatar(url):
    try:
        host = urlparse(url).hostname or ""
        if urlparse(url).scheme != "https" or host not in ALLOWED_AVATAR_HOSTS:
            return None
        req = urllib.request.Request(url, headers={"User-Agent": "AyhooProfileCard/1.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            return Image.open(io.BytesIO(r.read(4_000_000))).convert("RGB")
    except Exception:
        return None


def gradient(size):
    w, h = size
    top, mid, end = (244, 106, 0), (150, 58, 6), (16, 11, 8)
    base = Image.new("RGB", size)
    px = base.load()
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.55 + y / h * 0.45)
            if t < 0.5:
                k = t / 0.5
                c = tuple(int(top[i] + (mid[i] - top[i]) * k) for i in range(3))
            else:
                k = (t - 0.5) / 0.5
                c = tuple(int(mid[i] + (end[i] - mid[i]) * k) for i in range(3))
            px[x, y] = c
    return base


def glow(img, center, radius, color, alpha):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.45))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return m


def text_w(draw, txt, f):
    return draw.textlength(txt, font=f)


def render(name="Member", avatar=None, level=1, xp=0, nextxp=100, coins=0, roles=None):
    name = clean(name, 22) or "Member"
    roles = [clean(r, 20) for r in (roles or [])]
    roles = [r for r in roles if r]
    level, xp, nextxp, coins = to_int(level, 1, 1), to_int(xp), max(to_int(nextxp, 100, 1), 1), to_int(coins)

    img = gradient((W * S, H * S))
    img = glow(img, (130 * S, 40 * S), 220 * S, (255, 176, 102), 150)
    img = glow(img, (880 * S, 400 * S), 260 * S, (255, 120, 20), 70)

    # glass panel
    pad = 22 * S
    panel = (pad, pad, W * S - pad, H * S - pad)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle(panel, 30 * S, fill=(255, 255, 255, 30), outline=(255, 255, 255, 70), width=2 * S)

    # avatar
    asz = 210 * S
    ax, ay = 62 * S, 92 * S
    if avatar is not None:
        av = ImageOps.fit(avatar, (asz, asz), Image.LANCZOS)
    else:
        av = Image.new("RGB", (asz, asz), (60, 38, 24))
    m = Image.new("L", (asz, asz), 0)
    ImageDraw.Draw(m).ellipse((0, 0, asz - 1, asz - 1), fill=255)
    ring = 8 * S
    d.ellipse((ax - ring, ay - ring, ax + asz + ring, ay + asz + ring), fill=(255, 255, 255, 235))
    img.paste(av, (ax, ay), m)
    d = ImageDraw.Draw(img, "RGBA")

    # logo (top right)
    try:
        logo = Image.open(os.path.join(ROOT, "logo.png")).convert("RGBA")
        lw = 150 * S
        logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        img.paste(logo, (W * S - pad - 34 * S - lw, pad + 26 * S), logo)
        d = ImageDraw.Draw(img, "RGBA")
    except Exception:
        pass

    tx = 312 * S
    f_name, f_med, f_reg, f_small = font("Poppins-Bold.ttf", 46), font("Poppins-Medium.ttf", 22), font("Poppins-Regular.ttf", 18), font("Poppins-Medium.ttf", 16)

    # name
    d.text((tx, 48 * S), name, font=f_name, fill=(255, 255, 255, 255))

    # level pill
    lv = "LEVEL %d" % level
    f_pill = font("Poppins-Bold.ttf", 17)
    lw_ = text_w(d, lv, f_pill)
    px0, py0 = tx, 118 * S
    d.rounded_rectangle((px0, py0, px0 + lw_ + 34 * S, py0 + 38 * S), 19 * S, fill=(255, 255, 255, 255))
    d.text((px0 + 17 * S, py0 + 6 * S), lv, font=f_pill, fill=(160, 62, 0, 255))

    # coins
    cx0 = px0 + lw_ + 34 * S + 22 * S
    r = 15 * S
    cy = py0 + 19 * S
    d.ellipse((cx0, cy - r, cx0 + 2 * r, cy + r), fill=(255, 210, 120, 255), outline=(255, 255, 255, 255), width=2 * S)
    d.ellipse((cx0 + 6 * S, cy - r + 6 * S, cx0 + 2 * r - 6 * S, cy + r - 6 * S), outline=(214, 120, 0, 255), width=2 * S)
    d.text((cx0 + 2 * r + 10 * S, py0 + 4 * S), "{:,}".format(coins), font=f_med, fill=(255, 255, 255, 255))

    # xp bar
    by = 184 * S
    bw = (W - 62 - 60) * S - tx + 62 * S
    bw = (W * S - pad - 40 * S) - tx
    d.text((tx, by - 4 * S), "XP", font=f_small, fill=(255, 255, 255, 190))
    label = "{:,} / {:,}".format(xp, nextxp)
    d.text((tx + bw - text_w(d, label, f_small), by - 4 * S), label, font=f_small, fill=(255, 255, 255, 210))
    ty = by + 30 * S
    d.rounded_rectangle((tx, ty, tx + bw, ty + 16 * S), 8 * S, fill=(0, 0, 0, 90))
    frac = max(0.0, min(1.0, xp / nextxp))
    if frac > 0:
        fw = max(int(bw * frac), 16 * S)
        d.rounded_rectangle((tx, ty, tx + fw, ty + 16 * S), 8 * S, fill=(255, 255, 255, 255))

    # roles
    ry = 272 * S
    d.text((tx, ry - 4 * S), "ROLES", font=f_small, fill=(255, 255, 255, 190))
    x, y = tx, ry + 30 * S
    right = W * S - pad - 40 * S
    f_chip = font("Poppins-Medium.ttf", 16)
    shown = 0
    for i, rname in enumerate(roles[:12]):
        cw = text_w(d, rname, f_chip) + 28 * S
        if x + cw > right:
            if y > ry + 30 * S:  # second row already used
                break
            x, y = tx, y + 40 * S
        d.rounded_rectangle((x, y, x + cw, y + 32 * S), 16 * S, fill=(255, 255, 255, 46), outline=(255, 255, 255, 120), width=1 * S)
        d.text((x + 14 * S, y + 4 * S), rname, font=f_chip, fill=(255, 255, 255, 255))
        x += cw + 8 * S
        shown += 1
    if not roles:
        d.text((tx, ry + 30 * S), "No roles yet", font=f_reg, fill=(255, 255, 255, 170))
    elif len(roles) > shown:
        more = "+%d" % (len(roles) - shown)
        cw = text_w(d, more, f_chip) + 28 * S
        if x + cw <= right:
            d.rounded_rectangle((x, y, x + cw, y + 32 * S), 16 * S, fill=(255, 255, 255, 255))
            d.text((x + 14 * S, y + 4 * S), more, font=f_chip, fill=(160, 62, 0, 255))

    out = img.resize((W, H), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def split_roles(raw):
    raw = (raw or "").replace("|", ",")
    return [p.strip() for p in raw.split(",") if p.strip()]



app = Flask(__name__)

@app.get("/")
def home():
    return {"service": "Ayhoo! Profile Card API", "status": "online", "endpoint": "/api/card"}

@app.get("/api/card")
def profile_card():
    q = request.args
    avatar = fetch_avatar(q.get("avatar")) if q.get("avatar") else None
    try:
        png = render(
            name=q.get("name", "Member"),
            avatar=avatar,
            level=q.get("level", 1),
            xp=q.get("xp", 0),
            nextxp=q.get("nextxp", 100),
            coins=q.get("coins", 0),
            roles=split_roles(q.get("roles")),
        )
        return Response(png, mimetype="image/png", headers={"Cache-Control": "public, max-age=60"})
    except Exception:
        return Response("render error", status=500, mimetype="text/plain")
