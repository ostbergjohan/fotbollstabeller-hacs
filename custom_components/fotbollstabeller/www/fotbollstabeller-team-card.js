/* ═══════════════════════════════════════════════════════════════════
 *  Fotbollstabeller Team Card
 *  A hero-style card for a single team.
 *
 *  Config (WS mode – preferred, no sensor setup needed):
 *    group_url    – slug or URL to a fotbollstabeller.nu group
 *    team         – exact team name from the standings
 *    image        – URL to a team logo/image (optional)
 *    subtitle     – custom subtitle text (optional)
 *    rows         – 1 | 2 | 3 | 4 (default: 4)
 *
 *  Config (Entity mode – legacy, needs integration config entry):
 *    entity       – sensor.<group>_<team>
 *    image / subtitle / rows – same as above
 * ═══════════════════════════════════════════════════════════════════ */

/* ── Styles ────────────────────────────────────────────────────── */
var TEAM_CARD_STYLES = [
  ":host{display:block}",
  "ha-card{padding:0;overflow:hidden;border-radius:16px;background:var(--ha-card-background,var(--card-background-color,#2a2a2a));color:var(--primary-text-color,#fff)}",

  /* Hero */
  ".hero{background:linear-gradient(135deg,#1a6b3a 0%,#0d4a28 100%);padding:28px 24px 22px;display:flex;align-items:center;gap:18px;position:relative;overflow:hidden}",
  ".hero::after{content:'';position:absolute;right:-30px;top:-30px;width:140px;height:140px;background:rgba(255,255,255,0.04);border-radius:50%}",
  ".hero img{width:72px;height:72px;object-fit:contain;filter:drop-shadow(0 2px 8px rgba(0,0,0,0.3));flex-shrink:0}",
  ".hero .no-img{width:72px;height:72px;display:flex;align-items:center;justify-content:center;font-size:2em;background:rgba(255,255,255,0.1);border-radius:12px;flex-shrink:0}",
  ".hero-text{flex:1;min-width:0}",
  ".hero-text .team-name{font-size:1.3em;font-weight:700;line-height:1.2;color:#fff;text-shadow:0 1px 4px rgba(0,0,0,0.3)}",
  ".hero-text .subtitle{font-size:0.82em;color:rgba(255,255,255,0.7);margin-top:4px}",
  ".position-badge{position:absolute;top:14px;right:16px;background:rgba(255,255,255,0.15);backdrop-filter:blur(4px);border-radius:10px;padding:4px 12px;font-size:0.75em;font-weight:600;letter-spacing:0.5px;color:rgba(255,255,255,0.9)}",
  ".position-badge span{font-size:1.4em;font-weight:800;color:#fff}",

  /* Points bar */
  ".points-bar{display:flex;align-items:center;justify-content:center;gap:6px;padding:12px;background:linear-gradient(90deg,#145a30,#1a6b3a);font-size:0.85em;color:rgba(255,255,255,0.75)}",
  ".points-bar .pts{font-size:1.6em;font-weight:800;color:#7dff7d}",

  /* Stats grid */
  ".stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#333;padding:1px}",
  ".stat{background:var(--ha-card-background,var(--card-background-color,#2a2a2a));text-align:center;padding:14px 8px}",
  ".stat .val{font-size:1.4em;font-weight:700}",
  ".stat .lbl{font-size:0.72em;color:var(--secondary-text-color,#999);text-transform:uppercase;letter-spacing:0.5px;margin-top:2px}",
  ".stat.won .val{color:#66bb6a}",
  ".stat.draw .val{color:#ffa726}",
  ".stat.lost .val{color:#ef5350}",

  /* Goals section */
  ".goals{display:flex;align-items:center;justify-content:center;gap:16px;padding:16px;border-top:1px solid rgba(255,255,255,0.08)}",
  ".goals .g-block{text-align:center}",
  ".goals .g-block .val{font-size:1.3em;font-weight:700}",
  ".goals .g-block .lbl{font-size:0.7em;color:var(--secondary-text-color,#999);text-transform:uppercase;margin-top:2px}",
  ".goals .divider{font-size:1.2em;color:var(--secondary-text-color,#555)}",
  ".goals .gd{background:rgba(102,187,106,0.15);border-radius:8px;padding:6px 14px;text-align:center}",
  ".goals .gd .val.pos{color:#66bb6a}",
  ".goals .gd .val.neg{color:#ef5350}",
  ".goals .gd .val.zero{color:var(--secondary-text-color,#999)}",

  /* Form bar */
  ".form-bar{display:flex;height:5px}",
  ".form-bar .w{background:#66bb6a}",
  ".form-bar .d{background:#ffa726}",
  ".form-bar .l{background:#ef5350}",
].join("");


