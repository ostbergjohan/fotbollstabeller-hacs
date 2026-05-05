/* ── Column registry ────────────────────────────────────────────────
 * Each entry defines one toggleable column.
 * key    – used in the YAML "columns" list
 * header – table header text
 * thCls  – optional CSS class on <th>
 * cell   – function(teamRow) → HTML string for <td>
 */
var FOTBOLLSTABELLER_COLUMNS = [
  {
    key: "position",
    header: "#",
    thCls: "",
    cell: function (t) {
      return '<td class="pos">' + (t.position || "") + "</td>";
    },
  },
  {
    key: "team",
    header: "Lag",
    thCls: "tc",
    cell: function (t) {
      var logo = t.team_logo
        ? '<img src="' + t.team_logo + "\" loading=\"lazy\" onerror=\"this.style.display='none'\">"
        : "";
      return (
        '<td class="tc">' +
        logo +
        '<span title="' + (t.team || "") + '">' +
        (t.team_short || t.team || "") +
        "</span></td>"
      );
    },
  },
  {
    key: "played",
    header: "S",
    thCls: "",
    cell: function (t) {
      return "<td>" + (t.played_games != null ? t.played_games : "") + "</td>";
    },
  },
  {
    key: "won",
    header: "V",
    thCls: "",
    cell: function (t) {
      return "<td>" + (t.won != null ? t.won : "") + "</td>";
    },
  },
  {
    key: "draw",
    header: "O",
    thCls: "",
    cell: function (t) {
      return "<td>" + (t.draw != null ? t.draw : "") + "</td>";
    },
  },
  {
    key: "lost",
    header: "F",
    thCls: "",
    cell: function (t) {
      return "<td>" + (t.lost != null ? t.lost : "") + "</td>";
    },
  },
  {
    key: "goals",
    header: "Mål",
    thCls: "",
    cell: function (t) {
      return (
        "<td>" +
        (t.goals_for != null ? t.goals_for : "") +
        "-" +
        (t.goals_against != null ? t.goals_against : "") +
        "</td>"
      );
    },
  },
  {
    key: "goal_difference",
    header: "MS",
    thCls: "",
    cell: function (t) {
      var gd = t.goal_difference || 0;
      var gdStr = gd > 0 ? "+" + gd : "" + gd;
      var gdCls = gd > 0 ? "p" : gd < 0 ? "n" : "";
      return '<td class="gd ' + gdCls + '">' + gdStr + "</td>";
    },
  },
  {
    key: "points",
    header: "P",
    thCls: "",
    cell: function (t) {
      return '<td class="pts">' + (t.points != null ? t.points : "") + "</td>";
    },
  },
];

var ALL_COLUMN_KEYS = FOTBOLLSTABELLER_COLUMNS.map(function (c) {
  return c.key;
});

/* ── Helper: resolve active column objects from config ────────── */
function _resolveColumns(config) {
  var keys = config && Array.isArray(config.columns) && config.columns.length
    ? config.columns
    : ALL_COLUMN_KEYS;
  var out = [];
  for (var i = 0; i < keys.length; i++) {
    for (var j = 0; j < FOTBOLLSTABELLER_COLUMNS.length; j++) {
      if (FOTBOLLSTABELLER_COLUMNS[j].key === keys[i]) {
        out.push(FOTBOLLSTABELLER_COLUMNS[j]);
        break;
      }
    }
  }
  return out.length ? out : FOTBOLLSTABELLER_COLUMNS;
}

