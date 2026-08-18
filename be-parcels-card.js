class BeParcelsCard extends HTMLElement {
  static CARRIERS = [
    { slug: "bpost", label: "bpost (België)", implemented: true },
    { slug: "dpd", label: "DPD (EU)", implemented: false },
    { slug: "gls", label: "GLS (EU)", implemented: false },
    { slug: "postnl", label: "PostNL (Nederland)", implemented: true },
    { slug: "dhl", label: "DHL (Duitsland/intl.)", implemented: false },
    { slug: "deutsche_post", label: "Deutsche Post (Duitsland)", implemented: false },
    { slug: "la_poste", label: "La Poste / Colissimo (Frankrijk)", implemented: false },
    { slug: "chronopost", label: "Chronopost (Frankrijk)", implemented: false },
    { slug: "mondial_relay", label: "Mondial Relay (FR/BE)", implemented: false },
    { slug: "ups", label: "UPS (internationaal)", implemented: false },
    { slug: "fedex", label: "FedEx (internationaal)", implemented: false },
    { slug: "royal_mail", label: "Royal Mail (VK)", implemented: false },
    { slug: "evri", label: "Evri / Hermes (VK)", implemented: false },
    { slug: "an_post", label: "An Post (Ierland)", implemented: false },
    { slug: "poste_italiane", label: "Poste Italiane (Italië)", implemented: false },
    { slug: "correos", label: "Correos (Spanje)", implemented: false },
    { slug: "ctt", label: "CTT (Portugal)", implemented: false },
    { slug: "austrian_post", label: "Österreichische Post (Oostenrijk)", implemented: false },
    { slug: "postnord", label: "PostNord (SE/DK)", implemented: false },
    { slug: "poczta_polska", label: "Poczta Polska (Polen)", implemented: false },
    { slug: "inpost", label: "InPost (Polen)", implemented: false },
    { slug: "swiss_post", label: "Swiss Post (Zwitserland)", implemented: false },
  ];

  setConfig(config) {
    this._config = config || {};
    this._trackingNumber = "";
    this._carrier = "bpost";
    this._postalCode = "";
    this._error = "";
    this._submitting = false;
    this._pendingDeleteId = null;
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
    // Moet in sync blijven met carriers/*.py requires_postal_code.
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
        const parcelId = st.attributes.parcel_id || "";
        const name = st.attributes.friendly_name || st.entity_id;

        if (parcelId && parcelId === this._pendingDeleteId) {
          return `
            <div class="parcel-row confirm-row" data-entity="${st.entity_id}">
              <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
              <div class="parcel-text">
                <div class="parcel-name">${this._escape(name)} verwijderen?</div>
              </div>
              <button class="confirm-btn confirm-yes" data-parcel-id="${this._escape(parcelId)}">Ja</button>
              <button class="confirm-btn confirm-no">Annuleren</button>
            </div>`;
        }

        const icon = icons[st.state] || icons.unknown;
        const desc = st.attributes.status_omschrijving || st.state;
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
            <button class="delete-btn" data-parcel-id="${this._escape(parcelId)}" title="Pakje verwijderen">
              <ha-icon icon="mdi:close-circle"></ha-icon>
            </button>
          </div>`;
      })
      .join("");

    listEl.querySelectorAll(".parcel-row:not(.confirm-row)").forEach((row) => {
      row.addEventListener("click", () => {
        const evt = new CustomEvent("hass-more-info", {
          detail: { entityId: row.getAttribute("data-entity") },
          bubbles: true,
          composed: true,
        });
        this.dispatchEvent(evt);
      });
    });

    listEl.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation(); // niet de "meer info" van de rij zelf openen
        this._pendingDeleteId = btn.getAttribute("data-parcel-id");
        this._updateParcelList();
      });
    });

    listEl.querySelectorAll(".confirm-yes").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const parcelId = btn.getAttribute("data-parcel-id");
        this._pendingDeleteId = null;
        this._removeParcel(parcelId);
      });
    });

    listEl.querySelectorAll(".confirm-no").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        this._pendingDeleteId = null;
        this._updateParcelList();
      });
    });
  }

  async _removeParcel(parcelId) {
    if (!parcelId || !this._hass) return;
    try {
      await this._hass.callService("be_parcels", "remove_parcel", { parcel_id: parcelId });
    } catch (err) {
      this._error = "Kon pakje niet verwijderen: " + (err && err.message ? err.message : err);
      this._render();
    }
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
        .parcel-text { flex: 1; min-width: 0; }
        .delete-btn {
          background: none; border: none; padding: 4px; cursor: pointer;
          display: flex; align-items: center; flex-shrink: 0;
          border-radius: 50%;
        }
        .delete-btn ha-icon {
          color: var(--error-color, #db4437); --mdc-icon-size: 22px;
        }
        .delete-btn:hover { background: rgba(219, 68, 55, 0.1); }
        .confirm-row { cursor: default; }
        .confirm-row ha-icon { color: var(--warning-color, #f0a020); }
        .confirm-btn {
          border: none; border-radius: 14px; padding: 6px 14px;
          font-size: 13px; cursor: pointer; font-family: inherit; flex-shrink: 0;
        }
        .confirm-yes {
          background: var(--error-color, #db4437); color: #fff; margin-right: 6px;
        }
        .confirm-no {
          background: transparent; color: var(--secondary-text-color);
          border: 1px solid var(--divider-color);
        }
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
          !BeParcelsCard.CARRIERS.find((c) => c.slug === this._carrier)?.implemented
            ? `<div class="warning">Deze vervoerder is nog niet geïmplementeerd — toevoegen zal een foutmelding geven. Zie README.md.</div>`
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
