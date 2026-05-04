# Fotbollstabeller – Home Assistant Integration

![version](https://img.shields.io/badge/version-2.0.0-blue) ![hacs](https://img.shields.io/badge/HACS-Custom-orange)

Home Assistant integration som visar tabell och lagstatistik från **fotbollstabeller.nu** direkt i din dashboard. Fungerar med alla grupper/serier – P17 Allsvenskan, division 1, osv. Ingen API-nyckel krävs.

---

## Funktioner

- 📋 Inbyggt **Lovelace-kort** med tabell och konfiguerbara kolumner
- 🏟️ **Hero-kort per lag** med manuell bild-URL, poäng, målstatistik m.m.
- 📡 Sensor med **fullständig tabell** som attribut
- ⚽ En sensor **per lag** med aktuell position och detaljstatistik
- 🔄 Uppdateras automatiskt varje **60:e minut**
- 🔑 Ingen API-nyckel krävs

---

## Installation via HACS

1. Gå till **HACS → Integrations → ⋮ → Custom repositories**
2. Lägg till `https://github.com/ostbergjohan/fotbollstabeller-hacs` som **Integration**
3. Sök efter **Fotbollstabeller** och klicka **Download**
4. **Starta om Home Assistant**
5. Gå till **Settings → Devices & Services → Add Integration → Fotbollstabeller**
6. Ange URL till en grupp på fotbollstabeller.nu, t.ex.:
   - `u17-allsvenskan-sodra`
   - `fotbollstabeller.nu/home/group/u17-allsvenskan-sodra`
   - `https://www.fotbollstabeller.nu/home/group/u17-allsvenskan-sodra`

Du kan lägga till **flera grupper** genom att upprepa steg 5–6.

---

## Lovelace-kort

### Tabellkort

Lägg till via **Edit Dashboard → Add Card → Custom: Fotbollstabeller**, eller manuellt:

```yaml
type: custom:fotbollstabeller-card
entity: sensor.p17_allsvenskan_sodra_2026_tabell   # välj din tabellsensor
max_rows: 10                                        # valfritt, standard visar alla lag
favorite_team: Hammarby                              # valfritt, markerar raden i gult
```

### Lagkort

Hero-kort för ett enskilt lag. Eftersom fotbollstabeller.nu inte har laglogotyper kan du ange en bild-URL manuellt:

```yaml
type: custom:fotbollstabeller-team-card
entity: sensor.p17_allsvenskan_sodra_2026_bk_hacken
image: https://example.com/bk-hacken-logo.png   # valfri bild-URL
subtitle: P17 Allsvenskan Södra                   # valfri undertext
rows: 4                                            # 1-4, mer detalj med högre nummer
```

**rows-nivåer:**
| Nivå | Innehåll |
|------|----------|
| 1 | Namn + position |
| 2 | + poäng |
| 3 | + V/O/F |
| 4 | + mål & målskillnad |

---

## Sensorer

### Tabellsensor

Entity-namn genereras från gruppnamnet, t.ex. `sensor.p17_allsvenskan_sodra_2026_tabell`.

| | |
|---|---|
| **State** | Namn på serieledaren |
| **Attribut** | `group_name`, `standings` |

`standings` är en lista med ett objekt per lag:

```json
{
  "position": 1,
  "team": "BK Häcken",
  "team_short": "BK Häcken",
  "team_logo": null,
  "played_games": 5,
  "won": 3,
  "draw": 2,
  "lost": 0,
  "goals_for": 19,
  "goals_against": 7,
  "goal_difference": 12,
  "points": 11
}
```

### Lagsensor

En sensor per lag, t.ex. `sensor.p17_allsvenskan_sodra_2026_bk_hacken`.

| | |
|---|---|
| **State** | Tabellposition (heltal) |
| **Enhet** | `pos` |
| **Attribut** | `team`, `points`, `played`, `won`, `draw`, `lost`, `goals_for`, `goals_against`, `goal_difference`, `crest` |

---

## Datakälla

Data hämtas genom att scrapa gruppsidan på [fotbollstabeller.nu](https://www.fotbollstabeller.nu/). Ingen API-nyckel krävs. Uppdateras var 60:e minut.

---

## License

MIT – see [LICENSE](LICENSE) for details.
