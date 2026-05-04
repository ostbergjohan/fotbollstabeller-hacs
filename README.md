# Fotbollstabeller – Home Assistant Integration

![version](https://img.shields.io/badge/version-3.0.0-blue) ![hacs](https://img.shields.io/badge/HACS-Custom-orange)

Home Assistant-integration som visar fotbollstabeller från **fotbollstabeller.nu** direkt i din dashboard. Stödjer alla serier – Allsvenskan, Superettan, Division 1–3, P17/P19/F17/F19, med mera. Ingen API-nyckel krävs.

---

## Funktioner

- 📋 **Tabellkort** med konfiguerbara kolumner och färger
- 🏟️ **Lagkort** (hero-stil) med poäng, målstatistik och valfri klubbild
- 🎨 **Anpassningsbara färger** – rubrik, text och accent direkt i kortets editor
- ⚡ **Zero-config** – installera integrationen, välj serie direkt i kortet
- 🔄 Data hämtas via WebSocket med 5 min cache
- 🔑 Ingen API-nyckel krävs

---

## Installation

1. Gå till **HACS → Integrations → ⋮ → Custom repositories**
2. Lägg till `https://github.com/ostbergjohan/fotbollstabeller-hacs` som **Integration**
3. Sök efter **Fotbollstabeller** och klicka **Download**
4. **Starta om Home Assistant**
5. Gå till **Settings → Devices & Services → Add Integration → Fotbollstabeller**
6. Klicka **Skicka** – klart! Ingen konfiguration behövs.

Serier väljs sedan direkt i korten.

---

## Lovelace-kort

### Tabellkort

Lägg till via **Edit Dashboard → Add Card → Custom: Fotbollstabeller**.

Editorn låter dig:
- Välja serie från en lista eller ange en egen URL/slug
- Ställa in favoritlag (markeras i gult)
- Begränsa antal rader
- Välja vilka kolumner som visas
- Anpassa färger (rubrik, rubriktext, accent)

YAML-exempel:

```yaml
type: custom:fotbollstabeller-card
group_url: allsvenskan-herrar
favorite_team: Hammarby
max_rows: 10
header_color: "#1a6b3a"
header_text_color: "#ffffff"
accent_color: "#1a6b3a"
columns:
  - position
  - team
  - played
  - won
  - draw
  - lost
  - goals
  - goal_difference
  - points
```

### Lagkort

Hero-kort för ett enskilt lag:

```yaml
type: custom:fotbollstabeller-team-card
group_url: allsvenskan-herrar
team: Hammarby
image: https://example.com/hammarby-logo.png
subtitle: Allsvenskan 2026
rows: 4
header_color: "#00543e"
accent_color: "#7dff7d"
```

**rows-nivåer:**

| Nivå | Innehåll |
|------|----------|
| 1 | Namn + position |
| 2 | + poäng |
| 3 | + V/O/F |
| 4 | + mål & målskillnad |

---

## Färginställningar

Båda korten stödjer färgval via den visuella editorn eller YAML:

| Inställning | Tabellkort | Lagkort | Standard |
|---|---|---|---|
| `header_color` | Header-bakgrund | Hero + poängbar | `#1a6b3a` |
| `header_text_color` | Header-textfärg | — | `#ffffff` |
| `accent_color` | Poängkolumn | Poängtext | `#1a6b3a` / `#7dff7d` |

---

## Tillgängliga serier

Dropdown i editorn innehåller bl.a.:

- Allsvenskan & Superettan (herrar/damer)
- Elitettan (damer)
- Ettan Norra/Södra
- Division 1–3 (herrar/damer)
- P17/P19/F17/F19 Allsvenskan & Superettan

Du kan även ange **vilken grupp-URL som helst** från fotbollstabeller.nu via "Egen URL".

---

## Datakälla

Data hämtas genom att scrapa gruppsidan på [fotbollstabeller.nu](https://www.fotbollstabeller.nu/). Ingen API-nyckel krävs. Kortet hämtar data via WebSocket med 5 minuters cache.

---

## License

MIT – see [LICENSE](LICENSE) for details.
