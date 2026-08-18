# Belgian Parcels — Home Assistant custom integration

Track pakjes van Belgische vervoerders in Home Assistant, met zelf gekozen
vervoerder per pakje. Elk pakje wordt een eigen apparaat/sensor met status,
laatste update en (indien bekend) verwachte leverdatum.

⚠️ **Belangrijk om te weten**: geen enkele Belgische vervoerder biedt een
gratis, officiële publieke API voor particulieren. Deze integratie gebruikt
per vervoerder het (niet-officiële) endpoint dat de eigen track&trace-website
van de vervoerder intern gebruikt. Dat werkt in de praktijk, maar kan zonder
aankondiging stoppen als de vervoerder zijn website aanpast. Poll daarom niet
te vaak (standaard: elke 20 minuten) en verwacht dat je af en toe een
carrier-module moet bijwerken.

## Status per vervoerder

| Vervoerder | Status | Opmerking |
|---|---|---|
| bpost | ✅ werkend (best-effort) | Gebruikt `track.bpost.cloud`. Endpoint is community-gereverse-engineerd, niet officieel gedocumenteerd — dus mogelijk (deels) verouderd. Test het na installatie met een echt pakje. |
| DPD | 🚧 skelet | Zie `carriers/dpd.py` — implementeer volgens de stappen hieronder. |
| GLS | 🚧 skelet | Zie `carriers/gls.py` — implementeer volgens de stappen hieronder. |

## Installatie via HACS

1. HACS → drie puntjes rechtsboven → **Custom repositories**.
2. Voeg deze repository-URL toe, categorie **Integration**.
3. Zoek "Belgian Parcels" in HACS en installeer.
4. Herstart Home Assistant.
5. **Instellingen → Apparaten & diensten → Integratie toevoegen → Belgian Parcels.**
6. Kies de vervoerder, vul het trackingnummer in (en postcode indien gevraagd).

Voeg voor elk pakje dat je wil volgen de integratie opnieuw toe — elk pakje
wordt een eigen config-entry/apparaat, zodat je pakjes makkelijk individueel
kan verwijderen zodra ze geleverd zijn.

## Zelf een vervoerder toevoegen (DPD, GLS, PostNL, ...)

De integratie is bewust modulair opgebouwd: elke vervoerder is een losse
Python-klasse in `custom_components/be_parcels/carriers/`. Zo voeg je een
nieuwe vervoerder toe:

1. **Vind het onderliggende JSON-endpoint.**
   - Open de track&trace-pagina van de vervoerder in Chrome met een geldig
     trackingnummer.
   - Open DevTools (F12) → tabblad **Network** → filter op **Fetch/XHR**.
   - Vul het trackingnummer in / laad de pagina en zoek de request die de
     statusgegevens ophaalt (meestal een JSON-response met status, events, ...).
   - Noteer de URL, de nodige parameters (trackingnummer, soms postcode) en
     eventuele headers.
2. **Maak `carriers/<naam>.py` aan**, met een klasse die `ParcelCarrier` uit
   `carriers/base.py` implementeert (zie `bpost.py` als voorbeeld). Map het
   antwoord van de vervoerder naar de genormaliseerde `ParcelStatus`
   (`STATUS_LABEL_CREATED`, `STATUS_IN_TRANSIT`, `STATUS_OUT_FOR_DELIVERY`,
   `STATUS_DELIVERED`, `STATUS_EXCEPTION`, zie `const.py`).
3. **Registreer de klasse** in `carriers/__init__.py` (`CARRIERS` dict).
4. Herstart Home Assistant — de nieuwe vervoerder verschijnt automatisch in
   de dropdown bij het toevoegen van een pakje.

Dit patroon houdt de coordinator, sensor en config_flow volledig
vervoerder-onafhankelijk: je hoeft alleen de carrier-module te schrijven.

## Sensor-attributen

Elke pakje-sensor (`sensor.<naam>`) heeft als state één van:
`label_created`, `in_transit`, `out_for_delivery`, `delivered`, `exception`,
`unknown`, en als attributen o.a. `status_omschrijving`, `laatste_update`,
`verwachte_levering` en vervoerder-specifieke extra info.

## Alternatief: multi-carrier aggregator

Wil je liever niet zelf per vervoerder reverse-engineeren en breekbare
scraping onderhouden? Overweeg dan een betaalde/freemium aggregator-API zoals
17TRACK, TrackingMore of AfterShip als backend: één stabiele API-key, met in
de config flow nog steeds een dropdown waar jij zelf de vervoerder kiest per
pakje. De architectuur hierboven laat dat toe — vervang dan gewoon elke
carrier-module door een aanroep naar diezelfde aggregator met de juiste
carrier-code, in plaats van elk een eigen scraping-endpoint.