/* ── Position suffix helper ────────────────────────────────────── */
function _posSuffix(pos) {
  if (pos === 1 || pos === 2) return ":a";
  return ":e";
}


/* ── Main card ─────────────────────────────────────────────────── */
class FotbollstabellerTeamCard extends HTMLElement {

  static getConfigElement() {
    return document.createElement("fotbollstabeller-team-card-editor");
  }

  static getStubConfig() {
    return { group_url: "", team: "", rows: 4, image: "" };
  }

  setConfig(config) {
    if (!config.entity && !config.group_url) {
      throw new Error("V\u00e4lj en serie och ett lag i kortets inst\u00e4llningar.");
    }
    var urlChanged = !this.config || config.group_url !== this.config.group_url;
    this.config = config;
    if (urlChanged) {
      this._wsData = null;
      this._lastFetch = 0;
    }
    if (this._initialized && this._hass) {
      this.hass = this._hass;
    }
  }

  getCardSize() {
    var r = (this.config && this.config.rows) || 4;
    if (r <= 1) return 3;
    if (r === 2) return 4;
    if (r === 3) return 6;
    return 8;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) this._init();

    // ── WS mode ──
    if (this.config && this.config.group_url && this.config.team) {
      var now = Date.now();
      if ((!this._wsData || now - (this._lastFetch || 0) > 1800000) && !this._fetching) {
        this._fetchWS();
      }
      if (this._wsData) {
        var row = this._findTeamRow(this._wsData.standings || [], this.config.team);
        if (row) {
          this._renderFromRow(row, this._wsData.group_name || "");
        } else {
          this._content.innerHTML = '<p style="color:red;padding:12px">Lag "' + this.config.team + '" hittades inte.</p>';
        }
      } else if (!this._fetching) {
        this._content.innerHTML = '<p style="padding:12px;color:#999">Laddar\u2026</p>';
      }
      return;
    }

