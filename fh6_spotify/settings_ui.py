"""Settings-window visual helpers.

Split out of settings.py (which was pushing 14k lines) for file size:
icon/pixmap drawing, the Qt stylesheet builder (_build_qss), a handful of
small reusable widgets (_FadeMenu, _FadeScroll, _FadeLabel, _VerButton,
_BigMenuIconStyle, _DeviceButton, _SkipModeButton), and misc formatting
helpers (bind-code labels, What's-new HTML localization, version parsing).

settings.py does `from fh6_spotify.settings_ui import *` and re-exports
everything from its own namespace, so external callers (fh6_spotify.app)
keep importing names like `_APP_ICON` or `bundled_whatsnew_version` FROM
fh6_spotify.settings unchanged.

_SCALE is the one name that must NOT be copied by value: it's a live
module global _s() reads on every call, and both settings.py and app.py
rebuild it in place (module.attr = ...) when the UI scale changes. Any
new write site must target fh6_spotify.settings_ui._SCALE directly (see
SettingsWindow.__init__ and app.py's rebuild_window) - a bare
`from fh6_spotify.settings_ui import _SCALE` would silently decouple the
copy from the one _s() actually reads.
"""

import os
import sys
import math
import ctypes
from PySide6.QtCore import (
    Qt,
    QSize,
    QRectF,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QFont,
    QIcon,
    QPixmap,
    QPainterPath,
    QPen,
    QFontMetrics,
    QLinearGradient,
)
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QAbstractButton,
    QPushButton,
    QMenu,
    QScrollArea,
    QProxyStyle,
    QStyle,
)
from fh6_spotify.theme import (
    c as _c,
    active_theme as _active_theme,
    ACCENT as _ACCENT,
)


__all__ = [
    '_clear_layout',
    '_TITLEBAR_H',
    '_SCALE',
    '_SCALE_STEPS',
    '_scale_label',
    '_s',
    '_RECT',
    '_NCCALCSIZE_PARAMS',
    '_POINT',
    '_WINDOWPLACEMENT',
    '_LOOP_DT',
    '_ramp_from_ms',
    '_ms_from_ramp',
    '_ui_font',
    '_link_pixmap',
    '_app_icon',
    '_exe_icon',
    '_custom_glyph_pixmap',
    '_dots_tile_pixmap',
    '_alpha_bbox_center',
    '_style_icon_center',
    '_DEV_ART',
    '_dev_asset',
    '_dev_name',
    '_dev_wm_scale',
    '_invert_rgb',
    '_recolor_pm',
    '_forza_pixmap',
    '_dev_pixmap',
    '_dev_qicon',
    '_dev_icon',
    '_action_icon',
    '_kind_icon',
    '_tab_icon',
    '_tag_colors',
    '_DeviceButton',
    '_SkipModeButton',
    '_FadeMenu',
    '_media_icon',
    '_menu_icon',
    '_caption_icon',
    '_info_icon',
    '_zoom_icon',
    '_dim_pixmap',
    '_dev_wm_rot',
    '_paint_pill_backdrop',
    '_launcher_icon',
    '_bulb_pixmap',
    '_trash_pixmap',
    '_save_pixmap',
    '_globe_pixmap',
    '_refresh_pixmap',
    '_undo_pixmap',
    '_move_pixmap',
    '_mic_pixmap',
    '_smooth_scroll',
    '_FadeScroll',
    '_FadeLabel',
    '_VerButton',
    '_check_pixmap',
    '_question_pixmap',
    '_play_pixmap',
    '_x_pixmap',
    '_sparkle_pixmap',
    '_update_pixmap',
    '_BigMenuIconStyle',
    '_rounded_bordered',
    '_CHEV_CACHE',
    '_chevron_pixmap',
    '_chevron_qss_path',
    '_DOWNCHEV_CACHE',
    '_down_chevron_qss_path',
    '_CHECK_CACHE',
    '_check_qss_path',
    '_badge_html',
    '_folder_pixmap',
    '_ASSETS',
    '_FORZA',
    '_SPOTIFY',
    '_LINK',
    '_LINK_BROKEN',
    '_APP_ICON',
    '_SUPPORT_URL',
    '_DISCORD_URL',
    '_load_scaled',
    '_load_icon',
    '_apply_dwm_titlebar',
    '_round_menu',
    '_tinted',
    '_media_pixmap',
    '_SENS_HI_THRESH',
    '_SENS_LO_THRESH',
    '_sens_to_thresh',
    '_thresh_to_sens',
    '_XBOX_BTN',
    '_XBOX_FACE',
    '_PS_LABELS',
    '_pretty_code',
    '_is_dev',
    '_PS_FACE',
    '_ps_face_pixmap',
    '_xbox_face_pixmap',
    '_fetch_pixmap',
    'bundled_whatsnew_version',
    '_theme_note_html',
    '_localize_inline_images',
    '_contrast_text',
    '_combo_pixmap',
    '_set_bind_visual',
    '_vk_label',
    '_build_qss',
]


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


_TITLEBAR_H = 34
_SCALE = 1.0
_SCALE_STEPS = [1.25, 1.5, 1.75]


def _scale_label(step: float) -> str:
    return f"{int(round((step - 0.25) * 100))}%"


def _s(n: int) -> int:
    return max(1, int(round(n * _SCALE)))


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", _RECT * 3), ("lppos", ctypes.c_void_p)]


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("showCmd", ctypes.c_uint),
        ("ptMinPosition", _POINT),
        ("ptMaxPosition", _POINT),
        ("rcNormalPosition", _RECT),
    ]


_LOOP_DT = 0.02


def _ramp_from_ms(ms: int) -> float:
    secs = max(50, ms) / 1000.0
    return 1.0 - 0.05 ** (_LOOP_DT / secs)


def _ms_from_ramp(ramp: float) -> int:
    ramp = min(max(ramp, 0.0001), 0.999)
    n = math.log(0.05) / math.log(1.0 - ramp)
    return int(round(n * _LOOP_DT * 1000))


def _ui_font(px: int, weight=QFont.Medium) -> QFont:
    """Segoe UI Variable (the native Win11 UI font, hand-hinted for small sizes)
    forced to GRAYSCALE antialiasing + full hinting.

    Two Qt defaults make text look 'choppy/dirty' vs native apps:
      * ClearType *subpixel* AA paints colored (orange/blue) fringes on stems;
        NoSubpixelAntialias switches to clean grayscale AA like Win11 apps.
      * weak hinting lets stems land between pixels (uneven weight); full hinting
        grid-fits them. Segoe is built for this, Inter is not.
    The strategy/hint must live on a QFont set programmatically: a QSS
    `font-family` rule rebuilds the font and silently drops both."""
    f = QFont("Segoe UI")
    f.setPixelSize(_s(px))
    f.setWeight(weight)
    f.setStyleStrategy(QFont.PreferAntialias | QFont.NoSubpixelAntialias)
    f.setHintingPreference(QFont.PreferFullHinting)
    return f


def _link_pixmap(connected: bool) -> QPixmap:
    """Horizontal chain-link glyph (AA vector, thick solid rings). Connected ->
    bright + interlocked; disconnected -> dim + rings pulled apart (broken)."""
    s = 64
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(_c("icon") if connected else _c("icon_dim")))
    p.translate(s / 2, s / 2)
    off = 11.0 if connected else 19.0

    def ring(cx: float) -> QPainterPath:
        pth = QPainterPath()
        pth.setFillRule(Qt.OddEvenFill)
        pth.addRoundedRect(QRectF(cx - 16, -10, 32, 20), 10, 10)
        pth.addRoundedRect(QRectF(cx - 9, -4, 18, 8), 4, 4)
        return pth

    p.drawPath(ring(-off))
    p.drawPath(ring(off))
    p.end()
    return pix.scaled(_s(24), _s(24), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _app_icon(path: str, letter: str, size: int = 28) -> QPixmap:
    """Load an app logo (official asset the user drops in assets/). Falls back to
    a neutral rounded-square placeholder with a letter when the file is absent."""
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            return pm.scaled(
                _s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
    s = size * 2
    pm = QPixmap(s, s)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(_c("border")))
    p.drawRoundedRect(0, 0, s, s, s * 0.28, s * 0.28)
    p.setPen(QColor(_c("text")))
    p.setFont(_ui_font(int(size), QFont.Bold))
    p.drawText(pm.rect(), Qt.AlignCenter, letter)
    p.end()
    return pm.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _exe_icon(path: str, letter: str, size: int = 22) -> QIcon:
    """The real icon embedded in an exe (the app's own logo), or a letter-avatar
    fallback. Used by the custom-source picker so each app shows its real icon
    instead of a generic letter tile."""
    if path:
        try:
            from PySide6.QtWidgets import QFileIconProvider
            from PySide6.QtCore import QFileInfo

            ic = QFileIconProvider().icon(QFileInfo(path))
            if ic is not None and not ic.isNull():
                pm = ic.pixmap(_s(size), _s(size))
                if not pm.isNull():
                    return QIcon(pm)
        except Exception:
            pass
    return QIcon(_app_icon("", letter, size))


def _custom_glyph_pixmap(size: int = 22) -> QPixmap:
    """Icon for the 'Custom…' source entry before a real app is picked: the
    rounded tile (matching the letter avatars) with a '+' - you're adding your
    own source. Once a real app is picked it shows that app's own icon instead."""
    s = size * 2
    pm = QPixmap(s, s)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    _tp = QPen(QColor(_c("border_hi")))
    _tp.setWidthF(max(1.0, s * 0.045))
    p.setPen(_tp)
    p.setBrush(QColor(_c("surface")))
    _in = _tp.widthF() / 2
    p.drawRoundedRect(QRectF(_in, _in, s - 2 * _in, s - 2 * _in), s * 0.26, s * 0.26)
    pen = QPen(QColor(_c("icon")))
    pen.setWidthF(max(1.6, s * 0.1))
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    c = s / 2
    r = s * 0.22
    p.drawLine(int(c - r), int(c), int(c + r), int(c))
    p.drawLine(int(c), int(c - r), int(c), int(c + r))
    p.end()
    return pm.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _dots_tile_pixmap(size: int = 22) -> QPixmap:
    """'More' submenu icon: the same rounded tile as the Custom entry, with three
    dots, so the two custom/more rows match visually."""
    s = size * 2
    pm = QPixmap(s, s)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    _tp = QPen(QColor(_c("border_hi")))
    _tp.setWidthF(max(1.0, s * 0.045))
    p.setPen(_tp)
    p.setBrush(QColor(_c("surface")))
    _in = _tp.widthF() / 2
    p.drawRoundedRect(QRectF(_in, _in, s - 2 * _in, s - 2 * _in), s * 0.26, s * 0.26)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(_c("icon")))
    r = s * 0.075
    for dx in (-s * 0.2, 0.0, s * 0.2):
        p.drawEllipse(QRectF(s / 2 + dx - r, s / 2 - r, 2 * r, 2 * r))
    p.end()
    return pm.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _alpha_bbox_center(pm, ss):
    """Logical centre of a pixmap's opaque (alpha > 8) region, or None if fully
    transparent. Used to find where CE_PushButtonLabel actually drew the glyph in a
    buffer, so it can be offset onto the full-draw position."""
    from PySide6.QtGui import QImage
    from PySide6.QtCore import QPointF

    img = pm.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()
    if w <= 0 or h <= 0:
        return None
    mv = img.bits()
    stride = img.bytesPerLine()
    minx = miny = 1073741824
    maxx = maxy = -1
    for y in range(h):
        base = y * stride + 3
        for x in range(w):
            if mv[base + x * 4] > 8:
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
    if maxx < 0:
        return None
    return QPointF((minx + maxx + 1) / 2.0 / ss, (miny + maxy + 1) / 2.0 / ss)