/* ── Main card ─────────────────────────────────────────────────── */
class FotbollstabellerCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("fotbollstabeller-card-editor");
  }

  static getStubConfig() {
    return { group_url: "" };
  }

  connectedCallback() {
    // Re-trigger render on reconnection
    if (this._initialized && this._hass) {
      this._fetching = false;
      this.hass = this._hass;
    }
  }

  disconnectedCallback() {
    // Clear fetching flag so reconnection can retry
    this._fetching = false;
  }

  setConfig(config) {
    var urlChanged = !this.config || config.group_url !== this.config.group_url;
    this.config = config;
    if (urlChanged) {
      this._wsData = null;
      this._lastFetch = 0;
    }
    this._updateStyles();
    if (this._initialized && this._hass) {
      this.hass = this._hass;
    }
  }

  getCardSize() {
    return 10;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._init();
    }

    // ── WS mode: group_url is set ──
    if (this.config && this.config.group_url) {
      var now = Date.now();
      // Safety: reset _fetching if stuck for more than 30s
      if (this._fetching && this._fetchStart && now - this._fetchStart > 30000) {
        this._fetching = false;
      }
      if ((!this._wsData || now - (this._lastFetch || 0) > 14400000) && !this._fetching) {
        this._fetchWS();
      }
      if (this._wsData) {
        var standings = this._wsData.standings || [];
        var maxRows = this.config.max_rows;
        var limited = maxRows ? standings.slice(0, maxRows) : standings;
        this._render(limited, this._wsData.group_name || "Fotbollstabeller");
      } else if (!this._fetching) {
        this._content.innerHTML = '<p style="padding:12px;color:#999">Laddar\u2026</p>';
      }
      return;
    }

    // No group_url configured
    this._content.innerHTML = '<p style="padding:12px;color:#999">V\u00e4lj en serie i kortets inst\u00e4llningar.</p>';
  }

  _fetchWS() {
    if (!this._hass || this._fetching) return;
    this._fetching = true;
    this._fetchStart = Date.now();
    var self = this;
    this._hass
      .callWS({ type: "fotbollstabeller/get_standings", url: this.config.group_url })
      .then(function (result) {
        self._wsData = result;
        self._lastFetch = Date.now();
        self._fetching = false;
        if (self._hass) self.hass = self._hass;
      })
      .catch(function (err) {
        console.error("Fotbollstabeller fetch error:", err);
        self._fetching = false;
        if (self._content) {
          self._content.innerHTML =
            '<p style="color:red;padding:12px">Kunde inte h\u00e4mta data.</p>';
        }
        // Retry after 5 seconds
        setTimeout(function () {
          if (self._hass && !self._wsData) self.hass = self._hass;
        }, 5000);
      });
  }

  _init() {
    if (this._initialized) return;
    this._initialized = true;
    // Guard: reuse existing shadowRoot if present (e.g. after a hot-reload)
    var shadow = this.shadowRoot || this.attachShadow({ mode: "open" });
    // Clear any stale content in existing shadow root
    while (shadow.firstChild) shadow.removeChild(shadow.firstChild);
    this._styleEl = document.createElement("style");
    var card = document.createElement("ha-card");
    this._content = document.createElement("div");
    card.appendChild(this._content);
    shadow.appendChild(this._styleEl);
    shadow.appendChild(card);
    this._updateStyles();
  }

  _updateStyles() {
    if (!this._styleEl) return;
    var cfg = this.config || {};
    var hc = cfg.header_color || "#1a6b3a";
    var htc = cfg.header_text_color || "#ffffff";
    var ac = cfg.accent_color || hc;
    this._styleEl.textContent = [
      "ha-card{padding:0;overflow:hidden}",
      ".header{background-color:" + hc + ";background-image:linear-gradient(135deg,rgba(255,255,255,0.08),rgba(0,0,0,0.15));color:" + htc + ";padding:14px 16px;font-size:1.1em;font-weight:700}",
      "table{width:100%;border-collapse:collapse;font-size:0.88em}",
      "thead tr{background:#f4f4f4;color:#555;font-size:0.78em;text-transform:uppercase}",
      "th{padding:6px 8px;text-align:center;white-space:nowrap}",
      "th.tc{text-align:left;padding-left:10px}",
      "tbody tr{border-bottom:1px solid #f0f0f0}",
      "tbody tr:hover{background:#f9f9f9}",
      "tbody tr.fav{background:#FFF9C4}",
      "tbody tr.fav:hover{background:#FFF176}",
      "td{padding:7px 8px;text-align:center;vertical-align:middle}",
      "td.tc{text-align:left;padding-left:10px;display:flex;align-items:center;gap:8px}",
      "td.tc img{width:22px;height:22px;object-fit:contain;flex-shrink:0}",
      "td.tc span{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px}",
      "td.pos{font-weight:700;color:#333;width:28px}",
      "td.pts{font-weight:800;color:" + ac + "}",
      "td.gd.p{color:#2e7d32}",
      "td.gd.n{color:#c62828}",
    ].join("");
  }

  _render(standings, groupName) {
    var cols = _resolveColumns(this.config);
    var fav = ((this.config && this.config.favorite_team) || "").toLowerCase();

    var ths = cols
      .map(function (c) {
        return "<th" + (c.thCls ? ' class="' + c.thCls + '"' : "") + ">" + c.header + "</th>";
      })
      .join("");

    var rows = standings
      .map(function (t) {
        var isFav =
          fav &&
          ((t.team || "").toLowerCase().indexOf(fav) !== -1 ||
            (t.team_short || "").toLowerCase().indexOf(fav) !== -1 ||
            fav.indexOf((t.team || "").toLowerCase()) !== -1);
        var tds = cols
          .map(function (c) {
            return c.cell(t);
          })
          .join("");
        return '<tr class="' + (isFav ? "fav" : "") + '">' + tds + "</tr>";
      })
      .join("");

    this._content.innerHTML =
      '<div class="header">' +
      (groupName || "Fotbollstabeller") +
      "</div>" +
      "<table><thead><tr>" +
      ths +
      "</tr></thead><tbody>" +
      rows +
      "</tbody></table>";
  }
}