    // ── Entity mode ──
    var entity = this.config && this.config.entity;
    if (!entity) {
      this._content.innerHTML = '<p style="padding:12px;color:#999">V\u00e4lj serie och lag.</p>';
      return;
    }
    var stateObj = hass.states[entity];
    if (!stateObj) {
      this._content.innerHTML =
        '<p style="color:red;padding:12px">Entity <b>' + entity + "</b> not found.</p>";
      return;
    }
    this._renderCard(stateObj);
  }

  _fetchWS() {
    if (!this._hass || this._fetching) return;
    this._fetching = true;
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
        console.error("Fotbollstabeller team fetch error:", err);
        self._fetching = false;
      });
  }

  _findTeamRow(standings, teamName) {
    var lower = teamName.toLowerCase();
    for (var i = 0; i < standings.length; i++) {
      if ((standings[i].team || "").toLowerCase() === lower) return standings[i];
    }
    return null;
  }

  _renderFromRow(row, groupName) {
    var rows = Math.min(4, Math.max(1, parseInt(this.config.rows, 10) || 4));
    var crest = this.config.image || "";
    var teamName = row.team || "";
    var position = row.position;
    var points = row.points;
    var played = row.played_games;
    var won = row.won;
    var draw = row.draw;
    var lost = row.lost;
    var goalsFor = row.goals_for;
    var goalsAgainst = row.goals_against;
    var goalDiff = row.goal_difference;

    this._renderHtml(teamName, crest, position, points, played, won, draw, lost, goalsFor, goalsAgainst, goalDiff, rows, groupName);
  }

  _init() {
    this._initialized = true;
    var shadow = this.attachShadow({ mode: "open" });
    var style = document.createElement("style");
    style.textContent = TEAM_CARD_STYLES;
    var card = document.createElement("ha-card");
    this._content = document.createElement("div");
    card.appendChild(this._content);
    shadow.appendChild(style);
    shadow.appendChild(card);
  }

  _renderCard(stateObj) {
    var a = stateObj.attributes;
    var rows = Math.min(4, Math.max(1, parseInt(this.config.rows, 10) || 4));

    var teamName = a.team || stateObj.attributes.friendly_name || "";
    var crest = this.config.image || a.crest || "";
    var position = parseInt(stateObj.state, 10);
    var points = a.points;
    var played = a.played;
    var won = a.won;
    var draw = a.draw;
    var lost = a.lost;
    var goalsFor = a.goals_for;
    var goalsAgainst = a.goals_against;
    var goalDiff = a.goal_difference;

    this._renderHtml(teamName, crest, position, points, played, won, draw, lost, goalsFor, goalsAgainst, goalDiff, rows, "");
  }

  _renderHtml(teamName, crest, position, points, played, won, draw, lost, goalsFor, goalsAgainst, goalDiff, rows, groupName) {

    var html = "";

    /* ── Row 1: Hero ──────────────────────────── */
    var imgTag = crest
      ? '<img src="' + crest + "\" alt=\"\" loading=\"lazy\" onerror=\"this.style.display='none'\">"
      : '<div class="no-img">\u26BD</div>';
    var posNum = parseInt(position, 10);
    var posBadge = !isNaN(posNum)
      ? '<div class="position-badge"><span>' + posNum + "</span>" + _posSuffix(posNum) + "</div>"
      : "";
    html +=
      '<div class="hero">' +
        imgTag +
        '<div class="hero-text">' +
          '<div class="team-name">' + teamName + "</div>" +
          '<div class="subtitle">' + (this.config.subtitle || groupName || "fotbollstabeller.nu") + '</div>' +
        "</div>" +
        posBadge +
      "</div>";

    /* ── Row 2: Points bar ────────────────────── */
    if (rows >= 2) {
      var ptsStr = points != null ? points : "\u2013";
      var playedStr = played != null ? played : "\u2013";
      html +=
        '<div class="points-bar">' +
          '<span class="pts">' + ptsStr + "</span> po\u00e4ng" +
          " &nbsp;\u00b7&nbsp; " + playedStr + " spelade" +
        "</div>";
    }

    /* ── Row 3: W / D / L ─────────────────────── */
    if (rows >= 3) {
      html +=
        '<div class="stats">' +
          '<div class="stat won"><div class="val">' + (won != null ? won : "\u2013") + '</div><div class="lbl">Vinster</div></div>' +
          '<div class="stat draw"><div class="val">' + (draw != null ? draw : "\u2013") + '</div><div class="lbl">Oavgjort</div></div>' +
          '<div class="stat lost"><div class="val">' + (lost != null ? lost : "\u2013") + '</div><div class="lbl">F\u00f6rluster</div></div>' +
        "</div>";
    }

    /* ── Row 4: Goals + form bar ──────────────── */
    if (rows >= 4) {
      var gd = goalDiff != null ? parseInt(goalDiff, 10) : null;
      var gdStr = gd != null ? (gd > 0 ? "+" + gd : "" + gd) : "\u2013";
      var gdCls = gd != null ? (gd > 0 ? "pos" : gd < 0 ? "neg" : "zero") : "zero";

      html +=
        '<div class="goals">' +
          '<div class="g-block"><div class="val">' + (goalsFor != null ? goalsFor : "\u2013") + '</div><div class="lbl">Gjorda</div></div>' +
          '<div class="divider">\u2013</div>' +
          '<div class="g-block"><div class="val">' + (goalsAgainst != null ? goalsAgainst : "\u2013") + '</div><div class="lbl">Insl\u00e4ppta</div></div>' +
          '<div class="gd"><div class="val ' + gdCls + '">' + gdStr + '</div><div class="lbl">M\u00e5lskillnad</div></div>' +
        "</div>";

      var w = parseInt(won, 10) || 0;
      var d = parseInt(draw, 10) || 0;
      var l = parseInt(lost, 10) || 0;
      if (w + d + l > 0) {
        html +=
          '<div class="form-bar">' +
            '<div class="w" style="flex:' + w + '"></div>' +
            '<div class="d" style="flex:' + d + '"></div>' +
            '<div class="l" style="flex:' + l + '"></div>' +
          "</div>";
      }
    }

    this._content.innerHTML = html;
  }
}


/* ── Visual card editor ────────────────────────────────────────── */
class FotbollstabellerTeamCardEditor extends HTMLElement {

