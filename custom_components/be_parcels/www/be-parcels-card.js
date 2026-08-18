class BeParcelsCard extends HTMLElement {
  static CARRIERS = [
    { slug: "bpost", label: "bpost (België)", needsKey: false },
    { slug: "dpd", label: "DPD (BE)", needsKey: true },
    { slug: "gls", label: "GLS (EU)", needsKey: true },
    { slug: "postnl", label: "PostNL (Nederland)", needsKey: true },
    { slug: "dhl", label: "DHL Paket (Duitsland)", needsKey: true },
    { slug: "deutsche_post", label: "Deutsche Post (Duitsland)", needsKey: true },
    { slug: "la_poste", label: "La Poste / Colissimo (Frankrijk)", needsKey: true },
    { slug: "chronopost", label: "Chronopost (Frankrijk)", needsKey: true },
    { slug: "mondial_relay", label: "Mondial Relay (Frankrijk)", needsKey: true },
    { slug: "ups", label: "UPS (internationaal)", needsKey: true },
    { slug: "fedex", label: "FedEx (internationaal)", needsKey: true },
    { slug: "royal_mail", label: "Royal Mail (VK)", needsKey: true },
    { slug: "evri", label: "Evri / Hermes (VK)", needsKey: true },
    { slug: "an_post", label: "An Post (Ierland)", needsKey: true },
    { slug: "poste_italiane", label: "Poste Italiane (Italië)", needsKey: true },
    { slug: "correos", label: "Correos (Spanje)", needsKey: true },
    { slug: "ctt", label: "CTT (Portugal)", needsKey: true },
    { slug: "austrian_post", label: "Österreichische Post (Oostenrijk)", needsKey: true },
    { slug: "postnord", label: "PostNord (Zweden)", needsKey: true },
    { slug: "poczta_polska", label: "Poczta Polska (Polen)", needsKey: true },
    { slug: "inpost", label: "InPost (Polen)", needsKey: true },
    { slug: "swiss_post", label: "Swiss Post (Zwitserland)", needsKey: true },
  ];

  setConfig(config) {
    this._config = config || {};
    this._trackingNumber = "";
    this._carrier = "bpost";
    this._postalCode = "";
    this._error = "";
    this._submitting = false;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._updateParcelList();
  }

  getCardSize() {
    return 4;
  }

  _carrierNeedsPostalCode(carrier) {
    // Moet in sync blijven met carriers/*.py requires_postal_code
    // (bpost: eigen implementatie; postnl: 17TRACK vereist land+postcode).
    return carrier === "bpost" || carrier === "postnl";
  }

  _updateParcelList() {
    if (!this._hass) return;
    const parcels = Object.keys(this._hass.states)
      .filter((eid) => eid.startsWith("sensor."))
      .map((eid) => this._hass.states[eid])
      .filter((st) => st.attributes && "trackingnummer" in st.attributes)
      .sort((a, b) =>
        (a.attributes.friendly_name || "").localeCompare(b.attributes.friendly_name || "")
      );
    const listEl = this.shadowRoot && this.shadowRoot.getElementById("parcel-list");
    if (!listEl) return;

    if (parcels.length === 0) {
      listEl.innerHTML = `<div class="empty">Nog geen pakjes toegevoegd.</div>`;
      return;
    }

    const icons = {
      label_created: "mdi:package-variant-closed",
      in_transit: "mdi:truck-delivery-outline",
      out_for_delivery: "mdi:truck-fast-outline",
      delivered: "mdi:package-variant-closed-check",
      exception: "mdi:alert-circle-outline",
      not_found: "mdi:help-circle-outline",
      unknown: "mdi:package-variant",
    };

    listEl.innerHTML = parcels
      .map((st) => {
        const icon = icons[st.state] || icons.unknown;
        const desc = st.attributes.status_omschrijving || st.state;
        const name = st.attributes.friendly_name || st.entity_id;
        const lastUpdate = st.attributes.laatste_update;
        const lastUpdateText = lastUpdate
          ? new Date(lastUpdate).toLocaleString("nl-BE", {
              day: "2-digit",
              month: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
            })
          : null;
        return `
          <div class="parcel-row" data-entity="${st.entity_id}">
            <ha-icon icon="${icon}"></ha-icon>
            <div class="parcel-text">
              <div class="parcel-name">${this._escape(name)}</div>
              <div class="parcel-status">${this._escape(desc)}</div>
              ${
                lastUpdateText
                  ? `<div class="parcel-updated">Laatste update: ${this._escape(lastUpdateText)}</div>`
                  : ""
              }
            </div>
          </div>`;
      })
      .join("");

    listEl.querySelectorAll(".parcel-row").forEach((row) => {
      row.addEventListener("click", () => {
        const evt = new CustomEvent("hass-more-info", {
          detail: { entityId: row.getAttribute("data-entity") },
          bubbles: true,
          composed: true,
        });
        this.dispatchEvent(evt);
      });
    });
  }

  _escape(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  async _submit() {
    if (this._submitting) return;
    this._error = "";

    if (!this._trackingNumber.trim()) {
      this._error = "Vul een trackingnummer in.";
      this._render();
      return;
    }
    if (this._carrierNeedsPostalCode(this._carrier) && !this._postalCode.trim()) {
      this._error = "Deze vervoerder heeft ook de postcode nodig.";
      this._render();
      return;
    }

    this._submitting = true;
    this._render();

    try {
      await this._hass.callService("be_parcels", "add_parcel", {
        carrier: this._carrier,
        tracking_number: this._trackingNumber.trim(),
        postal_code: this._postalCode.trim() || undefined,
      });
      this._trackingNumber = "";
      this._postalCode = "";
      this._error = "";
    } catch (err) {
      this._error = "Kon pakje niet toevoegen: " + (err && err.message ? err.message : err);
    } finally {
      this._submitting = false;
      this._render();
    }
  }

  _render() {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        .header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
        .header ha-icon { color: var(--primary-color); }
        .header span { font-size: 18px; font-weight: 500; }
        .field { margin-bottom: 14px; }
        .field label {
          display: block; font-size: 12px; color: var(--secondary-text-color);
          margin-bottom: 4px;
        }
        .field input, .field select {
          width: 100%; box-sizing: border-box; font-size: 15px;
          background-color: var(--card-background-color, #1c1c1c);
          color: var(--primary-text-color);
          border: none; border-bottom: 1px solid var(--divider-color);
          padding: 6px 2px; outline: none; font-family: inherit;
        }
        .field select option {
          background-color: var(--card-background-color, #1c1c1c);
          color: var(--primary-text-color);
        }
        .field input:focus, .field select:focus { border-bottom: 2px solid var(--primary-color); }
        .error { color: var(--error-color, #db4437); font-size: 13px; margin-bottom: 10px; }
        .warning {
          color: var(--warning-color, #f0a020); font-size: 12px;
          margin: -6px 0 14px 0;
        }
        mwc-button, .btn {
          display: inline-flex; align-items: center; gap: 6px;
          background: var(--primary-color); color: var(--text-primary-color, #fff);
          border: none; border-radius: 20px; padding: 8px 18px;
          font-size: 14px; cursor: pointer; font-family: inherit;
        }
        .btn[disabled] { opacity: 0.5; cursor: default; }
        .divider { height: 1px; background: var(--divider-color); margin: 18px 0; }
        .parcel-row {
          display: flex; align-items: center; gap: 12px; padding: 8px 0;
          cursor: pointer;
        }
        .parcel-row ha-icon { color: var(--secondary-text-color); }
        .parcel-name { font-size: 15px; }
        .parcel-status { font-size: 13px; color: var(--secondary-text-color); }
        .parcel-updated { font-size: 11px; color: var(--disabled-text-color, var(--secondary-text-color)); }
        .empty { font-size: 14px; color: var(--secondary-text-color); padding: 8px 0; }
      </style>
      <ha-card>
        <div class="header">
          <ha-icon icon="mdi:package-variant-plus"></ha-icon>
          <span>Nieuw pakket toevoegen</span>
        </div>

        <div class="field">
          <label>Trackingnummer</label>
          <input id="tracking" type="text" placeholder="Voer trackingnummer in" value="${this._escape(this._trackingNumber)}" />
        </div>

        <div class="field">
          <label>Vervoerder</label>
          <select id="carrier">
            ${BeParcelsCard.CARRIERS.map(
              (c) => `
              <option value="${c.slug}" ${this._carrier === c.slug ? "selected" : ""}>
                ${this._escape(c.label)}
              </option>`
            ).join("")}
          </select>
        </div>
        ${
          BeParcelsCard.CARRIERS.find((c) => c.slug === this._carrier)?.needsKey
            ? `<div class="warning">Vereist een gratis 17TRACK API-key, in te stellen bij Instellingen → Belgian Parcels → Configureren.</div>`
            : ""
        }

        ${
          this._carrierNeedsPostalCode(this._carrier)
            ? `<div class="field">
                 <label>Postcode ontvanger</label>
                 <input id="postal" type="text" placeholder="bv. 1000" value="${this._escape(this._postalCode)}" />
               </div>`
            : ""
        }

        ${this._error ? `<div class="error">${this._escape(this._error)}</div>` : ""}

        <button class="btn" id="submit-btn" ${this._submitting ? "disabled" : ""}>
          <ha-icon icon="mdi:plus-circle"></ha-icon>
          ${this._submitting ? "Bezig..." : "Toevoegen"}
        </button>

        <div class="divider"></div>

        <div class="header">
          <ha-icon icon="mdi:truck-fast-outline"></ha-icon>
          <span>Lopende leveringen</span>
        </div>
        <div id="parcel-list"></div>
      </ha-card>
    `;

    const trackingInput = this.shadowRoot.getElementById("tracking");
    const carrierSelect = this.shadowRoot.getElementById("carrier");
    const postalInput = this.shadowRoot.getElementById("postal");
    const submitBtn = this.shadowRoot.getElementById("submit-btn");

    if (trackingInput) {
      trackingInput.addEventListener("input", (e) => (this._trackingNumber = e.target.value));
    }
    if (postalInput) {
      postalInput.addEventListener("input", (e) => (this._postalCode = e.target.value));
    }
    if (carrierSelect) {
      carrierSelect.addEventListener("change", (e) => {
        this._carrier = e.target.value;
        this._render();
      });
    }
    if (submitBtn) {
      submitBtn.addEventListener("click", () => this._submit());
    }

    this._updateParcelList();
  }
}

customElements.define("be-parcels-card", BeParcelsCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "be-parcels-card",
  name: "Belgian Parcels",
  description: "Voeg pakjes toe en volg lopende leveringen.",
});
