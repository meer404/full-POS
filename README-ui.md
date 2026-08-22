# UI design system

Everything about how the app looks lives in two files:

- `ui/theme.py` — the design tokens: `Colors`, `Spacing`, `Radius`, plus `icon()`,
  `apply_card_shadow()`, and `apply_app_style(app)`.
- `ui/style.qss` — the actual stylesheet, written with `${TOKEN}` placeholders that get
  substituted from `ui/theme.py` at startup.

Reusable widgets (`Card`, `StatCard`, `DataTable`, `Badge`, `Toast`, `SpinInput`, `Sidebar`,
`TopBar`) live in `ui/widgets/`. Each screen lives in `ui/pages/`.

## Changing colors

Edit the values on `Colors` in `ui/theme.py`, e.g.:

```python
class Colors:
    PRIMARY = "#2E7D32"   # brand green — buttons, totals, active nav item
    SECONDARY = "#1565C0" # blue — info accents, one of the KPI cards
    WARNING = "#F9A825"
    DANGER = "#C62828"
    ...
```

Every screen and widget reads colors from this class (or from `ui/style.qss`, which is
substituted from the same class), so changing a value here updates the whole app — there should
be no hex color literals anywhere else in `ui/`.

If you need a new color that isn't one of the existing tokens, add it to `Colors` first, then
reference it as `${YOUR_TOKEN_NAME}` in `ui/style.qss` or as `Colors.YOUR_TOKEN_NAME` in Python.

## Changing spacing / radius

`Spacing` (4/8/12/16/24/32) and `Radius` (`INPUT`, `CARD`, `PILL`) in `ui/theme.py` are the only
sizes that should be used for margins, padding, and corner radii. In `ui/style.qss` they're
available as `${SPACE_XS..SPACE_XXL}` and `${RADIUS_INPUT|RADIUS_CARD|RADIUS_PILL}`.

## Changing the font

`ui/theme.py` sets `APP_FONT_FAMILY` (default `"Segoe UI"`, used for `app.setFont(...)`) and
`FONT_STACK` (the CSS-style fallback chain used in `ui/style.qss`, currently `'Vazirmatn',
'Noto Sans Arabic', 'Segoe UI', Tahoma, sans-serif`). This app does not bundle a font file — it
relies on whatever Arabic-script-capable font is installed on the machine (Segoe UI ships with
full Arabic/Kurdish glyph support on Windows). To bundle a font instead, drop a `.ttf`/`.otf`
into `assets/fonts/`, load it in `apply_app_style()` via
`QFontDatabase.addApplicationFont(...)`, and update `APP_FONT_FAMILY`/`FONT_STACK` to name it
first in the chain.

## Adding a new screen

1. Create `ui/pages/your_page.py` with a `QWidget` subclass, following the existing
   `save()`/`on_save_clicked()` split (see CLAUDE.md) if it has a "commit" action.
2. Reuse `Card`, `DataTable`, `StatCard`, `Badge`, `SpinInput`, `Toast`/`confirm()` from
   `ui/widgets/` instead of raw `QGroupBox`/`QTableWidget`/`QMessageBox`.
3. Wire it into `main.py`'s `nav_items` list (gated on `user.is_admin` if it's an admin-only
   screen, same as Reports/Expiry/Users today).
4. Add `tests/test_your_page.py` in the same standalone headless style as the existing tests.