  setConfig(config) {
    this._config = Object.assign({}, config);
    this._leagues = null;
    this._teams = null;         // list of team names for the selected league
    this._teamsSlug = null;     // which slug the teams list corresponds to
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._leagues) {
      var self = this;
      hass
        .callWS({ type: "fotbollstabeller/get_leagues" })
        .then(function (leagues) {
          self._leagues = leagues;
          if (self._rendered) self._render();
        })
        .catch(function () {
          self._leagues = [];
        });
    }
    if (this._rendered) this._render();
  }

  _fetchTeams(slug) {
    if (!this._hass || !slug) return;
    if (this._teamsSlug === slug && this._teams) return; // already loaded
    this._teamsSlug = slug;
    this._teams = null;
    var self = this;
    this._hass
      .callWS({ type: "fotbollstabeller/get_standings", url: slug })
      .then(function (result) {
        self._teams = (result.standings || []).map(function (r) { return r.team; });
        self._render();
      })
      .catch(function () {
        self._teams = [];
        self._render();
      });
  }

  _render() {
    this._rendered = true;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    var cfg = this._config || {};
    var leagues = this._leagues || [];
    var currentRows = cfg.rows || 4;
    var currentImage = cfg.image || "";
    var currentSubtitle = cfg.subtitle || "";

    // Determine current slug
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

    // Ensure team list is loaded for current slug
    if (currentSlug && currentSlug !== "__custom__") {
      this._fetchTeams(currentSlug);
    }
    var teams = this._teams || [];

    /* Collect entity-based team sensors */
    var teamEntities = [];
    if (this._hass) {
      var states = this._hass.states;
      for (var sid in states) {
        var a = states[sid].attributes;
        if (a && a.team && a.points !== undefined && a.played !== undefined) {
          teamEntities.push(sid);
        }
      }
      teamEntities.sort();
    }

    var html =
      "<style>" +
        ":host{display:block;padding:16px}" +
        ".row{display:flex;align-items:center;margin-bottom:12px;gap:8px}" +
        "label{min-width:90px;font-weight:500}" +
        "select{flex:1;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:0.9em}" +
        "input[type=text]{flex:1;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:0.9em}" +
        ".sep{text-align:center;color:#999;font-size:0.82em;margin:8px 0}" +
        ".desc{font-size:0.78em;color:#888;margin:-4px 0 8px 98px}" +
      "</style>";

    // ── League dropdown ──
    html += '<div class="row"><label>Serie</label><select id="league">';
    html += '<option value=""' + (!cfg.group_url && !cfg.entity ? ' selected' : '') + '>-- v\u00e4lj serie --</option>';
    for (var i = 0; i < leagues.length; i++) {
      var lg = leagues[i];
      var sel = lg.slug === currentSlug ? ' selected' : '';
      html += '<option value="' + lg.slug + '"' + sel + '>' + lg.name + '</option>';
    }
    html += '<option value="__custom__"' + (showCustom ? ' selected' : '') + '>Egen URL\u2026</option>';
    html += '</select></div>';

    if (showCustom) {
      html += '<div class="row"><label>URL / slug</label>'
        + '<input type="text" id="custom_url" value="' + (cfg.group_url || '') + '" placeholder="u17-allsvenskan-norra"></div>';
    }

    // ── Team dropdown (populated from WS standings) ──
    if (cfg.group_url && teams.length > 0) {
      html += '<div class="row"><label>Lag</label><select id="team">';
      html += '<option value="">-- v\u00e4lj lag --</option>';
      for (var ti = 0; ti < teams.length; ti++) {
        var tn = teams[ti];
        var selT = tn === cfg.team ? ' selected' : '';
        html += '<option value="' + tn + '"' + selT + '>' + tn + '</option>';
      }
      html += '</select></div>';
    } else if (cfg.group_url && !teams.length && this._teamsSlug) {
      html += '<div class="desc">Laddar lag\u2026</div>';
    }

    // ── OR: Entity dropdown ──
    if (teamEntities.length > 0) {
      html += '<div class="sep">\u2014 eller via sensor \u2014</div>';
      html += '<div class="row"><label>Entity</label><select id="entity">';
      html += '<option value="">--</option>';
      for (var j = 0; j < teamEntities.length; j++) {
        var eid = teamEntities[j];
        var friendly = this._hass.states[eid].attributes.friendly_name || eid;
        var selE = eid === cfg.entity ? ' selected' : '';
        html += '<option value="' + eid + '"' + selE + '>' + friendly + '</option>';
      }
      html += '</select></div>';
    }

    // ── Other options ──
    html += '<div class="row"><label>Bild-URL</label>'
      + '<input type="text" id="image" value="' + currentImage + '" placeholder="https://..."></div>';
    html += '<div class="desc">Valfri URL till lagbild/logotyp.</div>';

    html += '<div class="row"><label>Undertext</label>'
      + '<input type="text" id="subtitle" value="' + currentSubtitle + '" placeholder="auto"></div>';
    html += '<div class="desc">Visas under lagnamnet.</div>';

    html += '<div class="row"><label>Rader</label><select id="rows">';
    var rowLabels = [
      "1 \u2013 Namn + position",
      "2 \u2013 + po\u00e4ng",
      "3 \u2013 + V/O/F",
      "4 \u2013 + m\u00e5l & m\u00e5lskillnad",
    ];
    for (var r = 1; r <= 4; r++) {
      var selR = r === currentRows ? " selected" : "";
      html += '<option value="' + r + '"' + selR + '>' + rowLabels[r - 1] + '</option>';
    }
    html += '</select></div>';

    this.shadowRoot.innerHTML = html;

    // ── Bind events ──
    var self = this;

    this.shadowRoot.getElementById("league").addEventListener("change", function (e) {
      var val = e.target.value;
      if (val === "__custom__") {
        self._config.group_url = "";
        delete self._config.entity;
        delete self._config.team;
        self._teams = null;
        self._teamsSlug = null;
        self._fireChanged();
        self._render();
      } else if (val === "") {
        delete self._config.group_url;
        delete self._config.team;
        self._teams = null;
        self._teamsSlug = null;
        self._fireChanged();
        self._render();
      } else {
        self._config.group_url = val;
        delete self._config.entity;
        delete self._config.team;
        self._teams = null;
        self._teamsSlug = null;
        self._fireChanged();
        self._fetchTeams(val);
        self._render();
      }
    });

    var customEl = this.shadowRoot.getElementById("custom_url");
    if (customEl) {
      customEl.addEventListener("change", function (e) {
        var v = e.target.value.trim();
        if (v) {
          self._config.group_url = v;
          delete self._config.entity;
          delete self._config.team;
          self._teams = null;
          self._teamsSlug = null;
          self._fetchTeams(v);
        } else {
          delete self._config.group_url;
        }
        self._fireChanged();
        self._render();
      });
    }

    var teamEl = this.shadowRoot.getElementById("team");
    if (teamEl) {
      teamEl.addEventListener("change", function (e) {
        self._config.team = e.target.value || undefined;
        if (!self._config.team) delete self._config.team;
        self._fireChanged();
      });
    }

    var entityEl = this.shadowRoot.getElementById("entity");
    if (entityEl) {
      entityEl.addEventListener("change", function (e) {
        var v = e.target.value;
        if (v) {
          self._config.entity = v;
          delete self._config.group_url;
          delete self._config.team;
        } else {
          delete self._config.entity;
        }
        self._fireChanged();
        self._render();
      });
    }

    this.shadowRoot.getElementById("image").addEventListener("change", function (e) {
      self._update("image", e.target.value);
    });
    this.shadowRoot.getElementById("subtitle").addEventListener("change", function (e) {
      self._update("subtitle", e.target.value);
    });
    this.shadowRoot.getElementById("rows").addEventListener("change", function (e) {
      self._update("rows", parseInt(e.target.value, 10));
    });
  }

  _update(key, value) {
    if (value === undefined || value === "") {
      delete this._config[key];
    } else {
      this._config[key] = value;
    }
    this._fireChanged();
    this._render();
  }

  _fireChanged() {
    var ev = new CustomEvent("config-changed", { detail: { config: this._config } });
    this.dispatchEvent(ev);
  }
}


/* ── Register elements ─────────────────────────────────────────── */
if (!customElements.get("fotbollstabeller-team-card-editor")) {
  customElements.define("fotbollstabeller-team-card-editor", FotbollstabellerTeamCardEditor);
}
if (!customElements.get("fotbollstabeller-team-card")) {
  customElements.define("fotbollstabeller-team-card", FotbollstabellerTeamCard);
  console.info(
    "%c FOTBOLLSTABELLER-TEAM-CARD %c loaded",
    "color:white;background:#1a6b3a;font-weight:700;padding:2px 6px",
    ""
  );
}

window.customCards = window.customCards || [];
if (!window.customCards.some(function (c) { return c.type === "fotbollstabeller-team-card"; })) {
  window.customCards.push({
    type: "fotbollstabeller-team-card",
    name: "Fotbollstabeller Lag",
    description: "Hero-kort f\u00f6r ett enskilt lag med valfri bild och konfiguerbara detaljer.",
    preview: false,
  });
}