def _style_icon_center(btn, opt, ss):
    """Logical centre of where the STYLE actually draws this button's icon, found by
    rendering the full control and the control-without-icon and taking the centre of
    the region that differs. CE_PushButtonLabel alone mis-places the icon on a
    QSS-grown active tab (it ignores the grow, drawing the glyph lower), which made
    the press dip scale around the wrong point and drag the glyph down. The full
    CE_PushButton draws the icon at its true spot; the diff reads exactly that, so
    the dip's glyph centre matches the resting glyph and it scales in place.
    Returns None if nothing differs (no icon)."""
    from PySide6.QtGui import QPixmap, QIcon, QImage
    from PySide6.QtWidgets import QStyle, QStylePainter
    from PySide6.QtCore import Qt, QPointF

    w = max(1, int(btn.width() * ss))
    h = max(1, int(btn.height() * ss))
    full = QPixmap(w, h)
    full.setDevicePixelRatio(ss)
    full.fill(Qt.transparent)
    bg = QPixmap(w, h)
    bg.setDevicePixelRatio(ss)
    bg.fill(Qt.transparent)
    sp = QStylePainter(full, btn)
    sp.drawControl(QStyle.ControlElement.CE_PushButton, opt)
    sp.end()
    saved = opt.icon
    opt.icon = QIcon()
    sp = QStylePainter(bg, btn)
    sp.drawControl(QStyle.ControlElement.CE_PushButton, opt)
    sp.end()
    opt.icon = saved
    ia = full.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    ib = bg.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    iw = min(ia.width(), ib.width())
    ih = min(ia.height(), ib.height())
    ma, mb = ia.bits(), ib.bits()
    sa, sb = ia.bytesPerLine(), ib.bytesPerLine()
    minx = miny = 1073741824
    maxx = maxy = -1
    for y in range(ih):
        ra, rb = y * sa, y * sb
        for x in range(iw):
            ja, jb = ra + x * 4, rb + x * 4
            if (
                abs(ma[ja] - mb[jb])
                + abs(ma[ja + 1] - mb[jb + 1])
                + abs(ma[ja + 2] - mb[jb + 2])
                + abs(ma[ja + 3] - mb[jb + 3])
                > 40
            ):
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
    if maxx < 0:
        return None
    return QPointF((minx + maxx + 1) / 2.0 / ss, (miny + maxy + 1) / 2.0 / ss)


_DEV_ART = {
    "playstation": ("dualsense.png", False),
    "dualsense": ("dualsense.png", False),
    "dualshock": ("dualsense.png", False),
    "xbox": ("xbox controller v4.png", True),
    "keyboard": ("keyboard icon v5.png", True),
    "wheel": ("steering-wheel v3.png", True),
}


def _dev_asset(dev: str) -> str:
    """Path to the device's icon art, or '' if none ships."""
    name = _DEV_ART.get(dev, ("", False))[0]
    if name:
        p = os.path.join(_ASSETS, name)
        if os.path.exists(p):
            return p
    return ""


def _dev_name(dev: str) -> str:
    """Friendly device label for the Controls pill + tooltips."""
    return {
        "playstation": "PlayStation",
        "dualsense": "PlayStation",
        "dualshock": "PlayStation",
        "xbox": "Xbox",
        "keyboard": "Keyboard",
        "wheel": "Sim wheel",
    }.get(dev, "Controller")


def _dev_wm_scale(dev: str) -> float:
    """Controls-pill watermark size multiple. The DualSense art fills its box; the
    line-art icons (xbox / keyboard / wheel) sit smaller, so they get a bump."""
    return 1.5 if dev in ("playstation", "dualsense", "dualshock") else 2.0


def _invert_rgb(pm):
    """Invert RGB (alpha untouched) - the v2 device art is black line-art, so we
    flip it to white to read on the dark UI."""
    if pm is None or pm.isNull():
        return pm
    from PySide6.QtGui import QImage

    img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
    img.invertPixels(QImage.InvertRgb)
    return QPixmap.fromImage(img)


def _recolor_pm(pm, color: str):
    """Flat-recolor a pixmap to `color`, keeping its alpha (SourceAtop fill).
    For monochrome line-art glyphs where only the silhouette matters."""
    if pm is None or pm.isNull():
        return pm
    out = QPixmap(pm.size())
    out.fill(QColor(0, 0, 0, 0))
    p = QPainter(out)
    p.drawPixmap(0, 0, pm)
    p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    p.fillRect(out.rect(), QColor(color))
    p.end()
    return out


def _forza_pixmap(size: int) -> QPixmap:
    """Themed Forza badge. Dark/HC keep the asset as-is (black FH on white disc).
    Light INVERTS it (white FH on black disc) AND lifts the now-pure-black disc to
    a softer #424240 - pure black read harsh. None if the asset is missing."""
    pm = _load_scaled(_FORZA, size)
    if pm is None or pm.isNull():
        return pm
    if _active_theme() != "light":
        return pm
    pm = _invert_rgb(pm)
    out = QPixmap(pm.size())
    out.fill(QColor(0, 0, 0, 0))
    p = QPainter(out)
    p.drawPixmap(0, 0, pm)
    p.setCompositionMode(QPainter.CompositionMode_Screen)
    p.fillRect(out.rect(), QColor("#424240"))
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out


def _dev_pixmap(dev: str, size: int):
    """Scaled device glyph, themed: WHITE on the dark UI, DARK on light. Art
    ships as black line-art (v2/v3) for most devices, already-light art for
    DualSense - so invert exactly when the art's tone differs from what the
    theme needs (XOR of "art is black" and "theme is light"). None when no art
    ships for `dev`."""
    pm = _load_scaled(_dev_asset(dev), size)
    if pm is None:
        return pm
    if _active_theme() == "light":
        pm = _recolor_pm(pm, "#3c3c38")
        return pm
    if _DEV_ART.get(dev, ("", False))[1]:
        pm = _invert_rgb(pm)
    return pm


def _dev_qicon(dev: str, size: int):
    """QIcon form of _dev_pixmap, or None."""
    pm = _dev_pixmap(dev, size)
    if pm is not None and not pm.isNull():
        return QIcon(pm)


def _dev_icon(dev: str, size: int = 34) -> QIcon:
    """Generic device glyph (gamepad / wheel / keyboard). Overridden by an
    official logo if assets/<dev>.png exists (loaded by the caller)."""
    s = 44
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(_c("icon")))
    pen.setWidthF(2.4)
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    if dev == "wheel":
        p.drawEllipse(QRectF(8, 8, 28, 28))
        p.setBrush(QColor(_c("icon")))
        p.drawEllipse(QRectF(19, 19, 6, 6))
        p.setBrush(Qt.NoBrush)
        p.drawLine(22, 22, 22, 9)
        p.drawLine(22, 22, 11, 30)
        p.drawLine(22, 22, 33, 30)
    elif dev == "keyboard":
        p.drawRoundedRect(QRectF(6, 13, 32, 18), 4, 4)
        p.setBrush(QColor(_c("icon")))
        p.setPen(Qt.NoPen)
        for kx in (11, 17, 23, 29):
            p.drawRoundedRect(QRectF(kx, 18, 3, 3), 1, 1)
        p.drawRoundedRect(QRectF(14, 24, 16, 3), 1, 1)
    else:
        p.drawRoundedRect(QRectF(7, 15, 30, 15), 8, 8)
        p.setBrush(QColor(_c("icon")))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(13, 20, 5, 5))
        p.drawEllipse(QRectF(26, 20, 5, 5))
    p.end()
    return QIcon(
        pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    )


def _action_icon(kind: str, color: str, size: int = 16) -> QIcon:
    """lock / power / rebind glyphs in a given color (light for dark bg, dark
    when the toggle is active/white)."""
    s = 40
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(3.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    if kind == "lock":
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(13, 7, 14, 17), 0, 2880)
        p.drawLine(13, 15, 13, 19)
        p.drawLine(27, 15, 27, 19)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(10, 19, 20, 15), 4, 4)
    elif kind == "power":
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(11, 12, 18, 18), 2000, -4640)
        p.drawLine(20, 9, 20, 21)
    else:
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(6, 14, 28, 16), 8, 8)
        p.drawLine(13, 22, 19, 22)
        p.drawLine(16, 19, 16, 25)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawEllipse(QRectF(24, 18, 4, 4))
        p.drawEllipse(QRectF(28, 22, 4, 4))
    p.end()
    return QIcon(
        pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    )


def _kind_icon(kind: str, color: str) -> QIcon:
    """Action glyph in `color`: the official asset (assets/<kind>.png, e.g. power)
    recoloured via its alpha, else the drawn fallback."""
    name = "lock icon v2" if kind == "lock" else kind
    t = _tinted(os.path.join(_ASSETS, name + ".png"), color, 18)
    if t is not None:
        return QIcon(t)
    return _action_icon(kind, color)


def _tab_icon(kind: str, size: int = 20, color: str = None) -> QIcon:
    """Tab glyphs: 'mixer' = horizontal faders, 'extras' = settings gear. Both
    prefer a bundled asset recoloured to `color`, falling back to a drawn glyph
    when the PNG is missing. color defaults to the active theme's icon colour."""
    color = color or _c("icon")
    if kind == "extras":
        t = _tinted(
            os.path.join(_ASSETS, "Overlay icon v4.png"), color, int(size * 1.3)
        )
        if t is not None:
            return QIcon(t)
    if kind == "mixer":
        t = _tinted(os.path.join(_ASSETS, "Mixer new icon v3.png"), color, size)
        if t is not None:
            return QIcon(t)
    s = 40
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    if kind == "mixer":
        pen = QPen(c)
        pen.setWidthF(2.6)
        pen.setCapStyle(Qt.RoundCap)
        for kx, y in ((12, 27), (20, 13), (28, 22)):
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawLine(8, y, 32, y)
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawEllipse(QRectF(kx - 4, y - 4, 8, 8))
    else:
        cx = cy = 20.0
        teeth = QPen(c)
        teeth.setWidthF(4.6)
        teeth.setCapStyle(Qt.RoundCap)
        p.setPen(teeth)
        p.setBrush(Qt.NoBrush)
        for i in range(8):
            a = math.radians(i * 45)
            ca, sa = math.cos(a), math.sin(a)
            p.drawLine(
                int(cx + 8.5 * ca),
                int(cy + 8.5 * sa),
                int(cx + 13.0 * ca),
                int(cy + 13.0 * sa),
            )
        ring = QPen(c)
        ring.setWidthF(3.2)
        p.setPen(ring)
        p.drawEllipse(QRectF(cx - 8.5, cy - 8.5, 17, 17))
        p.drawEllipse(QRectF(cx - 3.4, cy - 3.4, 6.8, 6.8))
    p.end()
    return QIcon(
        pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    )


def _tag_colors(tag: str) -> tuple:
    """(background, text) for the device-card tag pill. Scales the urgency:
    orange = first-class, white = solid-but-newer, gray = unknown territory.
    Unknown tags fall back to the orange accent so a typo is still visible."""
    t = (tag or "").lower()
    if t == "best":
        return (QColor(_ACCENT), QColor(_c("emph_text")))
    if t == "beta":
        return (QColor(_c("emph_fill")), QColor(_c("emph_text")))
    if t == "untested":
        return (QColor(_c("text_disabled")), QColor(_c("text")))
    return (QColor(_ACCENT), QColor(_c("emph_text")))


class _DeviceButton(QPushButton):
    """Device-selector button that paints a small corner tag (e.g. 'Best',
    'Beta', 'Untested') over the icon. Tag colour scales with the tag text
    so the user can read the rough confidence at a glance."""

    def __init__(self, tag: str = ""):
        super().__init__()
        self._tag = tag

    def paintEvent(self, e):
        super().paintEvent(e)
        if not self._tag:
            return None
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(_ui_font(10, QFont.Bold))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(self._tag)
        pad_x, pad_y = _s(6), _s(2)
        w = tw + 2 * pad_x
        h = fm.height() + 2 * pad_y
        rect = QRectF(self.width() - w - _s(4), _s(4), w, h)
        bg, fg = _tag_colors(self._tag)
        _gap = float(_s(2))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(_c("surface")))
        p.drawRoundedRect(
            rect.adjusted(-_gap, -_gap, _gap, _gap),
            (h + 2 * _gap) / 2,
            (h + 2 * _gap) / 2,
        )
        p.setBrush(bg)
        p.drawRoundedRect(rect, h / 2, h / 2)
        p.setPen(fg)
        p.drawText(rect, Qt.AlignCenter, self._tag)
        p.end()


class _SkipModeButton(QPushButton):
    """Skip-input toggle (D-pad / Touchpad swipe). Active-state visual is
    driven purely by QSS (skipbtn[active=true] -> orange outline + white text,
    matching the bind key-caps). Earlier versions painted a corner badge or
    filled the whole pill orange; the outlined look reads as 'engaged' the same
    way a bound cap does, without clipping the centred label."""


