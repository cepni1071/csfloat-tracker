import threading
import time
import hashlib
import io
import os
import tkinter as tk
from pathlib import Path

import requests
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

import database
import api
import notifier
import config

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DARK_BG     = "#0d1117"
CARD_BG     = "#161b22"
PANEL_BG    = "#13181f"
ACCENT      = "#ff8c00"
ACCENT2     = "#4da6ff"
TEXT_DIM    = "#8b949e"
TEXT_BRIGHT = "#e6edf3"
GREEN       = "#3fb950"
RED         = "#f85149"
BORDER      = "#30363d"

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

WEAR_ZONES = [
    (0.00, 0.07, "#3fb950", "FN"),
    (0.07, 0.15, "#58d68d", "MW"),
    (0.15, 0.38, "#f4d03f", "FT"),
    (0.38, 0.45, "#e67e22", "WW"),
    (0.45, 1.00, "#e74c3c", "BS"),
]

# ── Float Range Slider ────────────────────────────────────────────────────────

class FloatRangeSlider(ctk.CTkFrame):
    def __init__(self, parent, on_change=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_change = on_change
        self.min_val = 0.0
        self.max_val = 1.0
        self._dragging = None

        self._canvas = tk.Canvas(self, height=54, bg=PANEL_BG, highlightthickness=0)
        self._canvas.pack(fill="x", padx=2)
        self._canvas.bind("<ButtonPress-1>",  self._press)
        self._canvas.bind("<B1-Motion>",      self._drag)
        self._canvas.bind("<ButtonRelease-1>",self._release)
        self._canvas.bind("<Configure>",      lambda e: self._render())

    def _bounds(self):
        w = self._canvas.winfo_width()
        return 18, max(20, w - 18)

    def _to_x(self, val):
        x0, x1 = self._bounds()
        return x0 + (x1 - x0) * val

    def _to_val(self, x):
        x0, x1 = self._bounds()
        return max(0.0, min(1.0, (x - x0) / max(1, x1 - x0)))

    def _render(self):
        c = self._canvas
        w = c.winfo_width()
        if w < 20:
            return
        c.delete("all")
        ty = 26
        x0, x1 = self._bounds()

        # Wear zone renkli arka plan
        for zmin, zmax, color, _ in WEAR_ZONES:
            zx0 = x0 + (x1 - x0) * zmin
            zx1 = x0 + (x1 - x0) * zmax
            c.create_rectangle(zx0, ty - 3, zx1, ty + 3, fill=color, outline="")

        # Aktif aralık - turuncu üstü
        mx0 = self._to_x(self.min_val)
        mx1 = self._to_x(self.max_val)
        c.create_rectangle(mx0, ty - 4, mx1, ty + 4, fill=ACCENT, outline="")

        # Zone sınır çizgileri
        for val in [0.07, 0.15, 0.38, 0.45]:
            tx = self._to_x(val)
            c.create_line(tx, ty - 10, tx, ty + 10, fill="#555", width=1)

        # Min handle
        r = 9
        c.create_oval(mx0-r, ty-r, mx0+r, ty+r, fill=CARD_BG, outline=ACCENT, width=2)
        c.create_text(mx0, ty - 18, text=f"{self.min_val:.3f}",
                      fill=TEXT_BRIGHT, font=("Arial", 9, "bold"))

        # Max handle
        c.create_oval(mx1-r, ty-r, mx1+r, ty+r, fill=CARD_BG, outline=ACCENT, width=2)
        c.create_text(mx1, ty + 18, text=f"{self.max_val:.3f}",
                      fill=TEXT_BRIGHT, font=("Arial", 9, "bold"))

    def _press(self, event):
        mx0 = self._to_x(self.min_val)
        mx1 = self._to_x(self.max_val)
        if abs(event.x - mx0) <= abs(event.x - mx1):
            self._dragging = "min"
        else:
            self._dragging = "max"

    def _drag(self, event):
        if not self._dragging:
            return
        val = self._to_val(event.x)
        if self._dragging == "min":
            self.min_val = min(val, self.max_val - 0.005)
        else:
            self.max_val = max(val, self.min_val + 0.005)
        self._render()
        if self.on_change:
            self.on_change(self.min_val, self.max_val)

    def _release(self, event):
        self._dragging = None

    def get(self):
        return round(self.min_val, 4), round(self.max_val, 4)

    def set(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val
        self._render()


# ── Image cache ───────────────────────────────────────────────────────────────

_img_cache: dict[str, ctk.CTkImage | None] = {}

def load_skin_image(image_url: str, size=(72, 54)) -> ctk.CTkImage | None:
    if not image_url:
        return None
    key = hashlib.md5(image_url.encode()).hexdigest()
    if key in _img_cache:
        return _img_cache[key]
    cache_path = CACHE_DIR / f"{key}.png"
    if not cache_path.exists():
        try:
            r = requests.get(image_url, timeout=6)
            if r.status_code == 200:
                cache_path.write_bytes(r.content)
        except Exception:
            _img_cache[key] = None
            return None
    try:
        img = Image.open(cache_path).convert("RGBA")
        result = ctk.CTkImage(img, size=size)
        _img_cache[key] = result
        return result
    except Exception:
        _img_cache[key] = None
        return None


# ── Ana uygulama ──────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CSFloat Tracker")
        self.geometry("1060x700")
        self.minsize(960, 600)
        self.configure(fg_color=DARK_BG)

        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            try:
                from PIL import ImageTk
                _ico = ImageTk.PhotoImage(Image.open(icon_path).resize((64, 64)))
                self.iconphoto(True, _ico)
                self._ico = _ico
            except Exception:
                pass

        self._dropdown = None
        self._pending_image_url = ""   # autocomplete'ten seçilen skin'in image_url'i
        self._float_min = 0.0
        self._float_max = 1.0

        database.init_db()
        self._build_ui()
        self._refresh_list()
        self._start_checker()

        # Pencereyi öne getir
        self.after(200, self._bring_to_front)

    def _bring_to_front(self):
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            try:
                ctkimg = ctk.CTkImage(Image.open(icon_path), size=(34, 34))
                ctk.CTkLabel(header, image=ctkimg, text="").pack(side="left", padx=(16, 6), pady=12)
            except Exception:
                pass

        ctk.CTkLabel(header, text="CSFloat Tracker",
                     font=("Arial", 21, "bold"), text_color=TEXT_BRIGHT).pack(side="left", pady=12)
        ctk.CTkFrame(header, width=1, fg_color=BORDER).pack(side="left", fill="y", padx=14, pady=10)

        self.status_label = ctk.CTkLabel(header, text="● Hazır",
                                         font=("Arial", 12), text_color=GREEN)
        self.status_label.pack(side="left")

        ctk.CTkButton(header, text="🔄  Güncelle", command=self._manual_check,
                      fg_color="#21262d", hover_color="#30363d", text_color=TEXT_BRIGHT,
                      border_width=1, border_color=BORDER, font=("Arial", 13),
                      height=34, width=130, corner_radius=8).pack(side="right", padx=16, pady=12)

        # Gövde
        body = ctk.CTkFrame(self, fg_color=DARK_BG)
        body.pack(fill="both", expand=True)

        # Sol panel
        left = ctk.CTkFrame(body, width=300, fg_color=PANEL_BG,
                            border_width=1, border_color=BORDER, corner_radius=12)
        left.pack(side="left", fill="y", padx=(12, 6), pady=12)
        left.pack_propagate(False)

        self._build_left(left)

        # Sağ panel
        right = ctk.CTkFrame(body, fg_color=PANEL_BG,
                             border_width=1, border_color=BORDER, corner_radius=12)
        right.pack(side="right", fill="both", expand=True, padx=(6, 12), pady=12)

        rh = ctk.CTkFrame(right, fg_color="transparent")
        rh.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(rh, text="Takip Listesi",
                     font=("Arial", 15, "bold"), text_color=TEXT_BRIGHT).pack(side="left")
        self.count_label = ctk.CTkLabel(rh, text="0 skin",
                                        font=("Arial", 12), text_color=TEXT_DIM)
        self.count_label.pack(side="right")

        ctk.CTkFrame(right, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 8))

        self.scroll_frame = ctk.CTkScrollableFrame(right, fg_color="transparent",
                                                   scrollbar_button_color=BORDER)
        self.scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _build_left(self, parent):
        # Başlık
        ctk.CTkLabel(parent, text="Skin Ekle", font=("Arial", 15, "bold"),
                     text_color=TEXT_BRIGHT).pack(anchor="w", padx=18, pady=(18, 2))

        # Kategoriler
        CATS = [
            ("🔪 Bıçaklar", "★"), ("🧤 Eldivenler", "★ Sport Gloves"),
            ("AK-47", "AK-47"), ("AWP", "AWP"),
            ("M4A4", "M4A4"), ("M4A1-S", "M4A1-S"),
            ("Deagle", "Desert Eagle"), ("USP-S", "USP-S"),
            ("Glock-18", "Glock-18"), ("SSG 08", "SSG 08"),
        ]
        cat_scroll = ctk.CTkScrollableFrame(parent, height=44, fg_color="transparent",
                                            orientation="horizontal",
                                            scrollbar_button_color=BORDER)
        cat_scroll.pack(fill="x", padx=14, pady=(6, 4))
        for label, query in CATS:
            ctk.CTkButton(cat_scroll, text=label, width=95, height=28,
                          fg_color="#21262d", hover_color="#30363d",
                          text_color=TEXT_DIM, font=("Arial", 11),
                          border_width=1, border_color=BORDER, corner_radius=20,
                          command=lambda q=query: self._select_category(q)
                          ).pack(side="left", padx=3)

        # Arama kutusu + arama butonu
        search_row = ctk.CTkFrame(parent, fg_color="transparent")
        search_row.pack(fill="x", padx=18, pady=(4, 4))

        self.entry_name = ctk.CTkEntry(
            search_row, placeholder_text="Skin ara...",
            height=38, fg_color="#21262d", border_color=BORDER,
            border_width=1, text_color=TEXT_BRIGHT, font=("Arial", 13), corner_radius=8)
        self.entry_name.pack(side="left", fill="x", expand=True)
        self.entry_name.bind("<Return>", lambda e: self._do_search())
        self.entry_name.bind("<FocusOut>", lambda e: self.after(200, self._hide_dropdown))

        self.search_btn = ctk.CTkButton(
            search_row, text="Ara", command=self._do_search,
            width=56, height=38, fg_color=ACCENT, hover_color="#e07b00",
            text_color="white", font=("Arial", 13, "bold"), corner_radius=8)
        self.search_btn.pack(side="left", padx=(8, 0))

        # Float slider bölümü
        ctk.CTkLabel(parent, text="Float Aralığı", font=("Arial", 12, "bold"),
                     text_color=TEXT_BRIGHT).pack(anchor="w", padx=18, pady=(10, 0))

        # Wear ismi göstergesi
        self.wear_label = ctk.CTkLabel(parent, text="Tümü  (0.000 – 1.000)",
                                       font=("Arial", 11), text_color=TEXT_DIM)
        self.wear_label.pack(anchor="w", padx=18)

        self.float_slider = FloatRangeSlider(parent, on_change=self._on_float_change)
        self.float_slider.pack(fill="x", padx=18, pady=(4, 6))

        # Hedef fiyat
        self.entry_target = ctk.CTkEntry(
            parent, placeholder_text="Hedef fiyat $ (isteğe bağlı)",
            width=262, height=38, fg_color="#21262d", border_color=BORDER,
            border_width=1, text_color=TEXT_BRIGHT, font=("Arial", 13), corner_radius=8)
        self.entry_target.pack(padx=18, pady=(0, 8))

        ctk.CTkButton(parent, text="+ Listeye Ekle", command=self._add_skin,
                      width=262, height=40, fg_color=ACCENT, hover_color="#e07b00",
                      text_color="white", font=("Arial", 14, "bold"),
                      corner_radius=8).pack(padx=18, pady=(0, 14))

        ctk.CTkFrame(parent, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 12))

        # İstatistikler
        self.stat_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.stat_frame.pack(fill="x", padx=18)
        self._build_stats()

    def _build_stats(self):
        for w in self.stat_frame.winfo_children():
            w.destroy()
        skins = database.get_all_skins()
        total = len(skins)
        total_val = sum(s[3] for s in skins if s[3])
        for lbl, val in [("Toplam Skin", str(total)),
                         ("Toplam Değer", f"${total_val:.2f}" if total_val else "—")]:
            box = ctk.CTkFrame(self.stat_frame, fg_color="#21262d",
                               corner_radius=8, border_width=1, border_color=BORDER)
            box.pack(fill="x", pady=3)
            ctk.CTkLabel(box, text=lbl, font=("Arial", 11),
                         text_color=TEXT_DIM).pack(anchor="w", padx=12, pady=(7, 0))
            ctk.CTkLabel(box, text=val, font=("Arial", 17, "bold"),
                         text_color=ACCENT2).pack(anchor="w", padx=12, pady=(0, 7))

    # ── Float slider ──────────────────────────────────────────────────────────

    def _on_float_change(self, mn, mx):
        self._float_min = mn
        self._float_max = mx
        # Wear ismi
        wear = self._wear_name(mn, mx)
        self.wear_label.configure(text=f"{wear}  ({mn:.3f} – {mx:.3f})")

    def _wear_name(self, mn, mx):
        if mn == 0.0 and mx == 1.0:
            return "Tümü"
        names = []
        for zmin, zmax, _, label in WEAR_ZONES:
            if mn < zmax and mx > zmin:
                names.append(label)
        return " / ".join(names) if names else "Özel"

    # ── Kategori & Autocomplete ───────────────────────────────────────────────

    def _select_category(self, query):
        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, query)
        self._fetch_suggestions(query)

    def _do_search(self):
        query = self.entry_name.get().strip()
        if len(query) < 2:
            self._hide_dropdown()
            return
        self._fetch_suggestions(query)

    def _fetch_suggestions(self, query):
        self.status_label.configure(text="● Aranıyor...", text_color=ACCENT)
        self._search_id = getattr(self, "_search_id", 0) + 1
        my_id = self._search_id
        self._show_loading_dropdown()
        threading.Thread(target=self._fetch_and_sort, args=(query, my_id), daemon=True).start()

    def _fetch_and_sort(self, query, search_id):
        try:
            skins = api.search_all_skins(query)
        except Exception as e:
            print(f"search hata: {e}")
            skins = []

        if search_id != self._search_id:
            return

        if not skins:
            self.after(0, self._hide_dropdown)
            self.after(0, lambda: self.status_label.configure(text="● Hazır", text_color=GREEN))
            return

        # Not: CSFloat fiyatları burada ÇEKİLMEZ — API tasarrufu için.
        # Fiyatlar yalnızca takip listesinde "🔄 Güncelle" ile sorgulanır.
        self.after(0, lambda: self._show_dropdown_groups(skins) if search_id == self._search_id else None)

    def _show_loading_dropdown(self):
        self._hide_dropdown()
        DD_W = 460
        x = self.entry_name.winfo_rootx()
        y = self.entry_name.winfo_rooty() + self.entry_name.winfo_height() + 4
        self._dropdown = ctk.CTkToplevel(self)
        self._dropdown.wm_overrideredirect(True)
        self._dropdown.geometry(f"{DD_W}x60+{x}+{y}")
        self._dropdown.attributes("-topmost", True)
        self._dropdown.configure(fg_color="#1c2128")
        ctk.CTkLabel(self._dropdown,
                     text="⏳  Aranıyor...",
                     font=("Arial", 13), text_color=TEXT_DIM).pack(expand=True)

    def _show_dropdown_groups(self, groups):
        self._hide_dropdown()
        self.status_label.configure(text="● Hazır", text_color=GREEN)
        if not groups:
            return

        WEARS_SHORT = [("FN","Factory New","#3fb950"),("MW","Minimal Wear","#58d68d"),
                       ("FT","Field-Tested","#f4d03f"),("WW","Well-Worn","#e67e22"),
                       ("BS","Battle-Scarred","#e74c3c")]

        DD_W   = 460
        CARD_H = 106
        MAX_H  = 560
        x = self.entry_name.winfo_rootx()
        y = self.entry_name.winfo_rooty() + self.entry_name.winfo_height() + 4
        h = min(len(groups) * CARD_H, MAX_H)

        self._dropdown = ctk.CTkToplevel(self)
        self._dropdown.wm_overrideredirect(True)
        self._dropdown.geometry(f"{DD_W}x{h}+{x}+{y}")
        self._dropdown.attributes("-topmost", True)
        self._dropdown.configure(fg_color="#1c2128")

        scroll = ctk.CTkScrollableFrame(
            self._dropdown, fg_color="#1c2128",
            scrollbar_button_color="#30363d",
            scrollbar_button_hover_color="#555",
        )
        scroll.pack(fill="both", expand=True)

        for gi, grp in enumerate(groups):
            base      = grp["base"]
            image_url = grp["image_url"]
            is_knife  = grp["is_knife"]
            cf_price  = grp.get("cf_price")

            if is_knife:
                st_prefix = base.replace("★ ", "★ StatTrak™ ", 1)
            else:
                st_prefix = "StatTrak™ " + base

            card = ctk.CTkFrame(scroll, fg_color="#1c2128", corner_radius=0)
            card.pack(fill="x")

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(8,2))

            img_lbl = ctk.CTkLabel(top, text="", width=44, height=33)
            img_lbl.pack(side="left", padx=(0,8))
            threading.Thread(target=self._load_dropdown_img,
                             args=(img_lbl, image_url), daemon=True).start()

            ctk.CTkLabel(top, text=self._display_name(base),
                         font=("Arial", 13, "bold"), text_color=TEXT_BRIGHT,
                         anchor="w").pack(side="left")

            if cf_price:
                ctk.CTkLabel(top, text=f"${cf_price:.2f}'den",
                             font=("Arial", 11, "bold"), text_color=ACCENT,
                             anchor="e").pack(side="right")

            for st, prefix, row_color in [(False, base, TEXT_DIM), (True, st_prefix, "#cf6a32")]:
                btn_row = ctk.CTkFrame(card, fg_color="transparent")
                btn_row.pack(anchor="w", padx=10, pady=1)
                ctk.CTkLabel(btn_row, text="ST™" if st else "Normal",
                             font=("Arial", 9, "bold"), text_color=row_color,
                             width=42, anchor="e").pack(side="left", padx=(0,4))
                self._wear_btn(btn_row, "Floatsız", ACCENT, prefix, image_url)
                for short, full, color in WEARS_SHORT:
                    self._wear_btn(btn_row, short, color, f"{prefix} ({full})", image_url)

            if gi < len(groups) - 1:
                ctk.CTkFrame(scroll, height=1, fg_color=BORDER).pack(fill="x")

    def _wear_btn(self, parent, label, color, full_name, image_url):
        btn = ctk.CTkButton(
            parent, text=label, width=52, height=22,
            fg_color="#21262d", hover_color=color,
            text_color=color, font=("Arial", 10, "bold"),
            border_width=1, border_color=color, corner_radius=4,
            command=lambda n=full_name, iu=image_url: self._select_suggestion(n, iu),
        )
        btn.pack(side="left", padx=2)

    def _load_dropdown_img(self, label, image_url):
        if not image_url:
            return
        img = load_skin_image(image_url, size=(40, 30))
        if img:
            try:
                self.after(0, lambda: label.configure(image=img))
            except Exception:
                pass

    def _select_suggestion(self, name, image_url=""):
        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, name)
        self._pending_image_url = image_url
        self._hide_dropdown()

    def _hide_dropdown(self):
        if self._dropdown:
            try:
                self._dropdown.destroy()
            except Exception:
                pass
            self._dropdown = None

    # ── Skin kartı ────────────────────────────────────────────────────────────

    @staticmethod
    def _wear_badge(name: str) -> dict:
        wear_map = {
            "Factory New":   {"label": "FN",        "fg": "#e6edf3", "bg": "#3fb950"},
            "Minimal Wear":  {"label": "MW",        "fg": "#e6edf3", "bg": "#2ea043"},
            "Field-Tested":  {"label": "FT",        "fg": "#1a1a1a", "bg": "#f4d03f"},
            "Well-Worn":     {"label": "WW",        "fg": "#e6edf3", "bg": "#e67e22"},
            "Battle-Scarred":{"label": "BS",        "fg": "#e6edf3", "bg": "#e74c3c"},
        }
        for wear, badge in wear_map.items():
            if f"({wear})" in name:
                return badge
        return {"label": "Floatsız", "fg": "#e6edf3", "bg": "#30363d"}

    @staticmethod
    def _display_name(full_name: str) -> str:
        import re
        name = full_name
        name = name.replace("★ StatTrak™ ", "").replace("StatTrak™ ", "")
        name = name.replace("★ ", "").replace("★", "")
        name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        return name

    def _make_skin_row(self, parent, skin):
        skin_id, name, target, last_price, fmin, fmax, image_url, global_price = skin
        fmin = float(fmin or 0.0)
        fmax = float(fmax or 1.0)

        card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=10,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=5, padx=2)

        # Sol - resim
        img_label = ctk.CTkLabel(card, text="", width=80, height=60)
        img_label.pack(side="left", padx=(12, 8), pady=10)
        if image_url:
            threading.Thread(target=self._load_card_img,
                             args=(img_label, image_url), daemon=True).start()

        # Orta - bilgi
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=10)

        name_row = ctk.CTkFrame(info, fg_color="transparent")
        name_row.pack(anchor="w")

        if "StatTrak" in name:
            ctk.CTkLabel(name_row, text="ST™", font=("Arial", 10, "bold"),
                         text_color="#1a1a1a",
                         fg_color="#cf6a32", corner_radius=4,
                         padx=5, pady=1).pack(side="left", padx=(0, 6))

        display = self._display_name(name)
        ctk.CTkLabel(name_row, text=display, font=("Arial", 13, "bold"),
                     text_color=TEXT_BRIGHT, anchor="w").pack(side="left")

        row2 = ctk.CTkFrame(info, fg_color="transparent")
        row2.pack(anchor="w", pady=(4, 0))

        has_float_filter = (fmin != 0.0 or fmax != 1.0)

        # Float filtreli fiyat
        if has_float_filter:
            price_text = f"${last_price:.2f}" if last_price else "—"
            ctk.CTkLabel(row2, text=f"Float filtreli  {price_text}",
                         font=("Arial", 12), text_color=ACCENT2 if last_price else TEXT_DIM
                         ).pack(side="left", padx=(0, 12))

            # Genel en ucuz
            sep = ctk.CTkFrame(row2, width=1, height=14, fg_color=BORDER)
            sep.pack(side="left", padx=(0, 12))
            global_text = f"${global_price:.2f}" if global_price else "—"
            ctk.CTkLabel(row2, text=f"Genel  {global_text}",
                         font=("Arial", 12), text_color=TEXT_DIM
                         ).pack(side="left", padx=(0, 12))
        else:
            price_text = f"${last_price:.2f}" if last_price else "—"
            ctk.CTkLabel(row2, text=f"En düşük  {price_text}",
                         font=("Arial", 12), text_color=ACCENT2 if last_price else TEXT_DIM
                         ).pack(side="left", padx=(0, 14))

        if target:
            reached = last_price and last_price <= target
            ctk.CTkLabel(row2, text=f"Hedef  ${target:.2f}",
                         font=("Arial", 12),
                         text_color=GREEN if reached else TEXT_DIM).pack(side="left", padx=(0, 12))

        if has_float_filter:
            ctk.CTkLabel(row2, text=f"{fmin:.3f}–{fmax:.3f}",
                         font=("Arial", 11), text_color="#666").pack(side="left")
        else:
            wear_badge = self._wear_badge(name)
            ctk.CTkLabel(row2, text=wear_badge["label"],
                         font=("Arial", 10, "bold"),
                         text_color=wear_badge["fg"],
                         fg_color=wear_badge["bg"],
                         corner_radius=4, padx=5, pady=1).pack(side="left")

        # Sağ - sil
        ctk.CTkButton(card, text="✕", width=32, height=32,
                      fg_color="#21262d", hover_color=RED,
                      text_color=TEXT_DIM, font=("Arial", 14), corner_radius=8,
                      border_width=1, border_color=BORDER,
                      command=lambda sid=skin_id: self._remove_skin(sid)
                      ).pack(side="right", padx=12, pady=10)

    def _load_card_img(self, label, image_url):
        img = load_skin_image(image_url, size=(80, 60))
        if img:
            try:
                self.after(0, lambda: label.configure(image=img))
            except Exception:
                pass

    # ── Aksiyonlar ────────────────────────────────────────────────────────────

    def _add_skin(self):
        name = self.entry_name.get().strip()
        target_raw = self.entry_target.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Skin ismini gir.")
            return
        target = None
        if target_raw:
            try:
                target = float(target_raw)
            except ValueError:
                messagebox.showerror("Hata", "Hedef fiyat sayı olmalı.")
                return
        fmin, fmax = self.float_slider.get()
        if database.add_skin(name, target, fmin, fmax, self._pending_image_url):
            self.entry_name.delete(0, "end")
            self.entry_target.delete(0, "end")
            self._pending_image_url = ""
            self._hide_dropdown()
            self._refresh_list()
        else:
            messagebox.showinfo("Bilgi", "Bu skin zaten listede.")

    def _remove_skin(self, skin_id):
        database.remove_skin(skin_id)
        self._refresh_list()

    def _refresh_list(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        skins = database.get_all_skins()
        self.count_label.configure(text=f"{len(skins)} skin")
        self._build_stats()
        if not skins:
            empty = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            empty.pack(expand=True, pady=60)
            ctk.CTkLabel(empty, text="🎯", font=("Arial", 48)).pack()
            ctk.CTkLabel(empty, text="Henüz skin eklenmedi",
                         font=("Arial", 15, "bold"), text_color=TEXT_DIM).pack(pady=(8, 4))
            ctk.CTkLabel(empty, text="Sol panelden skin arayıp ekleyebilirsin",
                         font=("Arial", 12), text_color=TEXT_DIM).pack()
            return
        for skin in skins:
            self._make_skin_row(self.scroll_frame, skin)

    def _check_prices(self):
        skins = database.get_all_skins()
        self.after(0, lambda: self.status_label.configure(
            text="● Kontrol ediliyor...", text_color=ACCENT))
        for skin in skins:
            skin_id, name, target, last_price, fmin, fmax, _, global_price = skin
            fmin = float(fmin or 0.0)
            fmax = float(fmax or 1.0)
            has_filter = (fmin != 0.0 or fmax != 1.0)

            # Wear olmayan (Floatsız) isimler tüm wearleri arar
            is_base = not any(f"({w})" in name for w in api.WEARS)
            if is_base:
                listing = api.get_lowest_across_wears(name, fmin, fmax)
            else:
                listing = api.get_lowest_listing(name, fmin, fmax)
            if not listing:
                continue
            new_price = listing["price"]

            # Float filtresi varsa genel fiyatı da çek
            new_global = None
            if has_filter:
                g = api.get_lowest_across_wears(name) if is_base else api.get_lowest_listing(name)
                new_global = g["price"] if g else None
            if last_price and new_price < last_price:
                drop_pct = ((last_price - new_price) / last_price) * 100
                if drop_pct >= config.PRICE_DROP_THRESHOLD:
                    notifier.notify_price_drop(name, last_price, new_price, target)
            if target and new_price <= target and (not last_price or last_price > target):
                notifier.notify_target_reached(name, new_price, target)
            database.update_last_price(skin_id, new_price, new_global)

        self.after(0, self._refresh_list)
        self.after(0, lambda: self.status_label.configure(
            text=f"● Son kontrol: {time.strftime('%H:%M')}", text_color=GREEN))

    def _manual_check(self):
        threading.Thread(target=self._check_prices, daemon=True).start()

    def _start_checker(self):
        def loop():
            while True:
                self._check_prices()
                time.sleep(config.CHECK_INTERVAL_MINUTES * 60)
        threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