/* ── Visual card editor ────────────────────────────────────────── */
class FotbollstabellerCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = Object.assign({}, config);
    this._leagues = null;
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._leagues) {
      var self = this;
      hass
        .callWS({ type: "fotbollstabeller/get_leagues" })
        .then(function (leagues) {
          self._leagues = leagues;
          self._build();
        })
        .catch(function () {
          self._leagues = [];
          self._build();
        });
    }
  }

  _build() {
    if (this._built) return;
    this._built = true;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    var cfg = this._config || {};
    var leagues = this._leagues || [];

    var currentSlug = "";
    if (cfg.group_url) {
      var parts = cfg.group_url.split("/");
      currentSlug = parts[parts.length - 1] || cfg.group_url;
    }
    var isKnown = false;
    for (var k = 0; k < leagues.length; k++) {
      if (leagues[k].slug === currentSlug) { isKnown = true; break; }
    }
    var showCustom = cfg.group_url && !isKnown;

    var active = Array.isArray(cfg.columns) && cfg.columns.length ? cfg.columns : ALL_COLUMN_KEYS;

    var html = '<style>'
      + ':host{display:block;padding:16px}'
      + '.row{display:flex;align-items:center;margin-bottom:12px;gap:8px}'
      + 'label{min-width:120px;font-weight:500}'
      + 'input[type=text]{flex:1;padding:6px 8px;border:1px solid #ccc;border-radius:4px}'
      + 'input[type=number]{width:80px;padding:6px 8px;border:1px solid #ccc;border-radius:4px}'
      + 'input[type=color]{width:40px;height:34px;padding:2px;border:1px solid #ccc;border-radius:4px;cursor:pointer}'
      + 'select{flex:1;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:0.9em}'
      + '.sep{text-align:center;color:#999;font-size:0.82em;margin:8px 0}'
      + '.custom-row{display:none}'
      + '.custom-row.show{display:flex}'
      + '.col-section{margin-top:12px}'
      + '.col-section h3{margin:0 0 8px;font-size:0.95em;color:#555}'
      + '.col-grid{display:flex;flex-wrap:wrap;gap:6px}'
      + '.col-chip{display:flex;align-items:center;gap:4px;padding:4px 10px;border:1px solid #ccc;border-radius:16px;cursor:pointer;user-select:none;font-size:0.85em;transition:all .15s}'
      + '.col-chip.active{background:#1a6b3a;color:#fff;border-color:#1a6b3a}'
      + '.col-chip:hover{opacity:0.85}'
      + '</style>';

    // League dropdown
    html += '<div class="row"><label>Serie</label><select id="league">';
    html += '<option value="">-- v\u00e4lj serie --</option>';
    for (var i = 0; i < leagues.length; i++) {
      var lg = leagues[i];
      var sel = lg.slug === currentSlug ? ' selected' : '';
      html += '<option value="' + lg.slug + '"' + sel + '>' + lg.name + '</option>';
    }
    html += '<option value="__custom__"' + (showCustom ? ' selected' : '') + '>Egen URL\u2026</option>';
    html += '</select></div>';

    // Custom URL field
    html += '<div class="row custom-row' + (showCustom ? ' show' : '') + '" id="custom_row"><label>URL / slug</label>'
      + '<input type="text" id="custom_url" value="' + (cfg.group_url || '') + '" placeholder="u17-allsvenskan-norra"></div>';

    // Options
    html += '<div class="row"><label>Favoritlag</label>'
      + '<input type="text" id="fav" value="' + (cfg.favorite_team || "") + '" placeholder="Markeras i gult"></div>';
    html += '<div class="row"><label>Max rader</label>'
      + '<input type="number" id="maxrows" min="0" value="' + (cfg.max_rows || "") + '" placeholder="alla"></div>';

    // Colors
    html += '<div class="sep">\u2014 f\u00e4rger \u2014</div>';
    html += '<div class="row"><label>Rubrikf\u00e4rg</label><input type="color" id="header_color" value="' + (cfg.header_color || '#1a6b3a') + '"></div>';
    html += '<div class="row"><label>Rubriktext</label><input type="color" id="header_text_color" value="' + (cfg.header_text_color || '#ffffff') + '"></div>';
    html += '<div class="row"><label>Accentf\u00e4rg</label><input type="color" id="accent_color" value="' + (cfg.accent_color || '#1a6b3a') + '"></div>';

    // Columns
    html += '<div class="col-section"><h3>Kolumner (klicka f\u00f6r att v\u00e4xla)</h3><div class="col-grid">';
    for (var ci = 0; ci < FOTBOLLSTABELLER_COLUMNS.length; ci++) {
      var c = FOTBOLLSTABELLER_COLUMNS[ci];
      var isActive = active.indexOf(c.key) !== -1;
      html += '<div class="col-chip' + (isActive ? ' active' : '') + '" data-key="' + c.key + '">'
        + c.header + ' <small>(' + c.key + ')</small></div>';
    }
    html += '</div></div>';

    this.shadowRoot.innerHTML = html;

    // Bind events (once, no re-render)
    var self = this;

    this.shadowRoot.getElementById("league").addEventListener("change", function (e) {
      var val = e.target.value;
      var customRow = self.shadowRoot.getElementById("custom_row");
      if (val === "__custom__") {
        self._config.group_url = "";
        customRow.classList.add("show");
      } else if (val === "") {
        delete self._config.group_url;
        customRow.classList.remove("show");
      } else {
        self._config.group_url = val;
        customRow.classList.remove("show");
      }
      self._fireChanged();
    });

    this.shadowRoot.getElementById("custom_url").addEventListener("change", function (e) {
      var v = e.target.value.trim();
      if (v) { self._config.group_url = v; } else { delete self._config.group_url; }
      self._fireChanged();
    });

    this.shadowRoot.getElementById("fav").addEventListener("change", function (e) {
      var v = e.target.value.trim();
      if (v) { self._config.favorite_team = v; } else { delete self._config.favorite_team; }
      self._fireChanged();
    });

    this.shadowRoot.getElementById("maxrows").addEventListener("change", function (e) {
      var v = parseInt(e.target.value, 10);
      if (v > 0) { self._config.max_rows = v; } else { delete self._config.max_rows; }
      self._fireChanged();
    });

    this.shadowRoot.getElementById("header_color").addEventListener("input", function (e) {
      self._config.header_color = e.target.value;
      self._fireChanged();
    });
    this.shadowRoot.getElementById("header_text_color").addEventListener("input", function (e) {
      self._config.header_text_color = e.target.value;
      self._fireChanged();
    });
    this.shadowRoot.getElementById("accent_color").addEventListener("input", function (e) {
      self._config.accent_color = e.target.value;
      self._fireChanged();
    });

    var chips = this.shadowRoot.querySelectorAll(".col-chip");
    for (var cj = 0; cj < chips.length; cj++) {
      chips[cj].addEventListener("click", function () {
        var key = this.getAttribute("data-key");
        self._toggleColumn(key);
        this.classList.toggle("active");
      });
    }
  }

  _toggleColumn(key) {
    var cfg = this._config || {};
    var cols = Array.isArray(cfg.columns) && cfg.columns.length
      ? cfg.columns.slice()
      : ALL_COLUMN_KEYS.slice();
    var idx = cols.indexOf(key);
    if (idx !== -1) {
      if (cols.length <= 1) return;
      cols.splice(idx, 1);
    } else {
      var insertIdx = 0;
      for (var i = 0; i < ALL_COLUMN_KEYS.length; i++) {
        if (ALL_COLUMN_KEYS[i] === key) break;
        if (cols.indexOf(ALL_COLUMN_KEYS[i]) !== -1) insertIdx++;
      }
      cols.splice(insertIdx, 0, key);
    }
    if (cols.length === ALL_COLUMN_KEYS.length) {
      delete this._config.columns;
    } else {
      this._config.columns = cols;
    }
    this._fireChanged();
  }

  _fireChanged() {
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config } }));
  }
}

/* ── Register elements ─────────────────────────────────────────── */
if (!customElements.get("fotbollstabeller-card-editor")) {
  customElements.define("fotbollstabeller-card-editor", FotbollstabellerCardEditor);
}
if (!customElements.get("fotbollstabeller-card")) {
  customElements.define("fotbollstabeller-card", FotbollstabellerCard);
  console.info(
    "%c FOTBOLLSTABELLER-CARD %c loaded",
    "color:white;background:#1a6b3a;font-weight:700;padding:2px 6px",
    ""
  );
}

window.customCards = window.customCards || [];
if (!window.customCards.some(function (c) { return c.type === "fotbollstabeller-card"; })) {
  window.customCards.push({
    type: "fotbollstabeller-card",
    name: "Fotbollstabeller",
    description: "Tabell från fotbollstabeller.nu med konfiguerbara kolumner.",
    preview: false,
  });
}