class _FadeMenu(QMenu):
    """QMenu that fades in when shown - an instant pop felt abrupt; switching
    between submenus looked flickery. Opacity is forced to 0 in aboutToShow (i.e.
    BEFORE the native popup is mapped, so there's no full-opacity flash frame),
    then eased to 1. Any in-flight fade is stopped first so rapid hover-switches
    don't stack two animations (the flicker)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        _round_menu(self)
        self.aboutToShow.connect(lambda: self.setWindowOpacity(0.0))

    def showEvent(self, e):
        super().showEvent(e)
        prev = getattr(self, "_fade_anim", None)
        if prev is not None:
            prev.stop()
        a = QPropertyAnimation(self, b"windowOpacity", self)
        a.setDuration(130)
        a.setStartValue(self.windowOpacity())
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.OutQuad)
        a.start()
        self._fade_anim = a


def _media_icon(kind: str, color: str = None, size: int = 18) -> QIcon:
    """Media-transport glyphs: shuffle / prev / play / pause / next / repeat.
    color defaults to the active theme's icon colour."""
    color = color or _c("icon")
    s = 40
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(3.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    if kind == "play":
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        path = QPainterPath()
        path.moveTo(15, 11)
        path.lineTo(15, 29)
        path.lineTo(30, 20)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "pause":
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(15, 11, 4.5, 18), 2, 2)
        p.drawRoundedRect(QRectF(21.5, 11, 4.5, 18), 2, 2)
    elif kind == "next":
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        path = QPainterPath()
        path.moveTo(13, 11)
        path.lineTo(13, 29)
        path.lineTo(26, 20)
        path.closeSubpath()
        p.drawPath(path)
        p.drawRoundedRect(QRectF(27, 11, 4, 18), 1.5, 1.5)
    elif kind == "prev":
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        path = QPainterPath()
        path.moveTo(27, 11)
        path.lineTo(27, 29)
        path.lineTo(14, 20)
        path.closeSubpath()
        p.drawPath(path)
        p.drawRoundedRect(QRectF(9, 11, 4, 18), 1.5, 1.5)
    elif kind == "shuffle":
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        a = QPainterPath()
        a.moveTo(8, 13)
        a.lineTo(17, 13)
        a.lineTo(29, 27)
        b = QPainterPath()
        b.moveTo(8, 27)
        b.lineTo(17, 27)
        b.lineTo(29, 13)
        p.drawPath(a)
        p.drawPath(b)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        for tip, k1, k2 in (
            ((31, 27), (24, 27), (30, 20)),
            ((31, 13), (24, 13), (30, 20)),
        ):
            h = QPainterPath()
            h.moveTo(*tip)
            h.lineTo(*k1)
            h.lineTo(*k2)
            h.closeSubpath()
            p.drawPath(h)
    elif kind == "repeat":
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(11, 12, 18, 16), 1248, 4672)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        h = QPainterPath()
        h.moveTo(30, 13)
        h.lineTo(22, 11)
        h.lineTo(26, 18)
        h.closeSubpath()
        p.drawPath(h)
    p.end()
    return QIcon(
        pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    )


def _menu_icon() -> QIcon:
    """Hamburger (3 rounded lines): bundled asset recoloured, else drawn."""
    t = _tinted(os.path.join(_ASSETS, "hamburger menu icon.png"), _c("icon"), 20)
    if t is not None:
        return QIcon(t)
    s = 44
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(_c("icon")))
    for cy in (14, 22, 30):
        p.drawRoundedRect(QRectF(10, cy - 2, 24, 4), 2, 2)
    p.end()
    return QIcon(
        pix.scaled(_s(20), _s(20), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    )


def _caption_icon(kind: str, size: int = 18, color: str = None) -> QIcon:
    """Win11-style caption glyph (min / max / restore / close) as AA vector.

    `color` overrides the glyph tint - used to flip the close X to white while
    its red hover background is showing (a dark themed X on red read muddy)."""
    s = 40
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color or _c("icon")))
    pen.setWidthF(2.6)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    if kind == "min":
        p.drawLine(10, 20, 30, 20)
    elif kind == "max":
        p.drawRect(11, 11, 18, 18)
    elif kind == "restore":
        p.drawRect(11, 15, 14, 14)
        p.drawLine(15, 11, 29, 11)
        p.drawLine(29, 11, 29, 25)
    elif kind == "close":
        p.drawLine(10, 10, 30, 30)
        p.drawLine(30, 10, 10, 30)
    p.end()
    return QIcon(
        pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    )


def _info_icon(size: int = 15, bright: bool = False) -> QPixmap:
    """Small circled-i info glyph (AA vector). Hover target for tooltips."""
    s = size * 3
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    col = QColor("#c4c4c2" if bright else "#8a8a88")
    pen = QPen(col)
    pen.setWidthF(s * 0.075)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    m = s * 0.1
    p.drawEllipse(QRectF(m, m, s - 2 * m, s - 2 * m))
    p.setPen(Qt.NoPen)
    p.setBrush(col)
    cx = s / 2
    p.drawEllipse(QRectF(cx - s * 0.055, s * 0.3, s * 0.11, s * 0.11))
    p.drawRoundedRect(
        QRectF(cx - s * 0.055, s * 0.45, s * 0.11, s * 0.26), s * 0.05, s * 0.05
    )
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _zoom_icon(path: str, sz: int, zoom: float = 1.0) -> QPixmap:
    """Menu icon scaled to `sz`, but enlarged by `zoom` and centre-cropped so
    logos with built-in padding (TIDAL, YT Music) fill the box like the others."""
    pm = QPixmap(path)
    if pm.isNull():
        return pm
    big = pm.scaled(
        int(sz * zoom), int(sz * zoom), Qt.KeepAspectRatio, Qt.SmoothTransformation
    )
    if zoom <= 1.0:
        return big
    out = QPixmap(sz, sz)
    out.fill(QColor(0, 0, 0, 0))
    p = QPainter(out)
    p.drawPixmap(int((sz - big.width()) / 2), int((sz - big.height()) / 2), big)
    p.end()
    return out


def _dim_pixmap(pm: QPixmap) -> QPixmap:
    """Faded copy used when that side is disconnected."""
    out = QPixmap(pm.size())
    out.fill(QColor(0, 0, 0, 0))
    p = QPainter(out)
    p.setOpacity(0.3)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out


def _dev_wm_rot(dev: str, size: int = 90, angle: float = 14.0):
    """Device glyph rotated slightly clockwise, for the Controls pill's big
    right-side background watermark. None if the device has no glyph.

    Recoloured to the theme's icon colour (dark in light, light in dark) so it
    reads on both backgrounds. `_dev_pixmap` inverts the black line-art to white
    for the dark UI, which would leave it invisible on the near-white light bg;
    flattening to a single tint is fine here since it's painted at ~0.16 opacity.
    Scoped to the watermark (NOT _dev_pixmap) so the device-picker cards keep
    their full line-art shading."""
    pm = _dev_pixmap(dev, size)
    if pm is None or pm.isNull():
        return pm
    tint = QPixmap(pm.size())
    tint.fill(QColor(0, 0, 0, 0))
    _tp = QPainter(tint)
    _tp.drawPixmap(0, 0, pm)
    _tp.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    _tp.fillRect(tint.rect(), QColor(_c("icon")))
    _tp.end()
    pm = tint
    from PySide6.QtGui import QTransform

    return pm.transformed(QTransform().rotate(angle), Qt.SmoothTransformation)


def _paint_pill_backdrop(
    btn, e, pm, radius, opacity=0.12, hfrac=0.5, hscale=1.7, vfrac=0.5, fade=False
):
    """Paint a big, faint, edge-cropped icon behind a pill button's text - a
    watermark (e.g. the active controller) that doesn't compete with the label.
    Mirrors the source picker's oversized cropped icons. Runs the button's
    normal QSS paint first, then overlays the icon clipped to the rounded rect
    so it's cropped by the borders; child text labels paint on top after.
    hfrac = horizontal centre as a fraction of width (0.5 = middle, lower = left
    side); hscale = icon height as a multiple of the button height."""
    from PySide6.QtWidgets import QPushButton

    QPushButton.paintEvent(btn, e)
    if pm is None or pm.isNull():
        return None
    r = btn.rect()
    p = QPainter(btn)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(QRectF(r), radius, radius)
    p.setClipPath(path)
    p.setOpacity(opacity)
    sp = pm.scaledToHeight(int(r.height() * hscale), Qt.SmoothTransformation)
    if fade:
        from PySide6.QtGui import QLinearGradient

        _f = QPixmap(sp.size())
        _f.fill(QColor(0, 0, 0, 0))
        _fp = QPainter(_f)
        _fp.drawPixmap(0, 0, sp)
        _fp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        _g = QLinearGradient(0, 0, sp.width(), 0)
        if hfrac < 0.5:
            _g.setColorAt(0.0, QColor(0, 0, 0, 255))
            _g.setColorAt(0.55, QColor(0, 0, 0, 255))
            _g.setColorAt(1.0, QColor(0, 0, 0, 0))
        else:
            _g.setColorAt(0.0, QColor(0, 0, 0, 0))
            _g.setColorAt(0.45, QColor(0, 0, 0, 255))
            _g.setColorAt(1.0, QColor(0, 0, 0, 255))
        _fp.fillRect(_f.rect(), _g)
        _fp.end()
        sp = _f
    p.drawPixmap(
        int(r.left() + r.width() * hfrac - sp.width() / 2),
        int(r.top() + r.height() * vfrac - sp.height() / 2),
        sp,
    )
    p.end()


def _launcher_icon(
    base, box: int, *, spinner: bool = False, angle=0, dx: int = 0, glow: float = 1.0
) -> QIcon:
    """Source icon DIMMED with a launch affordance centred on top: a power glyph
    ('turn it on') or, while launching, a rotating arc. The source art stays
    visible behind it instead of vanishing - the glyph reads as an overlay, not a
    replacement. Built as one pixmap so Qt centres the whole thing where the
    source icon sits (no overlay-vs-icon misalignment to chase)."""
    pm = QPixmap(box, box)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setRenderHint(QPainter.Antialiasing)
    bp = base.pixmap(box, box)
    if not bp.isNull():
        p.setOpacity(0.3)
        p.drawPixmap(0, 0, bp)
        p.setOpacity(1.0)
    if spinner:
        pen = QPen(QColor(_c("icon")), max(2.0, box * 0.09))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        rad = box * 0.3
        c = box / 2.0
        p.drawArc(
            QRectF(c + dx - rad, c - rad, 2 * rad, 2 * rad),
            int(-angle * 16),
            int(-4320),
        )
    else:
        d = max(1, int(box * 0.6))
        off = (box - d) // 2
        _g = max(0.0, min(1.0, glow))
        _v = int(140 + 115 * _g)
        _gl = _kind_icon("power", f"#{_v:02x}{_v:02x}{_v:02x}").pixmap(d, d)
        _sh = _kind_icon("power", "#000000").pixmap(d, d)
        p.setOpacity(0.5)
        p.drawPixmap(off + 1, off + 1, _sh)
        p.setOpacity(0.55 + 0.45 * _g)
        p.drawPixmap(off, off, _gl)
    p.end()
    return QIcon(pm)


