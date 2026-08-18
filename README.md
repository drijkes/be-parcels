# Belgian Parcels — Home Assistant custom integration

Track pakjes van Belgische vervoerders in Home Assistant. Volledig
zelfstandig: de integratie levert zelf een dashboard-kaart mee waarop je een
trackingnummer en vervoerder invult, en toont daar meteen de status van al
je lopende leveringen. Geen handmatige helpers, scripts of extra
HACS-frontendkaarten nodig.

⚠️ **Belangrijk om te weten**: geen enkele Belgische vervoerder biedt een
gratis, officiële publieke API voor particulieren. Deze integratie gebruikt
per vervoerder het (niet-officiële) endpoint dat de eigen track&trace-website
van de vervoerder intern gebruikt. Dat werkt in de praktijk, maar kan zonder
aankondiging stoppen als de vervoerder zijn website aanpast.

## Status per vervoerder

| Vervoerder | Status | Opmerking |
|---|---|---|
| bpost | ✅ werkend (best-effort) | Gebruikt `track.bpost.cloud`. Community-gereverse-engineerd, niet officieel gedocumenteerd. |
| DPD | 🚧 skelet | Zie `carriers/dpd.py`. |
| GLS | 🚧 skelet | Zie `carriers/gls.py`. |

## Installatie via HACS

1. HACS → drie puntjes rechtsboven → **Custom repositories**.
2. Voeg deze repository-URL toe, categorie **Integration**.
3. Zoek "Belgian Parcels" in HACS en installeer.
4. **Herstart Home Assistant.** (Dit is nodig zodat de integratie ook meteen
   haar eigen dashboard-kaart registreert.)
5. **Instellingen → Apparaten & diensten → Integratie toevoegen → Belgian
   Parcels.** Dit maakt éénmalig de hub aan (geen velden om in te vullen).

## De dashboard-kaart toevoegen

De integratie registreert zichzelf automatisch als Lovelace-resource — je
hoeft dus **niets** in te stellen bij Instellingen → Dashboards → Resources.

1. Ga naar het dashboard waar je de kaart wil, klik het potlood (bewerken)
   rechtsboven.
2. Klik **+ Kaart toevoegen** onderaan.
3. Zoek naar **"Belgian Parcels"** in de kaartenlijst (of kies handmatig
   type `Custom: Belgian Parcels` / `custom:be-parcels-card`).
4. Voeg toe en sla het dashboard op.

De kaart toont:
- **"Nieuw pakket toevoegen"**: trackingnummer, vervoerder (dropdown), en
  — enkel zichtbaar wanneer nodig, zoals bij bpost — een postcode-veld.
  Klik "Toevoegen" en het pakje verschijnt meteen in de lijst eronder.
- **"Lopende leveringen"**: elk toegevoegd pakje met status-icoon en
  omschrijving, live bijgewerkt. Klik op een pakje voor het volledige
  "meer info"-paneel (met alle attributen, incl. verwachte leverdatum).

Geen YAML, geen `input_text`/`input_select`-helpers, geen aparte kaarten
zoals Mushroom nodig — dit is puur de meegeleverde `be-parcels-card`.

## Melding wanneer een bezorger onderweg is

Dit zit nu **volledig in de integratie zelf** — geen aparte automation meer
nodig:

1. Ga naar **Instellingen → Apparaten & diensten → Belgian Parcels →
   Configureren**.
2. Vul bij **Notify-service** de naam van je notify-doel in (bv.
   `mobile_app_iphone_van_jan`). Je vindt die naam onder
   Ontwikkelhulpmiddelen → Acties, zoek op "notify" — de service heet
   `notify.<naam>`, hier vul je enkel `<naam>` in.
3. Opslaan. Klaar.

Zodra een pakje overgaat naar status `out_for_delivery` (de bezorger is
onderweg), stuurt de integratie automatisch een melding via die
notify-service — bij elk pakje, zonder verdere configuratie per pakje.

Wil je toch zelf iets bouwen bovenop (bv. een andere melding per
statuswijziging, of een lichtje laten knipperen)? De integratie blijft ook
het event `be_parcels_status_changed` gooien bij élke statuswijziging (niet
enkel `out_for_delivery`), met alle pakje-info in `trigger.event.data` —
bruikbaar in een eigen automation als je verder wil dan de ingebouwde
melding.

## Services (voor eigen automations/scripts)

- **`be_parcels.add_parcel`** — velden: `carrier` (bpost/dpd/gls),
  `tracking_number`, optioneel `postal_code`, optioneel `name`.
- **`be_parcels.remove_parcel`** — veld: `parcel_id` (zichtbaar als
  attribuut op de sensor, of `<vervoerder>_<trackingnummer>` in kleine
  letters).

Deze services zijn ook rechtstreeks bruikbaar buiten de kaart om, bv. vanuit
een automation die een pakje automatisch toevoegt op basis van een
order-bevestigingsmail.

## Zelf een vervoerder toevoegen (DPD, GLS, PostNL, ...)

Elke vervoerder is een losse Python-klasse in
`custom_components/be_parcels/carriers/`:

1. Open de track&trace-pagina van de vervoerder in Chrome met een geldig
   trackingnummer, open DevTools (F12) → **Network** → filter **Fetch/XHR**,
   en zoek de request die de statusgegevens ophaalt (meestal JSON).
2. Maak `carriers/<naam>.py` aan met een klasse die `ParcelCarrier` uit
   `carriers/base.py` implementeert (zie `bpost.py` als voorbeeld).
3. Registreer de klasse in `carriers/__init__.py` (`CARRIERS`-dict).
4. Voeg de nieuwe vervoerder ook toe aan de dropdown in
   `www/be-parcels-card.js` (`<option value="...">`).
5. Herstart Home Assistant.

## Problemen met de dashboard-kaart oplossen

Verschijnt de kaart niet in de kaart-editor? Zet debug-logging aan om de
exacte oorzaak te zien. Voeg toe aan `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.be_parcels: debug
```

Herstart HA en kijk in Instellingen → Systeem → Logs naar regels die
beginnen met `be_parcels:`. Vanaf versie 0.3.0 logt de integratie expliciet
wanneer de kaart-registratie mislukt (bv. ontbrekend bestand, of de
frontend-component was nog niet klaar) — dat stond hiervoor soms onder een
andere loggernaam en was daardoor moeilijk terug te vinden.

## Sensor-attributen

Elke pakje-sensor (`sensor.<naam>`) heeft als state één van:
`label_created`, `in_transit`, `out_for_delivery`, `delivered`, `exception`,
`not_found`, `unknown`, en als attributen o.a. `status_omschrijving`,
`laatste_update`, `verwachte_levering`, `trackingnummer` en `vervoerder`.