def _bulb_pixmap(size: int = 18, color: str = "#ff8a16") -> QPixmap:
    """Lightbulb glyph for the 'Tip' callout cards. Vector so it stays
    crisp at any UI scale."""
    s = 64
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(3.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(18, 8, 28, 28))
    p.drawLine(28, 36, 36, 36)
    p.drawLine(26, 42, 38, 42)
    p.drawLine(27, 48, 37, 48)
    p.drawLine(29, 54, 35, 54)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _trash_pixmap(size: int = 18, color: str = None) -> QPixmap:
    """Simple trash-can glyph for the per-row delete button in the presets
    popup. Drawn vector so it stays crisp at any UI scale."""
    color = color or _c("icon_dim")
    s = 64
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(3.4)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawLine(14, 18, 50, 18)
    p.drawLine(26, 18, 27, 12)
    p.drawLine(38, 18, 37, 12)
    p.drawLine(27, 12, 37, 12)
    path = QPainterPath()
    path.moveTo(18, 22)
    path.lineTo(21, 52)
    path.lineTo(43, 52)
    path.lineTo(46, 22)
    p.drawPath(path)
    p.drawLine(27, 28, 28, 46)
    p.drawLine(32, 28, 32, 46)
    p.drawLine(37, 28, 36, 46)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _save_pixmap(size: int = 18, color: str = None) -> QPixmap:
    """Floppy-disk 'save' glyph for the Save-current row in the presets popup."""
    color = color or _c("icon_dim")
    s = 64
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(3.4)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(14, 14)
    path.lineTo(44, 14)
    path.lineTo(50, 20)
    path.lineTo(50, 50)
    path.lineTo(14, 50)
    path.closeSubpath()
    p.drawPath(path)
    p.drawRect(QRectF(22, 36, 20, 12))
    p.drawRect(QRectF(22, 16, 16, 10))
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _globe_pixmap(size: int = 28) -> QPixmap:
    """White globe glyph for the 'Browser' source (YouTube etc.)."""
    s = 64
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(_c("text")))
    pen.setWidthF(3.2)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(7, 7, 50, 50))
    p.drawEllipse(QRectF(23, 7, 18, 50))
    p.drawLine(32, 7, 32, 57)
    p.drawLine(9, 25, 55, 25)
    p.drawLine(9, 39, 55, 39)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _refresh_pixmap(size: int = 16, color: str = None, angle: float = 0.0) -> QPixmap:
    """Circular-arrow 'check for updates' glyph. `angle` spins it (click anim)."""
    color = color or _c("icon_dim")
    import math

    s = 64
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    cx, cy, r = (32, 36, 18)
    if angle:
        p.translate(cx, cy)
        p.rotate(angle)
        p.translate(-cx, -cy)
    pen = QPen(QColor(color))
    pen.setWidthF(6.5)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    start_deg, span_deg = (55, 280)
    p.drawArc(
        QRectF(cx - r, cy - r, 2 * r, 2 * r), int(start_deg * 16), int(span_deg * 16)
    )
    end = math.radians(start_deg + span_deg)
    ex, ey = (cx + r * math.cos(end), cy - r * math.sin(end))
    tx, ty = (-math.sin(end), -math.cos(end))
    px, py = (-ty, tx)
    a = 8.0
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    tri = QPainterPath()
    tri.moveTo(ex + tx * a, ey + ty * a)
    tri.lineTo(ex - tx * 2 + px * a * 0.8, ey - ty * 2 + py * a * 0.8)
    tri.lineTo(ex - tx * 2 - px * a * 0.8, ey - ty * 2 - py * a * 0.8)
    tri.closeSubpath()
    p.drawPath(tri)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _undo_pixmap(size: int = 20, color: str = "#9a9a98") -> QPixmap:
    """Bold 'undo' arrow (matches the chunky reference): a thick shaft running
    LEFT into a big arrowhead, then two 90-degree bends on the tail (right ->
    down -> small left foot). Arrowhead points left (revert / back), distinct
    from the circular refresh glyph."""
    color = color or _c("icon_dim")
    s = 100
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    col = QColor(color)
    pen = QPen(col)
    pen.setWidthF(11)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(44, 33)
    path.lineTo(64, 33)
    path.quadTo(78, 33, 78, 47)
    path.lineTo(78, 60)
    path.quadTo(78, 73, 65, 73)
    path.lineTo(57, 73)
    p.drawPath(path)
    p.setPen(Qt.NoPen)
    p.setBrush(col)
    tri = QPainterPath()
    tri.moveTo(14, 33)
    tri.lineTo(42, 16)
    tri.lineTo(42, 50)
    tri.closeSubpath()
    p.drawPath(tri)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _move_pixmap(size: int = 20, color: str = None) -> QPixmap:
    """4-way move glyph: a plus-shaped cross with an arrowhead on each end
    (the universal 'drag to reposition' symbol). Used by the overlay
    'Move on screen' button."""
    color = color or _c("icon_dim")
    s = 100
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    col = QColor(color)
    cx, cy = (50, 50)
    pen = QPen(col)
    pen.setWidthF(10)
    pen.setCapStyle(Qt.FlatCap)
    pen.setJoinStyle(Qt.MiterJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawLine(24, cy, 76, cy)
    p.drawLine(cx, 24, cx, 76)
    p.setPen(Qt.NoPen)
    p.setBrush(col)
    h = 14
    for tip, b1, b2 in (
        ((8, cy), (26, cy - h), (26, cy + h)),
        ((92, cy), (74, cy - h), (74, cy + h)),
        ((cx, 8), (cx - h, 26), (cx + h, 26)),
        ((cx, 92), (cx - h, 74), (cx + h, 74)),
    ):
        tri = QPainterPath()
        tri.moveTo(*tip)
        tri.lineTo(*b1)
        tri.lineTo(*b2)
        tri.closeSubpath()
        p.drawPath(tri)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _mic_pixmap(size: int = 16, color: str = None) -> QPixmap:
    """Microphone glyph: a rounded capsule body, a U-shaped pickup bracket, a
    stem and a base. Compact label for the 'Duck on my voice' toggle."""
    color = color or _c("icon_dim")
    s = 100
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    col = QColor(color)
    p.setPen(Qt.NoPen)
    p.setBrush(col)
    p.drawRoundedRect(QRectF(38, 16, 24, 46), 12, 12)
    pen = QPen(col)
    pen.setWidthF(7)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(28, 30, 44, 44), 2880, 2880)
    p.drawLine(50, 74, 50, 86)
    p.drawLine(38, 88, 62, 88)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _smooth_scroll(area):
    """Smooth wheel scrolling: a refresh-rate timer eases the scrollbar toward
    an accumulating target, instead of the old per-notch QPropertyAnimation that
    restarted its OutCubic on every notch (continuous scrolling then felt like a
    string of decelerating hops - chunky / low-fps). Each notch just adds to the
    target; the value chases it at a constant fraction per frame, so a run of
    notches glides as one motion. Wheel-driven widgets (combo / slider / spin)
    under the cursor keep their own wheel behaviour."""
    from PySide6.QtCore import QTimer, QObject, QEvent, Qt
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QAbstractSlider,
        QAbstractSpinBox,
    )

    sb = area.verticalScrollBar()
    area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    sb.setCursor(Qt.ClosedHandCursor)
    import math

    refresh = 60.0
    try:
        _sc = area.screen() or QApplication.primaryScreen()
        if _sc is not None and _sc.refreshRate() > 0:
            refresh = float(_sc.refreshRate())
    except Exception:
        pass
    interval = max(3, int(round(1000.0 / refresh)))
    ease = 1.0 - math.exp(-interval / 55.0)
    state = {"target": float(sb.value())}
    timer = QTimer(area)
    timer.setTimerType(Qt.PreciseTimer)
    timer.setInterval(interval)

    def _tick():
        tgt = max(sb.minimum(), min(sb.maximum(), state["target"]))
        state["target"] = tgt
        cur = sb.value()
        diff = tgt - cur
        if abs(diff) < 1:
            sb.setValue(int(round(tgt)))
            timer.stop()
            return None
        step = diff * ease
        if abs(step) < 1:
            step = 1.0 if diff > 0 else -1.0
        sb.setValue(int(round(cur + step)))

    timer.timeout.connect(_tick)

    class _Wheel(QObject):
        def eventFilter(self, obj, e):
            if e.type() != QEvent.Wheel:
                return False
            if sb.maximum() <= sb.minimum():
                return False
            w = QApplication.widgetAt(e.globalPosition().toPoint())
            while w is not None and w is not area:
                if isinstance(w, (QComboBox, QAbstractSlider, QAbstractSpinBox)):
                    return False
                w = w.parentWidget()
            d = e.angleDelta().y()
            if d == 0:
                return False
            base = state["target"] if timer.isActive() else float(sb.value())
            state["target"] = max(sb.minimum(), min(sb.maximum(), base - d))
            if not timer.isActive():
                timer.start()
            return True

    flt = _Wheel(area)
    area.viewport().installEventFilter(flt)
    area._smooth_wheel = flt
    area._smooth_timer = timer
    area._smooth_state = state


class _FadeScroll(QScrollArea):
    """Scroll area with a soft top + bottom fade, so content melts into the
    dialog background at the edges. Position-aware: the top fade only shows once
    you've scrolled down, the bottom only while there's more content below - so
    nothing is dimmed at rest."""

    def __init__(self, bg=None, fade_top=14, fade_bot=30, parent=None):
        super().__init__(parent)
        self._bg = QColor(bg if bg is not None else _c("sunk"))
        self._ft = fade_top
        self._fb = fade_bot
        self._top = QWidget(self)
        self._bot = QWidget(self)
        for _w in (self._top, self._bot):
            _w.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._top.paintEvent = lambda e: self._paint_fade(self._top, True)
        self._bot.paintEvent = lambda e: self._paint_fade(self._bot, False)
        self.verticalScrollBar().valueChanged.connect(self._update_fades)
        _smooth_scroll(self)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        vw = self.viewport().width()
        self._top.setGeometry(0, 0, vw, _s(self._ft))
        self._bot.setGeometry(0, self.height() - _s(self._fb), vw, _s(self._fb))
        self._top.raise_()
        self._bot.raise_()
        self._update_fades()

    def _update_fades(self):
        sb = self.verticalScrollBar()
        self._top.setVisible(sb.value() > sb.minimum())
        self._bot.setVisible(sb.value() < sb.maximum())

    def _paint_fade(self, w, top):
        p = QPainter(w)
        g = QLinearGradient(0, 0, 0, w.height())
        c_op = QColor(self._bg)
        c_tr = QColor(self._bg)
        c_tr.setAlpha(0)
        g.setColorAt(0.0, c_op if top else c_tr)
        g.setColorAt(1.0, c_tr if top else c_op)
        p.fillRect(w.rect(), g)
        p.end()

    def setWidget(self, w):
        if w is not None:
            name = w.objectName() or "fadescrollbody"
            w.setObjectName(name)
            w.setStyleSheet(
                (w.styleSheet() or "")
                + f"\nQWidget#{name}{{background:{self._bg.name()};}}"
            )
        super().setWidget(w)


class _FadeLabel(QLabel):
    """Left-aligned single-line label whose text fades out at the right edge when
    it overflows the widget (instead of a hard clip / ellipsis). Used for the
    update banner headline so it degrades nicely on a narrow window."""

    def __init__(self, text="", fade=34, parent=None):
        super().__init__(text, parent)
        self._fade = fade
        self._color = QColor(_c("text"))

    def setTextColor(self, c):
        self._color = QColor(c)
        self.update()

    def minimumSizeHint(self):
        return QSize(_s(16), self.fontMetrics().height())

    def paintEvent(self, e):
        from PySide6.QtGui import QImage

        txt = self.text()
        flags = int(Qt.AlignLeft | Qt.AlignVCenter)
        avail = self.width()
        if self.fontMetrics().horizontalAdvance(txt) <= avail:
            p = QPainter(self)
            p.setFont(self.font())
            p.setPen(self._color)
            p.drawText(self.rect(), flags, txt)
            return None
        img = QImage(
            max(1, self.width()),
            max(1, self.height()),
            QImage.Format_ARGB32_Premultiplied,
        )
        img.fill(0)
        ip = QPainter(img)
        ip.setFont(self.font())
        ip.setPen(self._color)
        ip.drawText(self.rect(), flags, txt)
        f = min(_s(self._fade), avail)
        g = QLinearGradient(avail - f, 0, avail, 0)
        g.setColorAt(0.0, QColor(0, 0, 0, 255))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        ip.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        ip.fillRect(QRectF(avail - f, 0, f, self.height()), g)
        ip.end()
        QPainter(self).drawImage(0, 0, img)


class _VerButton(QPushButton):
    """Version label + refresh icon as ONE clickable, hover-highlighted unit.
    Dim at rest (matches the old version label), brightens on hover; the icon
    spins during a check."""

    def __init__(self, version_text: str):
        super().__init__()
        self.setObjectName("verbar")
        self.setCursor(Qt.PointingHandCursor)
        self.setText(version_text)
        self.setLayoutDirection(Qt.RightToLeft)
        self._dim = _c("verbar_text")
        self._bright = _c("verbar_text_hi")
        self._check = _c("success")
        self._angle = 0.0
        self._mode = "refresh"
        self._paint_icon(self._dim)

    def _paint_icon(self, color: str) -> None:
        if self._mode == "check":
            self.setIcon(QIcon(_check_pixmap(15, self._check)))
            return None
        self.setIcon(QIcon(_refresh_pixmap(15, color, self._angle)))

    def set_angle(self, a: float) -> None:
        self._mode = "refresh"
        self._angle = a
        self._paint_icon(self._bright)

    def show_check(self) -> None:
        """Swap the arrow for a green checkmark (check finished, up to date)."""
        self._mode = "check"
        self._paint_icon(self._check)

    def show_refresh(self) -> None:
        """Back to the refresh arrow (dim, or bright if hovered)."""
        self._mode = "refresh"
        self._paint_icon(self._bright if self.underMouse() else self._dim)

    def _retint(self) -> None:
        """Re-read theme colours + repaint the icon (live theme switch); the
        baked _dim/_bright/_check were stale after a switch."""
        self._dim = _c("verbar_text")
        self._bright = _c("verbar_text_hi")
        self._check = _c("success")
        self._paint_icon(
            self._check
            if self._mode == "check"
            else self._bright
            if self.underMouse()
            else self._dim
        )

    def enterEvent(self, e):
        self._paint_icon(self._bright)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._paint_icon(self._dim)
        super().leaveEvent(e)


def _check_pixmap(size: int = 15, color: str = "#3FB950") -> QPixmap:
    """Checkmark glyph - the version button's 'up to date' state (replaces the
    refresh arrow once a check finds no update)."""
    s = 100
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(13)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(20, 60)
    path.lineTo(42, 80)
    path.lineTo(82, 34)
    p.drawPath(path)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _question_pixmap(size: int = 15, color: str = None) -> QPixmap:
    """Question-mark glyph (Help -> Open guide menu icon)."""
    color = color or _c("icon_dim")
    s = 100
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    f = QFont("Segoe UI", 74)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(pix.rect(), Qt.AlignCenter, "?")
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _play_pixmap(size: int = 15, color: str = None) -> QPixmap:
    """Filled play triangle (Help -> Replay tour menu icon)."""
    color = color or _c("icon_dim")
    s = 100
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    tri = QPainterPath()
    tri.moveTo(30, 22)
    tri.lineTo(30, 78)
    tri.lineTo(80, 50)
    tri.closeSubpath()
    p.drawPath(tri)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _x_pixmap(size: int = 12, color: str = "#1f1f1e") -> QPixmap:
    """Crisp anti-aliased X (two round-capped diagonals) for the banner close
    button - the "✕" text glyph rendered choppy at small bold sizes."""
    s = 64
    pm = QPixmap(s, s)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(7)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    m = 19
    p.drawLine(m, m, s - m, s - m)
    p.drawLine(s - m, m, m, s - m)
    p.end()
    return pm.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _sparkle_pixmap(size: int = 14, color: str = "#1f1f1e") -> QPixmap:
    """Crisp multi-point sparkle (one big + two small 4-point stars, the Tabler
    'sparkles' look) for the update banner's leading glyph. Recolored to the
    banner's contrast text color in _apply_banner_color (like the × close icon)."""
    s = 64
    pm = QPixmap(s, s)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))

    def star(cx, cy, R, w):
        path = QPainterPath()
        path.moveTo(cx, cy - R)
        path.cubicTo(cx + w, cy - w, cx + w, cy - w, cx + R, cy)
        path.cubicTo(cx + w, cy + w, cx + w, cy + w, cx, cy + R)
        path.cubicTo(cx - w, cy + w, cx - w, cy + w, cx - R, cy)
        path.cubicTo(cx - w, cy - w, cx - w, cy - w, cx, cy - R)
        p.drawPath(path)

    star(s * 0.44, s * 0.5, s * 0.34, s * 0.085)
    star(s * 0.8, s * 0.23, s * 0.16, s * 0.04)
    star(s * 0.23, s * 0.81, s * 0.135, s * 0.034)
    p.end()
    return pm.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _update_pixmap(size: int = 14, color: str = "#1f1f1e") -> QPixmap:
    """Download/update glyph (down arrow into a tray) for the update banner's
    leading icon. Recolored to the banner's contrast text in _apply_banner_color.
    The sparkle look is kept as _sparkle_pixmap if we want to switch back."""
    s = 64
    pm = QPixmap(s, s)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(s * 0.105)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    cx = s * 0.5
    p.drawLine(int(cx), int(s * 0.15), int(cx), int(s * 0.55))
    chev = QPainterPath()
    chev.moveTo(cx - s * 0.18, s * 0.37)
    chev.lineTo(cx, s * 0.58)
    chev.lineTo(cx + s * 0.18, s * 0.37)
    p.drawPath(chev)
    tray = QPainterPath()
    tray.moveTo(cx - s * 0.27, s * 0.63)
    tray.lineTo(cx - s * 0.27, s * 0.83)
    tray.lineTo(cx + s * 0.27, s * 0.83)
    tray.lineTo(cx + s * 0.27, s * 0.63)
    p.drawPath(tray)
    p.end()
    return pm.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


class _BigMenuIconStyle(QProxyStyle):
    """QMenu hard-locks action icons to PM_SmallIconSize (~16px) and they paint
    tiny + edge-hugging (same reason the source picker uses _IconPopup). Override
    that one metric so a QMenu renders its icons at the app scale, crisp - without
    rebuilding the whole nested menu as custom popups."""

    def __init__(self, px: int):
        super().__init__()
        self._px = int(px)

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PixelMetric.PM_SmallIconSize:
            return self._px
        return super().pixelMetric(metric, option, widget)


def _rounded_bordered(src, radius, border="#4d4c47", bw=1.0):
    """Clip an image to a rounded rect + stroke a subtle 1px border - a framed
    preview for the What's-new dialog (so screenshots aren't bare rectangles)."""
    if src is None or src.isNull():
        return src
    out = QPixmap(src.size())
    out.fill(QColor(0, 0, 0, 0))
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    r = QRectF(bw / 2, bw / 2, src.width() - bw, src.height() - bw)
    clip = QPainterPath()
    clip.addRoundedRect(r, radius, radius)
    p.setClipPath(clip)
    p.drawPixmap(0, 0, src)
    p.setClipping(False)
    pen = QPen(QColor(border))
    pen.setWidthF(bw)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(r, radius, radius)
    p.end()
    return out


_CHEV_CACHE = {}


def _chevron_pixmap(size: int, color: str = None) -> QPixmap:
    """Right-pointing chevron '>' for the submenu arrow (Qt's native one is ~7px
    and invisible on dark themes; this scales with the menu font)."""
    color = color or _c("icon_dim")
    s = 64
    pm = QPixmap(s, s)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(7)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawLine(int(s * 0.4), int(s * 0.24), int(s * 0.64), int(s * 0.5))
    p.drawLine(int(s * 0.64), int(s * 0.5), int(s * 0.4), int(s * 0.76))
    p.end()
    return pm.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _chevron_qss_path(size: int, color: str = None) -> str:
    """Paint the chevron to a cached PNG and return a QSS-friendly (forward-slash)
    path, so QMenu::right-arrow can reference it as an image - which Qt then
    right-aligns natively. Empty string on failure (arrow just hides)."""
    color = color or _c("icon_dim")
    key = (int(_s(size)), color)
    cached = _CHEV_CACHE.get(key)
    if cached and os.path.exists(cached):
        return cached
    import tempfile

    path = os.path.join(
        tempfile.gettempdir(), f"segue_chev_{key[0]}_{color.lstrip('#')}.png"
    )
    try:
        _chevron_pixmap(size, color).save(path, "PNG")
        qss = path.replace("\\", "/")
        _CHEV_CACHE[key] = qss
        return qss
    except Exception:
        return ""


_DOWNCHEV_CACHE = {}


def _down_chevron_qss_path(size: int, color: str = None) -> str:
    """Tinted down-chevron asset -> cached PNG path for QComboBox::down-arrow,
    so every dropdown uses the shipped chevron glyph instead of the native
    Windows arrow. Empty string on failure (combo falls back to no image)."""
    color = color or _c("icon_dim")
    key = (int(_s(size)), color)
    cached = _DOWNCHEV_CACHE.get(key)
    if cached and os.path.exists(cached):
        return cached
    pm = _tinted(os.path.join(_ASSETS, "down-chevron.png"), color, size)
    if pm is None:
        return ""
    import tempfile

    path = os.path.join(
        tempfile.gettempdir(), f"segue_downchev_{key[0]}_{color.lstrip('#')}.png"
    )
    try:
        pm.save(path, "PNG")
        qss = path.replace("\\", "/")
        _DOWNCHEV_CACHE[key] = qss
        return qss
    except Exception:
        return ""


_CHECK_CACHE = {}


def _check_qss_path(size: int, color: str = "#f0f0f0") -> str:
    """Painted check glyph -> cached PNG path for QMenu::indicator:checked. The
    native menu checkmark renders tiny + dim; this is bigger + theme-coloured."""
    key = (int(_s(size)), color)
    cached = _CHECK_CACHE.get(key)
    if cached and os.path.exists(cached):
        return cached
    import tempfile

    path = os.path.join(
        tempfile.gettempdir(), f"segue_check_{key[0]}_{color.lstrip('#')}.png"
    )
    try:
        _check_pixmap(size, color).save(path, "PNG")
        qss = path.replace("\\", "/")
        _CHECK_CACHE[key] = qss
        return qss
    except Exception:
        return ""


def _badge_html(label: str, bg: str, fg: str) -> str:
    """A rounded pill badge (NEW / FIXED / ...) as an inline <img> data URI, so
    it lives INSIDE the rich text - wrapped lines then start under the badge
    instead of in a separate column. Supersampled x2 for crisp text."""
    import base64
    from PySide6.QtCore import QBuffer, QByteArray

    bf = _ui_font(9, QFont.Bold)
    fm = QFontMetrics(bf)
    img_h = max(1, QFontMetrics(_ui_font(14)).ascent())
    pad_x = _s(6)
    pill_w = fm.horizontalAdvance(label) + 2 * pad_x
    pill_h = min(img_h, fm.height())
    y0 = (img_h - pill_h) / 2.0
    ss = 3
    big = QPixmap(int(pill_w * ss), int(img_h * ss))
    big.fill(QColor(0, 0, 0, 0))
    p = QPainter(big)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(bg))
    _rect = QRectF(0, y0 * ss, pill_w * ss, pill_h * ss)
    _r = _s(4) * ss
    p.drawRoundedRect(_rect, _r, _r)
    fb = QFont(bf)
    if bf.pixelSize() > 0:
        fb.setPixelSize(bf.pixelSize() * ss)
    else:
        fb.setPointSizeF(bf.pointSizeF() * ss)
    p.setFont(fb)
    p.setPen(QColor(fg))
    p.drawText(_rect, Qt.AlignCenter, label)
    p.end()
    pm = big.scaled(
        int(pill_w), int(img_h), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
    )
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.WriteOnly)
    pm.save(buf, "PNG")
    buf.close()
    uri = "data:image/png;base64," + base64.b64encode(bytes(ba)).decode("ascii")
    return f"<img src='{uri}' width='{int(pill_w)}' height='{int(img_h)}' style='vertical-align:baseline'>"


def _folder_pixmap(size: int = 28) -> QPixmap:
    """White folder glyph for the 'Local files' source (reads as files, not the
    generic music note)."""
    s = 64
    pix = QPixmap(s, s)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    col = QColor(_c("text"))
    p.setPen(Qt.NoPen)
    p.setBrush(col)
    folder = QPainterPath()
    folder.addRoundedRect(QRectF(8, 17, 22, 10), 4, 4)
    folder.addRoundedRect(QRectF(8, 22, 48, 31), 6, 6)
    p.drawPath(folder.simplified())
    p.setPen(QPen(QColor(0, 0, 0, 70), 2))
    p.setBrush(Qt.NoBrush)
    p.drawLine(13, 31, 51, 31)
    p.end()
    return pix.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)


_ASSETS = os.path.join(os.path.dirname(__file__), "assets")
_FORZA = os.path.join(_ASSETS, "forza.png")
_SPOTIFY = os.path.join(_ASSETS, "spotify.png")
_LINK = os.path.join(_ASSETS, "link.png")
_LINK_BROKEN = os.path.join(_ASSETS, "link_broken.png")
_APP_ICON = os.path.join(_ASSETS, "segue.png")
_SUPPORT_URL = "https://ko-fi.com/segueapp"
_DISCORD_URL = "https://discord.gg/AUrMXdzGZE"


def _load_scaled(path: str, size: int):
    """Load an asset scaled into a size box (keep aspect), or None if missing."""
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            return pm.scaled(
                _s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
    return None


def _load_icon(path: str, size: int = 20):
    pm = _load_scaled(path, size)
    if pm is not None:
        return QIcon(pm)


def _apply_dwm_titlebar(widget) -> None:
    """Match a native window's title bar to the ACTIVE Segue theme (Windows).
    Dialogs use the native frame, which otherwise follows the SYSTEM dark/light
    setting - so a dark-mode Windows showed dark title bars under Segue's light
    theme. DWMWA_USE_IMMERSIVE_DARK_MODE (20) = 0 light / 1 dark."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        hwnd = int(widget.winId())
        val = ctypes.byref(ctypes.c_int(0 if _active_theme() == "light" else 1))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, val, 4)
    except Exception:
        pass


def _round_menu(m) -> None:
    """No-op: menu rounding is now the NATIVE Win11 frame (the QSS sets only the
    fill, no border/radius), so a single corner. Translucent/DONOTROUND hacks
    fought the native rendering and left the double corner; kept as a no-op so
    the call sites stay harmless."""
    pass


def _tinted(path: str, color: str, size: int):
    """Recolor an asset (uses its alpha) to `color` at `size`, or None if absent.
    Lets a single white PNG serve both light (dark bg) and dark (white bg) states."""
    if not os.path.exists(path):
        return None
    src = QPixmap(path)
    if src.isNull():
        return None
    src = src.scaled(_s(size), _s(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    out = QPixmap(src.size())
    out.fill(QColor(0, 0, 0, 0))
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    p.drawPixmap(0, 0, src)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(out.rect(), QColor(color))
    p.end()
    return out


def _media_pixmap(kind: str, color: str, size: int) -> QPixmap:
    """A media glyph: tinted asset (assets/media_<kind>.png) if present, else drawn."""
    t = _tinted(os.path.join(_ASSETS, f"media_{kind}.png"), color, size)
    if t is not None:
        return t
    return _media_icon(kind, color, size).pixmap(QSize(_s(size), _s(size)))


_SENS_HI_THRESH = 0.85
_SENS_LO_THRESH = 0.15


def _sens_to_thresh(sens: int) -> float:
    """Sensitivity slider (0-100) -> Silero vad_threshold. Higher sensitivity =
    lower threshold = ducks more readily."""
    s = max(0, min(100, int(sens)))
    return round(_SENS_HI_THRESH - (_SENS_HI_THRESH - _SENS_LO_THRESH) * s / 100.0, 3)


def _thresh_to_sens(thresh: float) -> int:
    """Inverse of _sens_to_thresh: vad_threshold -> sensitivity 0-100."""
    span = _SENS_HI_THRESH - _SENS_LO_THRESH
    s = (_SENS_HI_THRESH - float(thresh)) / span * 100.0
    return int(round(max(0.0, min(100.0, s))))


_XBOX_BTN = {
    0: "A",
    1: "B",
    2: "X",
    3: "Y",
    4: "LB",
    5: "RB",
    6: "View",
    7: "Menu",
    8: "LS",
    9: "RS",
}
_XBOX_FACE = {0: "A", 1: "B", 2: "X", 3: "Y"}
_PS_LABELS = {
    "cross": "✕",
    "circle": "◯",
    "square": "▢",
    "triangle": "△",
    "L1": "L1",
    "R1": "R1",
    "L2": "L2",
    "R2": "R2",
    "L3": "L3",
    "R3": "R3",
    "DpadUp": "D-pad ↑",
    "DpadDown": "D-pad ↓",
    "DpadLeft": "D-pad ←",
    "DpadRight": "D-pad →",
    "micBtn": "Mic",
    "share": "Share",
    "create": "Create",
    "options": "Options",
    "touchpad": "Touchpad",
}


def _pretty_code(code: str, device: str = None) -> str:
    """Human label for a binding code. `device="xbox"` makes btn:N read as
    A/B/X/Y/LB/... instead of the generic "Button N"."""
    if not code:
        return "Unbound"
    if "+" in code and not code.startswith("key:"):
        return " + ".join((_pretty_code(p, device) for p in code.split("+")))
    if code.startswith("btn:"):
        if device == "xbox":
            try:
                return _XBOX_BTN.get(int(code[4:]), "Button " + code[4:])
            except ValueError:
                pass
        return "Button " + code[4:]
    if code.startswith("hat:"):
        parts = code.split(":")
        return "D-pad " + (parts[2].capitalize() if len(parts) > 2 else "")
    if code.startswith("key:"):
        try:
            nums = [int(p) for p in code[4:].split("+") if p != ""]
        except ValueError:
            return f"Key {code[4:]}"
        if not nums:
            return "Unbound"
        mod_names = {17: "Ctrl", 16: "Shift", 18: "Alt"}
        mods = [mod_names[m] for m in (17, 16, 18) if m in nums[:-1]]
        return " + ".join(mods + [_vk_label(nums[-1])])
    return _PS_LABELS.get(code, code)


def _is_dev() -> bool:
    """Dev-only tools (Demo mode, Preview update banner) appear ONLY when this
    is true - never in shipped builds. Enabled by the env var SEGUE_DEV or a
    marker file %APPDATA%/Segue/dev.flag (persists across reinstalls)."""
    if os.environ.get("SEGUE_DEV"):
        return True
    try:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.exists(os.path.join(base, "Segue", "dev.flag"))
    except Exception:
        return False


_PS_FACE = ("cross", "circle", "square", "triangle")


def _ps_face_pixmap(name: str, px: int, color: str = "#ffffff"):
    """Draw a DualSense face button (outer ring + the shape) at a fixed size so
    all four read the same weight - Unicode glyphs render at wildly different
    sizes (□ tiny, ◯ huge) and have no enclosing ring. Anti-aliased. `color`
    lets it sit on light buttons (dark glyph) as well as dark ones."""
    if name not in _PS_FACE:
        return None
    from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QPolygonF
    from PySide6.QtCore import QRectF, QPointF

    px = int(px)
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.5, px * 0.075))
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    om = px * 0.06
    p.drawEllipse(QRectF(om, om, px - 2 * om, px - 2 * om))
    im = px * 0.33
    w = px - 2 * im
    cx = px / 2
    if name == "circle":
        cm = px * 0.25
        p.drawEllipse(QRectF(cm, cm, px - 2 * cm, px - 2 * cm))
    elif name == "square":
        p.drawRect(QRectF(im, im, w, w))
    elif name == "triangle":
        h = px * 0.42
        a = px / 2 - 2 * h / 3
        bw = px * 0.25
        p.drawPolygon(
            QPolygonF(
                [QPointF(cx, a), QPointF(cx + bw, a + h), QPointF(cx - bw, a + h)]
            )
        )
    else:
        p.drawLine(QPointF(im, im), QPointF(px - im, px - im))
        p.drawLine(QPointF(px - im, im), QPointF(im, px - im))
    p.end()
    return pm


def _xbox_face_pixmap(letter: str, px: int, color: str = "#ffffff"):
    """Draw an Xbox face button: outer ring (same weight as the DualSense glyphs)
    + the letter A/B/X/Y centered. Monochrome to match the PS glyph style - the
    iconic green/red/blue/yellow would clash with Segue's tonal UI."""
    from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QFontMetrics
    from PySide6.QtCore import QRectF, QPointF

    px = int(px)
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.5, px * 0.075))
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    om = px * 0.06
    p.drawEllipse(QRectF(om, om, px - 2 * om, px - 2 * om))
    f = QFont()
    f.setBold(True)
    f.setPixelSize(max(7, int(round(px * 0.5))))
    p.setFont(f)
    br = QFontMetrics(f).tightBoundingRect(letter)
    bx = (px - br.width()) / 2.0 - br.left()
    by = (px - br.height()) / 2.0 - br.top()
    p.drawText(QPointF(bx, by), letter)
    p.end()
    return pm


def _fetch_pixmap(url: str, max_w: int):
    """Best-effort fetch of a remote image -> QPixmap scaled to max_w. Short
    timeout; returns None on any failure (so the What's new dialog still works
    without an image). Called only when a release sets image_url."""
    try:
        if url.lower().startswith(("http://", "https://")):
            import urllib.request

            req = urllib.request.Request(url, headers={"User-Agent": "Segue"})
            with urllib.request.urlopen(req, timeout=4) as r:
                data = r.read()
            pm = QPixmap()
            pm.loadFromData(data)
        else:
            pm = QPixmap(url)
        if pm.isNull():
            return None
        if pm.width() > max_w:
            pm = pm.scaledToWidth(int(max_w), Qt.SmoothTransformation)
        return pm
    except Exception:
        return None


def bundled_whatsnew_version() -> str:
    """Version of the bundled What's-new CONTENT (assets/whatsnew.json). Drives the
    post-update popup, decoupled from the app VERSION: a silent patch keeps the same
    content version (no re-pop), a notable release bumps it (shows). '' if absent."""
    import json

    try:
        with open(os.path.join(_ASSETS, "whatsnew.json"), encoding="utf-8") as f:
            return str(json.load(f).get("version", "")).strip()
    except Exception:
        return ""


def _theme_note_html(html: str) -> str:
    """Release-note markup bakes white emphasis (color:#ffffff) for dark mode.
    Re-point hardcoded white to the theme's primary text so titles read in light
    mode too (dark theme's text is ~white, so it looks unchanged there)."""
    import re

    return re.sub(
        "color:\\s*#?(?:ffffff|fff|white)\\b",
        f"color:{_c('text')}",
        html,
        flags=re.IGNORECASE,
    )


def _localize_inline_images(html: str) -> str:
    """Inline every <img> in What's-new notes as a base64 data URI.

    Two reasons: (1) QLabel rich text never downloads remote images, so hosted
    https sources must be fetched ourselves; (2) Qt's rich-text pixmap cache
    COLLIDES on same-sized images loaded from different file paths - two 380px
    screenshots rendered as the same image (verified with an isolated probe).
    Data URIs are immune to both. Downloads cache to temp by URL hash so
    re-opening the dialog is instant; a failed fetch drops just that image."""
    import re, io, hashlib, tempfile, urllib.request, base64
    from PIL import Image

    def repl(m):
        tag, src = m.group(0), m.group("src")
        if src.lower().startswith("data:"):
            return tag
        wm = re.search("width='(\\d+)'", tag)
        w = int(wm.group(1)) if wm else None
        try:
            if src.lower().startswith(("http://", "https://")):
                path = os.path.join(
                    tempfile.gettempdir(),
                    "segue_wn_" + hashlib.md5(src.encode()).hexdigest() + ".png",
                )
                if not os.path.exists(path):
                    req = urllib.request.Request(src, headers={"User-Agent": "Segue"})
                    with urllib.request.urlopen(req, timeout=6) as r:
                        data = r.read()
                    im = Image.open(io.BytesIO(data)).convert("RGBA")
                    bbox = im.getbbox()
                    if bbox:
                        im = im.crop(bbox)
                    if w and im.width != w:
                        im = im.resize(
                            (w, max(1, round(im.height * w / im.width))), Image.LANCZOS
                        )
                    im.save(path)
                mime = "image/png"
            else:
                path = src
                if w:
                    im = Image.open(path)
                    if im.width != w:
                        im = im.convert("RGBA").resize(
                            (w, max(1, round(im.height * w / im.width))), Image.LANCZOS
                        )
                        buf = io.BytesIO()
                        im.save(buf, "PNG")
                        b = base64.b64encode(buf.getvalue()).decode()
                        return f"<img src='data:image/png;base64,{b}'>"
                mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
            with open(path, "rb") as f:
                b = base64.b64encode(f.read()).decode()
            return f"<img src='data:{mime};base64,{b}'>"
        except Exception:
            return ""

    return re.sub("<img[^>]*src='(?P<src>[^']+)'[^>]*>", repl, html)


def _contrast_text(hex_color: str) -> str:
    """Dark or light text, whichever reads on the given background hex."""
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join((c * 2 for c in h))
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        if lum > 0.55:
            return "#1f1f1e"
        return "#f0f0f0"
    except Exception:
        return "#1f1f1e"


def _combo_pixmap(code: str, px: int, color: str = "#ffffff", device: str = None):
    """Composite a controller combo ("L1+square", "btn:4+btn:2") into one pixmap:
    each part as its drawn face glyph (cross/circle/square/triangle, same ring as
    a single bind) or its text label, separated by " + ". Returns None for a
    non-combo or key code so callers fall back to single-bind rendering. This is
    why a combo's face buttons read at full size instead of as a tiny Unicode
    glyph from the text path."""
    if not code or "+" not in code or code.startswith("key:"):
        return None
    from PySide6.QtGui import QPixmap, QPainter, QColor, QFontMetrics
    from PySide6.QtCore import Qt, QRectF

    parts = [p for p in code.split("+") if p]
    if len(parts) < 2:
        return None
    font = _ui_font(int(round(px * 0.62)), QFont.Bold)
    fm = QFontMetrics(font)
    sep = "  +  "
    sep_w = fm.horizontalAdvance(sep)
    segs = []
    for p in parts:
        face = _ps_face_pixmap(p, px, color)
        if face is None and device == "xbox" and p.startswith("btn:"):
            try:
                _n = int(p[4:])
                if _n in _XBOX_FACE:
                    face = _xbox_face_pixmap(_XBOX_FACE[_n], px, color)
            except ValueError:
                pass
        if face is not None:
            segs.append(("pm", face, face.width(), face.height()))
            continue
        t = _pretty_code(p, device)
        segs.append(("txt", t, fm.horizontalAdvance(t), px))
    total = max(1, sum((w for _, _, w, _ in segs)) + sep_w * (len(segs) - 1))
    pm = QPixmap(total, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    p.setFont(font)
    p.setPen(QColor(color))
    x = 0.0
    for i, (kind, payload, w, h) in enumerate(segs):
        if i > 0:
            p.drawText(QRectF(x, 0, sep_w, px), Qt.AlignCenter, sep)
            x += sep_w
        if kind == "pm":
            p.drawPixmap(int(round(x)), int(round((px - h) / 2)), payload)
        else:
            p.drawText(QRectF(x, 0, w, px), Qt.AlignVCenter | Qt.AlignLeft, payload)
        x += w
    p.end()
    return pm


def _set_bind_visual(
    w, code, fallback: str = "", px: int = 22, suffix: str = "", device: str = None
):
    """Render a bind on a keycap button or a QLabel: a drawn icon for the four
    DualSense face buttons (uniform size + ring) and composited combos, plain
    text for everything else. Falls back to `fallback` for an empty code.
    `suffix` rides inside the cap after the bind name, e.g. "(hold)" on the Open
    Segue row."""
    from PySide6.QtGui import QIcon, QPixmap

    try:
        pm = _combo_pixmap(code, px, _c("text"), device)
    except Exception:
        pm = None
    if pm is None and device == "xbox" and code and code.startswith("btn:"):
        try:
            _n = int(code[4:])
            if _n in _XBOX_FACE:
                pm = _xbox_face_pixmap(_XBOX_FACE[_n], px, _c("text"))
        except ValueError:
            pm = None
    if pm is None:
        pm = _ps_face_pixmap(code, px, _c("text"))
    is_btn = isinstance(w, QAbstractButton)
    if pm is not None:
        if is_btn:
            w.setText(suffix)
            w.setIcon(QIcon(pm))
            w.setIconSize(pm.size())
            return None
        w.setText(suffix)
        w.setPixmap(pm)
        return None
    txt = _pretty_code(code, device) if code else (fallback or "Unbound")
    if suffix:
        txt = f"{txt} {suffix}"
    if is_btn:
        w.setIcon(QIcon())
        w.setText(txt)
        return None
    w.setPixmap(QPixmap())
    w.setText(txt)


def _vk_label(vk: int) -> str:
    """Human label for a single Windows virtual-key code."""
    named = {
        8: "Backspace",
        9: "Tab",
        13: "Enter",
        16: "Shift",
        17: "Ctrl",
        18: "Alt",
        19: "Pause",
        20: "Caps Lock",
        27: "Esc",
        32: "Space",
        33: "Page Up",
        34: "Page Down",
        35: "End",
        36: "Home",
        37: "Left",
        38: "Up",
        39: "Right",
        40: "Down",
        45: "Insert",
        46: "Delete",
        106: "Numpad *",
        107: "Numpad +",
        109: "Numpad -",
        110: "Numpad .",
        111: "Numpad /",
    }
    if vk in named:
        return named[vk]
    if 96 <= vk <= 105:
        return f"Numpad {vk - 96}"
    if 112 <= vk <= 123:
        return f"F{vk - 111}"
    try:
        import ctypes

        ch = ctypes.windll.user32.MapVirtualKeyW(int(vk), 2) & 65535
        if ch >= 32 and chr(ch).strip():
            return chr(ch).upper()
    except Exception:
        pass
    if 48 <= vk <= 90:
        return chr(vk)
    return f"Key {vk}"


def _build_qss() -> str:
    """Stylesheet with every px scaled by _s() for live UI scaling."""
    hw = _s(18)
    bw = max(1, _s(2))
    gh = _s(6)
    hrad = (hw + 2 * bw) // 2
    hmar = (hw + 2 * bw - gh) // 2
    chev = _chevron_qss_path(13)
    chk = _check_qss_path(14, _c("text"))
    cbchk = _check_qss_path(14, _c("emph_text"))
    downchev = _down_chevron_qss_path(12)
    _bb = f"1px solid {_c('border')}" if _active_theme() == "light" else "none"
    _tog_act_bd = (
        f"1px solid {_c('emph_fill')}" if _active_theme() == "light" else "none"
    )
    _pwr_act_bd = f"1px solid {_ACCENT}" if _active_theme() == "light" else "none"
    _tab_act_bd = f"1px solid {_c('panel')}" if _active_theme() == "light" else "none"
    return f"""
* {{ color: {_c("text")}; }}
QLabel#hint {{ color: {_c("text_hint")}; }}
QLabel:disabled, QLabel#hint:disabled {{ color: {_c("text_disabled")}; }}   /* greyed when row off */
QCheckBox::indicator {{ width: {_s(22)}px; height: {_s(22)}px; border-radius: {_s(6)}px;
    border: 1px solid {_c("border_hi")}; background: {_c("surface")}; }}
QCheckBox::indicator:checked {{ background: {_c("emph_fill")}; border: 1px solid {_c("emph_fill")};
    image: url("{cbchk}"); }}
QCheckBox:disabled {{ color: {_c("text_disabled")}; }}
QCheckBox::indicator:disabled {{ background: {_c("sunk")}; border: 1px solid {_c("border")}; }}
QCheckBox::indicator:checked:disabled {{ background: {_c("text_disabled")}; border: 1px solid {_c("text_disabled")}; }}
QSlider:horizontal {{ min-height: {_s(24)}px; }}
QSlider::groove:horizontal {{ height: {gh}px; background: {_c("border")}; border-radius: {gh // 2}px; }}
QSlider::sub-page:horizontal {{ background: {_c("emph_fill")}; border-radius: {gh // 2}px; }}
QSlider::add-page:horizontal {{ background: {_c("border")}; border-radius: {gh // 2}px; }}
QSlider::handle:horizontal {{ width: {hw}px; height: {hw}px; margin: -{hmar}px 0;
    background: {_c("emph_fill")}; border: {bw}px solid {_c("panel")}; border-radius: {hrad}px; }}
/* Hover keeps a CONTRASTING outline (border_hi went white in high-contrast =
   same as the white handle/track -> no separation). emph_text is defined as the
   contrast to emph_fill, so the handle stays separated from the filled track. */
QSlider::handle:horizontal:hover {{ border-color: {_c("emph_text")}; }}
QSlider::handle:horizontal:pressed {{ background: {_c("emph_fill")}; }}
QSlider::groove:horizontal:disabled {{ background: {_c("surface")}; }}
QSlider::sub-page:horizontal:disabled {{ background: {_c("border_hi")}; }}
QSlider::handle:horizontal:disabled {{ background: {_c("text_disabled")}; border-color: {_c("panel")}; }}
QPushButton {{ background: {_c("surface")}; border: none; border-radius: {_s(8)}px;
    padding: {_s(7)}px {_s(12)}px; }}
QPushButton:hover {{ background: {_c("surface_hi")}; }}
QPushButton#togglebtn {{ background: {_c("surface")}; border: {_bb}; border-radius: {_s(8)}px;
    padding: {_s(9)}px {_s(10)}px; min-height: {_s(20)}px; }}
QPushButton#togglebtn:hover {{ background: {_c("surface_hi")}; }}
QPushButton#togglebtn[active="true"] {{ background: {_c("emph_fill")}; color: {_c("emph_text")}; border: {_tog_act_bd}; }}
QPushButton#togglebtn:disabled {{ color: {_c("text_disabled")}; }}
/* Skip-input pills (D-pad / Touchpad swipe) + pause Tap/Press: styled like the
   bind key-caps - outlined, not a solid fill. Active = orange outline + white
   text on a faint orange tint (matches keycap hover), so the chosen option
   reads as "engaged" the same way a bound cap does. 2px border on every state
   so toggling active doesn't shift the layout. */
QPushButton#skipbtn {{ background: {_c("deep")}; border: 2px solid {_c("border_hi")}; border-radius: {_s(8)}px;
    padding: {_s(7)}px {_s(14)}px; min-height: {_s(20)}px; font-weight: 600; color: {_c("text")}; }}
QPushButton#skipbtn:hover {{ border-color: {_ACCENT}; background: {_c("accent_tint")}; }}
QPushButton#skipbtn[active="true"] {{ background: {_c("accent_tint")}; border: 2px solid {_ACCENT}; color: {_c("text")}; }}
QPushButton#skipbtn[active="true"]:hover {{ border-color: {_c("accent_hi")}; }}
QPushButton#powerbtn {{ background: {_c("surface")}; border: {_bb}; border-radius: {_s(8)}px;
    padding: {_s(9)}px {_s(10)}px; min-height: {_s(20)}px; }}
QPushButton#powerbtn:hover {{ background: {_c("surface_hi")}; }}
QPushButton#powerbtn[active="true"] {{ background: {_ACCENT}; color: {_c("emph_text")}; border: {_pwr_act_bd}; }}
/* The 5 row buttons (media + tabs) share one height via min/max-height so they
   match exactly; the active tab is the only one made taller (to meet its panel). */
QPushButton#mediabtn {{ background: {_c("surface")}; border: {_bb}; border-radius: {_s(8)}px;
    padding: {_s(6)}px {_s(10)}px; min-height: {_s(32)}px; max-height: {_s(32)}px; }}
QPushButton#mediabtn:hover {{ background: {_c("surface_hi")}; }}
QPushButton#playbtn {{ background: {_c("btn_fill")}; border: {_bb}; border-radius: {_s(8)}px;
    padding: {_s(6)}px {_s(10)}px; min-height: {_s(32)}px; max-height: {_s(32)}px; }}
QPushButton#playbtn:hover {{ background: {_c("btn_fill_hi")}; }}
QPushButton#playbtn[playing="true"] {{ background: {_c("btn_dull")}; }}   /* duller while playing */
QPushButton#playbtn[playing="true"]:hover {{ background: {_c("btn_dull_hi")}; }}
QPushButton#tabbtn {{ background: {_c("surface")}; border: {_bb}; border-radius: {_s(8)}px;
    padding: {_s(6)}px {_s(10)}px; min-height: {_s(32)}px; max-height: {_s(32)}px; }}
QPushButton#tabbtn:hover {{ background: {_c("surface_hi")}; }}
QPushButton#tabbtn[dull="true"] {{ background: {_c("surface_dull")}; }}
QPushButton#tabbtn[dull="true"]:hover {{ background: {_c("surface_hi")}; }}
QPushButton#tabbtn[active="true"] {{ background: {_c("panel")}; border: {_tab_act_bd};
    /* fill-coloured (invisible) border keeps the SAME 1px box as the outlined
       rest tab so the icon doesn't jump on open; it still merges into its panel */
    /* same content height as inactive; the +7 to reach the panel is bottom padding
       so the icon stays put instead of recentering downward */
    min-height: {_s(32)}px; max-height: {_s(32)}px;
    padding: {_s(6)}px {_s(10)}px {_s(13)}px {_s(10)}px;
    border-top-left-radius: {_s(8)}px; border-top-right-radius: {_s(8)}px;
    border-bottom-left-radius: 0; border-bottom-right-radius: 0; }}
QPushButton#tabbtn[active="true"]:hover {{ background: {_c("panel")}; }}
QFrame#tabpanel {{ background: {_c("panel")}; border: none; border-radius: {_s(8)}px; }}
QFrame#tabpanelL {{ background: {_c("panel")}; border: none; border-radius: {_s(8)}px;
    border-top-left-radius: 0; }}   /* Mixer panel: sharp top-left (tab sits at the edge) */
QPushButton#advbtn {{ background: transparent; border: none; text-align: left;
    color: {_c("text_hint")}; padding: {_s(2)}px {_s(2)}px; }}
QPushButton#advbtn:hover {{ color: {_c("text")}; }}
QPushButton#bindsbtn::menu-indicator {{ image: none; width: 0; }}
QPushButton#devbtn {{ background: {_c("surface")}; border: 2px solid transparent;
    border-radius: {_s(6)}px; padding: {_s(5)}px {_s(8)}px; }}
QPushButton#devbtn:hover {{ background: {_c("surface_hi")}; }}
QPushButton#devbtn:checked {{ background: {_c("surface")}; border: 2px solid {_ACCENT}; }}
QToolButton#devcard {{ background: {_c("surface")}; border: 2px solid transparent;
    border-radius: {_s(10)}px; color: {_c("text")}; padding: {_s(10)}px; }}
QToolButton#devcard:hover {{ background: {_c("surface_hi")}; border: 2px solid {_ACCENT}; }}
/* Save uses emph_fill (dark slab in light, white in dark) - btn_fill is the
   BRIGHT white play pill, which on the light dialog was white-on-near-white and
   vanished (worse on hover). emph keeps the primary action high-contrast in both
   themes. 1px transparent border = same box as the disabled border (no shift).
   Disabled gets a visible surface fill + border so the button still reads as a
   button when greyed (sunk was invisible against the dialog). */
QPushButton#savebtn {{ background: {_c("emph_fill")}; color: {_c("emph_text")};
    border: 1px solid transparent; border-radius: {_s(8)}px;
    padding: {_s(9)}px {_s(12)}px; font-weight: 700; }}
QPushButton#savebtn:hover {{ background: {_c("emph_fill_hi")}; }}
QPushButton#savebtn:disabled {{ background: {_c("surface")}; color: {_c("text_disabled")};
    border: 1px solid {_c("border")}; }}
QFrame#card {{ background: {_c("surface")}; border: {_bb}; border-radius: {_s(8)}px; }}
QFrame#vline {{ background: {_c("border")}; border: none; }}
QLabel#nptitle {{ color: {_c("text")}; }}
QWidget#titlebar {{ background: {_c("titlebar")}; }}
/* Titlebar buttons: square hover fill (border-radius 0) like a native window
   caption, NOT the global rounded-button look they were inheriting from the
   generic QPushButton rule. The window's own rounded corner is DWM-clipped,
   so the close button's top-right follows it automatically. */
QPushButton#menubtn {{ background: transparent; border: none; border-radius: 0; }}
QPushButton#menubtn:hover {{ background: {_c("surface_hi")}; }}
QPushButton#menubtn::menu-indicator {{ image: none; width: 0; }}
/* Version + refresh = one rounded, contained hover unit (not a tall square). */
QPushButton#verbar {{ background: transparent; border: none; border-radius: 7px;
                      color: {_c("verbar_text")}; padding: 3px 8px; text-align: left; }}
QPushButton#verbar:hover {{ background: {_c("surface_hi")}; color: {_c("verbar_text_hi")}; }}
/* Flat icon-only undo button (overlay-size reset): no box, subtle hover. */
QPushButton#undobtn {{ background: transparent; border: none; border-radius: {_s(6)}px;
                       padding: {_s(4)}px; }}
QPushButton#undobtn:hover {{ background: {_c("surface_hi")}; }}
QPushButton#capbtn, QPushButton#capclose {{ background: transparent; border: none; border-radius: 0; }}
QPushButton#capbtn:hover {{ background: {_c("surface_hi")}; }}
/* Close hover is the universal Windows close-red in EVERY theme (the contrast
   theme's danger is a light salmon that read weak as a close button); the X
   glyph flips to white on hover via enter/leaveEvent. */
QPushButton#capclose:hover {{ background: #c42b1c; }}
/* Tooltips: without an explicit rule Qt falls back to the OS tooltip palette
   (light on Win10/11), and the app's light text then renders white-on-white /
   unreadable. Pin a themed tooltip everywhere so it always matches. */
QToolTip {{ background-color: {_c("panel")}; color: {_c("text")}; border: 1px solid {_c("border")};
    border-radius: {_s(5)}px; padding: {_s(4)}px {_s(7)}px; }}
/* No QSS border/border-radius on the menu FRAME: the native Win11 style rounds
   the menu window itself, and a QSS rounded rect on top sat at a different
   radius -> a second, inset rounded border ('double corner'). Just recolour the
   fill; the native frame is the single rounded corner. */
QMenu {{ background: {_c("panel")}; border: none; padding: {_s(6)}px; }}
QMenu::item {{ padding: {_s(7)}px {_s(22)}px {_s(7)}px {_s(10)}px; border-radius: {_s(6)}px; }}
/* Icons hug the popup's left edge by default; pad them inward so they sit
   balanced inside the rounded item highlight (Help submenu glyphs). */
QMenu::icon {{ padding-left: {_s(10)}px; }}
QMenu::item:!selected {{ background: transparent; }}
QMenu::item:selected {{ background: {_c("surface_hi")}; }}
/* QWidgetAction rows (Uninstall / Quit) with the icon pinned right - replicate
   the item hover highlight since they aren't native QMenu::items. */
QWidget#menurowR {{ background: transparent; border-radius: {_s(6)}px; }}
QWidget#menurowR:hover {{ background: {_c("surface_hi")}; }}
QLabel#menurowtext {{ color: {_c("text")}; background: transparent; }}
/* Update banner: slim orange bar under the titlebar. Hidden until a new
   release lands, then shown with a Get-it button + small × dismiss. */
QWidget#updatebanner {{ background: {_ACCENT}; }}
QLabel#updatebannertext {{ color: #1f1f1e; padding-left: {_s(2)}px; }}
QPushButton#updatebannerbtn {{ background: #1f1f1e; color: {_ACCENT};
    border: none; border-radius: {_s(6)}px; padding: {_s(4)}px {_s(12)}px;
    min-height: 0; }}
QPushButton#updatebannerbtn:hover {{ background: #2b2b29; }}
QPushButton#updatebannerclose {{ background: transparent; color: #1f1f1e;
    border: none; padding: 0; }}
QPushButton#updatebannerclose:hover {{ background: rgba(0,0,0,0.12);
    border-radius: {_s(12)}px; }}
QPushButton#updatebannerlink {{ background: transparent; color: #1f1f1e;
    border: none; padding: 0 {_s(6)}px; font-weight: 600; text-decoration: underline; }}
QPushButton#updatebannerlink:hover {{ color: #000000; }}
QPushButton#resetbtn {{ background: {_c("surface")}; border: 1px solid {_c("border")}; color: {_c("text_dim")};
    border-radius: {_s(6)}px; padding: {_s(3)}px {_s(10)}px; min-height: 0; }}
QPushButton#resetbtn:hover {{ background: {_c("surface_hi")}; border-color: {_c("border_hi")}; color: {_c("text")}; }}
QPushButton#srcbtn {{ background: transparent; border: none; color: {_c("text_dim")};
    padding: {_s(6)}px {_s(8)}px; }}
QPushButton#srcbtn:hover {{ background: {_c("surface_hi")}; border-radius: {_s(6)}px; }}
/* Source split: the pill bg is painted by the container (_paint_src_box) so the
   inner edges at the gap stay SHARP (Qt's per-corner QSS radius rounds all four).
   The segment buttons are transparent click/icon targets. */
QFrame#srcbox {{ background: transparent; }}
QPushButton#srcseg {{ background: transparent; border: none; color: {_c("text_dim")}; }}
/* Custom icon-popup (source picker etc.) - replaces QMenu so the icons
   can scale freely. Rounded frame, hover-lit rows, left-aligned. */
QFrame#iconpopup {{ background: {_c("panel")}; border: 1px solid {_c("border")};
    border-radius: {_s(8)}px; }}
/* 'Tip' callout card in the Setup tab - tinted box, accent left edge. */
QFrame#tipcard {{ background: {_c("accent_tint")}; border: 1px solid {_c("border")};
    border-left: {_s(3)}px solid {_ACCENT}; border-radius: {_s(8)}px; }}
QPushButton#popupitem {{ background: transparent; border: none; color: {_c("text")};
    text-align: left; padding: {_s(8)}px {_s(12)}px; border-radius: {_s(6)}px; }}
QPushButton#popupitem:hover {{ background: {_c("surface_hi")}; }}
/* Per-row delete button in the presets popup. Trash icon stays dim until
   hovered, then lights red so deletion reads as a deliberate action. */
QPushButton#presetdel {{ background: transparent; border: none;
    border-radius: {_s(6)}px; padding: {_s(8)}px {_s(6)}px; }}
QPushButton#presetdel:hover {{ background: {_c("danger_tint")}; }}
QComboBox {{ background: {_c("surface")}; color: {_c("text")}; border: 1px solid {_c("border")};
    border-radius: {_s(4)}px; padding: {_s(4)}px {_s(8)}px; }}
QComboBox:hover {{ background: {_c("surface_hi")}; }}
/* Disabled combo (e.g. mic picker when Speech recognition / Include self is off):
   without this it keeps full colour and looks active. Dim it like the rest. */
QComboBox:disabled {{ background: {_c("sunk")}; color: {_c("text_disabled")}; border-color: {_c("border")}; }}
QComboBox::drop-down {{ border: none; width: {_s(18)}px; }}
QComboBox::down-arrow {{ image: url("{downchev}"); width: {_s(12)}px; height: {_s(12)}px; }}
/* Subtle grey row highlight (selection-background-color), NOT an accent-orange
   ::item bleed - the orange + taller item padding read heavy in the mic picker
   ("we had it good"). Back to the shipped subtle look. */
QComboBox QAbstractItemView {{ background: {_c("panel")}; color: {_c("text")};
    border: 1px solid {_c("border")}; outline: none;
    selection-background-color: {_c("surface_hi")}; padding: {_s(4)}px; }}
QMenu::separator {{ height: 1px; background: {_c("border")}; margin: {_s(5)}px {_s(8)}px; }}
/* Submenu chevron: a painted PNG (Qt's built-in is ~7px + invisible on dark)
   set as the right-arrow IMAGE so Qt right-aligns it natively at the menu's
   right edge, sized to the menu font. Replaces the old "  >" text in titles. */
QMenu::right-arrow {{ image: url("{chev}"); width: {_s(13)}px; height: {_s(13)}px;
    subcontrol-position: center right; right: {_s(8)}px; }}
/* Checked-item tick (View / scale menu): bigger + theme-coloured, nudged in
   toward the label so it isn't stranded at the far left. */
QMenu::indicator {{ width: {_s(14)}px; height: {_s(14)}px; left: {_s(6)}px; }}
QMenu::indicator:checked {{ image: url("{chk}"); }}
QMenu::indicator:non-exclusive:checked {{ image: url("{chk}"); }}
QMenu::indicator:exclusive:checked {{ image: url("{chk}"); }}
QMenu::indicator:unchecked {{ image: none; }}
QMessageBox {{ background: {_c("sunk")}; }}
QMessageBox QLabel {{ color: {_c("text")}; }}
QInputDialog, QDialog {{ background: {_c("sunk")}; }}
QInputDialog QLabel, QDialog QLabel {{ color: {_c("text")}; }}
QLineEdit {{ background: {_c("surface")}; color: {_c("text")}; border: 1px solid {_c("border")};
    border-radius: {_s(6)}px; padding: {_s(5)}px {_s(8)}px; selection-background-color: {_c("border_hi")}; }}
/* Generic list (the "Pick app" picker). WITHOUT an explicit rule an unstyled
   QListWidget falls back to the SYSTEM palette - so on a Windows-dark-mode
   machine the list body rendered dark even in Segue's light theme. Theme it. */
QListWidget {{ background: {_c("surface")}; color: {_c("text")};
    border: 1px solid {_c("border")}; border-radius: {_s(6)}px; outline: none; padding: {_s(3)}px; }}
QListWidget::item {{ padding: {_s(7)}px {_s(9)}px; border-radius: {_s(4)}px; }}
QListWidget::item:hover {{ background: {_c("surface_hi")}; }}
QListWidget::item:selected {{ background: {_ACCENT}; color: {_c("emph_text")}; }}
QListWidget#helpnav {{ background: {_c("panel")}; border: none; border-radius: {_s(8)}px;
    padding: {_s(6)}px; outline: none; }}
QListWidget#helpnav::item {{ color: {_c("text_dim")}; padding: {_s(8)}px {_s(10)}px;
    border-radius: {_s(6)}px; margin-bottom: {_s(2)}px; }}
QListWidget#helpnav::item:hover {{ background: {_c("surface_hi")}; color: {_c("text")}; }}
QListWidget#helpnav::item:selected {{ background: {_ACCENT}; color: {_c("emph_text")}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
/* Thin track LINE + a rounded HANDLE over it. Page-margins squeeze the
   add/sub-page into a ~2px centred line; the handle's smaller margins make it an
   8px rounded bar (radius 4 = full pill, still thin). Hover brightens. Fixed px
   (not _s): _s rounding kept flattening the handle's corners. Verified offscreen. */
QScrollBar:vertical {{ background: transparent; width: 16px; margin: 5px 0; }}
QScrollBar::handle:vertical {{ background: {_c("scrollbar")}; border-radius: 4px;
    min-height: 40px; margin: 0 4px; }}
QScrollBar::handle:vertical:hover {{ background: {_c("scrollbar_hi")}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; width: 0; background: none; border: none; }}
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{ width: 0; height: 0; background: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: {_c("border")}; margin: 0 7px; border-radius: 2px; }}
"""


