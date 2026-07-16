# Output-format-kontrakt: hvordan briefet præsenteres

Denne fil styrer **kun præsentationen af Output #1 (projektleder-overblikket)**. Den rører ikke data-fan-out'en (Trin 0.5-2), diff-klassifikationen (Trin 4), eller den gatede skrivning (Trin 6) — de er format-uafhængige og kører altid ens. Briefet kan leveres i to formater, valgt af brugeren i Trin 0:

1. **Rapport (side)** — en selvstændig, scanbar HTML-side publiceret som en privat **claude.ai-artifact** via `Artifact`-værktøjet. Default. Genkendelig Inbound-husstil.
2. **Rapport (i chatten)** — samme indhold og samme zone-struktur, skrevet som struktureret Markdown direkte i chat-svaret.

Begge formater bruger **den samme zone-struktur** (nedenfor). Kun skindet skifter. Det er bevidst: strukturen er der hele værdien ligger, ikke i om det er en side eller tekst.

**Hard regel — brief vs. gate er to dokumenter.** Uanset format er `## Klientoverblik`-briefet (læse-tilstand) altid adskilt fra kontekst-opdaterings-diffen (beslut-og-skriv-tilstand). I side-formatet er diffen en tydeligt afgrænset sektion nederst med et "Skriver ikke automatisk"-badge. I chat-formatet kommer diffen efter briefet under sin egen overskrift. Diffens godkendelse + `findAndReplaceInDoc`-skrivning sker ALTID conversationelt i chatten (Trin 5-6) — en artifact kan ikke godkende eller skrive noget, og human-in-the-loop på writes er en hard Inbound-regel.

**Sprog:** dansk medmindre brugeren skriver engelsk. Real Æ Ø Å, aldrig ASCII (aa/oe/ae) — gælder også al tekst i HTML-siden; grep før publicering.

---

## Zone-strukturen (fælles for begge formater)

Rækkefølgen er læse-prioritet (BLUF-doktrin: konklusion + det brugeren skal handle på først, status og kontekst derefter, kildeteknik til sidst). Forskningsgrundlaget: BLUF/inverted-pyramid, NN/g layer-cake-scanning (79% scanner, læser ikke), gov.uk-reporting (requests i åbningen), consulting-onepagers (så-hvad + ejer/deadline).

1. **BLUF / header.** Klient-navn + en-linjes hvem-de-er + status-chip (relationstilstand) + en "Kort sagt"-verdikt-blok (2-4 sætninger: hvad er situationen, hvad kræver din opmærksomhed) + en meta-linje (nyt-siden-dato, as-of, tier, retainer, kontakt, marked). Hvis brugeren kun læser dette, kan de gå ind til mødet.
2. **Hvad kræver handling.** ØVERST, ikke i prosa. Tre adskilte grupper, hver som en lille tabel/kort-kolonne:
   - **Beslutning nødvendig** — åbne forks brugeren skal afgøre. Felter: beslutning | kontekst | anbefalet valg.
   - **Handlinger** — konkrete opgaver. Felter: opgave | ejer (ét navn) | mål/deadline eller afhængighed | status-pill.
   - **Venter på** — parkeret hos andre. Felter: hvad | fra hvem | siden | status.
   Enhver handling uden ejer er status, ikke en handling. Buried actions bliver overset — de skal have deres egen visuelle zone.
3. **Hvad er nyt** (siden watermark-datoen). Per kilde (HubSpot, Google Ads, Drive, Rapporter), hver med en freshness-pill (ren / delvis / ingen nyere). Hvert fund parres med et **"Betyder:"** (så-hvad + talepunkt), ikke råt faktum. Rapport-kilden viser nyeste deck eller "ingen nyere rapport" pænt.
4. **Hvem de er & hvor vi står.** Komprimeret durable kontekst fra `## Klientoverblik`: rammer/setup (tier, budget, marked, mål, hårde regler), team/bemanding, kendte åbne håndtag.
5. **Forslag til AI-kontekst-opdatering (gaten).** Diff-tabellen (# | Type | Sektion | Foreslået | Kilde) med "Skriver ikke automatisk"-badge. Kun visning her; godkendelse sker i chatten (Trin 5).
6. **Datagrundlag & kilder.** Footer. Per-kilde tilstand + freshness-stamp + evt. fejl. Det er HER "delvis", "watermark", "hs_createdate", per-kilde as-of hører til — ude af selve briefet. En fejlet/delvis kilde vises eksplicit, aldrig et tavst drop.

**Status-encoding (begge formater):** brug ikon + ord + farve sammen, aldrig farve alene (WCAG 1.4.1). Tilstande: ren/ok (grøn), delvis/i-gang (gul/amber), risiko (rød), afventer/info (blå), neutral/ubesvaret (grå). I chat-formatet: emoji-pills (🟢 🟠 🔵 ⚪) + ord.

---

## Format A: Rapport (side) — claude.ai-artifact i Inbound-husstil

### Levering

1. Skriv den udfyldte HTML til en `.html`-fil i scratchpad (fx `<scratchpad>/<klient-slug>-brief.html`).
2. Publicér med `Artifact`-værktøjet (`file_path` = den fil). Titlen sættes via `<title>` i HTML'en; sæt en `description` og en `favicon` (fx 🧭).
3. Giv brugeren linket i chat-svaret med en kort en-linjes intro ("Her er briefet på <klient> — åbn og scan"). Læg derefter **diffen + godkendelses-spørgsmålet i chatten** (Trin 4-5), IKKE kun på siden.

### Husstil (låst — Inbound-designsystemet)

Samme palet som `../inb-ads-account-audit/template.html`, men som en **scanbar scroll-side, IKKE et fullscreen slide-deck**. Ingen `overflow:hidden`, ingen `100vh`-slides, ingen slide-navigation.

- Palet: `--bg:#001B2E` (navy), `--panel:#06263B`, `--accent:#F16C56` (koral), tekst hvid med mute/dim-varianter. Status: grøn `#3DB069`, gul `#F5C842`, rød `#E05252`, info-blå `#5AA9E6`.
- Font: **Manrope** (husfonten). CSP i artifacts blokerer font-CDN'er, så Manrope SKAL inlines som `@font-face` data-URI — link ALDRIG `fonts.googleapis.com` (det fejler tavst i en artifact). Se "Font-indlejring" nedenfor.
- Ambient husmønster (de diagonale linjer) som `position:fixed` baggrund, non-scrolling. Koral venstre-kant-accent på BLUF-blokken. Manrope 800 til overskrifter, tabular-nums til datoer/tal.
- Single-theme (committed mørk husstil — bevidst, ikke en udeladelse). Ingen lys-tema-tokens nødvendige.

### Font-indlejring (Manrope som data-URI)

Artifact-CSP'en tillader ikke eksterne fonte. Hent Manrope én gang og inlin den subsat som variabel WOFF:

```bash
# hent variabel Manrope (OFL) og subset med bevaret wght-akse (dækker 400-800 fra én fil)
curl -sSL -o manrope.ttf "https://github.com/google/fonts/raw/main/ofl/manrope/Manrope%5Bwght%5D.ttf"
UNI="U+0020-007E,U+00A0,U+00C6,U+00D8,U+00C5,U+00E6,U+00F8,U+00E5,U+2013,U+2014,U+2018,U+2019,U+201C,U+201D,U+201A,U+00AB,U+00BB,U+2022,U+2026,U+00B7,U+2192,U+2190,U+2194,U+2265,U+2264,U+00D7,U+2713,U+25CF,U+00A9,U+2011"
python3 -m fontTools.subset manrope.ttf --unicodes="$UNI" --layout-features='kern,liga,calt,tnum,ss01' --flavor=woff --output-file=manrope-var.woff --no-hinting
# byg @font-face med font-weight:400 800 og format("woff-variations"); base64-encode manrope-var.woff ind i src:url(data:font/woff;base64,...)
```

Læg det resulterende `@font-face`-blok øverst i `<style>`. `font-family:"Manrope";font-weight:400 800;src:url(data:font/woff;base64,<...>) format("woff-variations")`. Kræver `fontTools` (findes i miljøet; ingen brotli, så WOFF ikke WOFF2). En færdig referenceside med Manrope allerede indlejret ligger i `references/brief-template.html` — kopiér den, og erstat kun indholdet (behold `<style>` + font-blokken uændret).

### Struktur

Følg `references/brief-template.html` som skabelon: den ER zone-strukturen ovenfor, udfyldt med et eksempel (DBI). Erstat teksten, behold CSS + font. Byg med rigtige data; ingen lorem, ingen opfundne tal. Udelad en tom zone pænt (fx "ingen nyere rapport") frem for at skrive en stub.

---

## Format B: Rapport (i chatten) — struktureret Markdown

Samme zoner, som Markdown direkte i chat-svaret. Denne variant er ofte "god nok som den er" og kræver ingen infrastruktur. Skabelon (udfyld, behold rækkefølgen):

```markdown
# <Klient> — <fuldt navn> · Projektleder-brief

`<relationstilstand>` · <tier> · <retainer> · Kontakt: <navn> · Marked <marked>
**Nyt siden <dato> · as-of <dato>**

> **Kort sagt.** <2-4 sætninger: situation + hvad kræver din opmærksomhed.>

## Hvad kræver handling · <N handlinger · N beslutning · N venter>

**Beslutning nødvendig**
| # | Beslutning | Kontekst | Anbefalet |
| ... |

**Handlinger**
| # | Opgave | Ejer | Mål / afh. | Status |
| ... |   (Status som emoji-pill + ord: 🟠 I gang, 🔵 Afventer, osv.)

**Venter på**
| # | Hvad | Fra | Siden | Status |
| ... |

## Hvad er nyt · siden <dato>

### <Kilde> — <🟢 ren / 🟠 delvis / ⚪ ingen nyere> (<detalje>)
- **<dato> · <fund>** → *Betyder:* <så-hvad + talepunkt.>

(gentag per kilde: HubSpot, Google Ads, Drive, Rapporter)

## Hvem de er & hvor vi står
**Rammer & setup** — engagement, marked, mål, hårde regler (bullets).
**Team & bemanding** — navne · roller.
**Kendte åbne håndtag** — bullets.

## 🔒 Forslag til AI-kontekst-opdatering — skriver ikke automatisk
> Separat trin. Skrives kun efter din eksplicitte godkendelse, punkt for punkt.
| # | Type | Sektion | Foreslået | Kilde |
| ... |
→ *Godkend:* «tilføj alle» · «vælg 1,3,4» · eller «nej».

### Datagrundlag & kilder
| Kilde | Tilstand | Note | As-of |
| ... |
<watermark-fodnote: Sidst opdateret-gulv, Seneste rapport læst, Ads 29-dages loft.>
```

---

## Fælles regler for begge formater

- **Så-hvad, ikke dump.** Hvert nyt-fund parres med sin implikation. Rå fakta uden fortolkning tvinger læseren til at gøre arbejdet.
- **3-5 tal-reglen.** Vis kun tal der mapper til klientens mål; undgå data-dump. Øjebliks-performance hører i rapporten, ikke i briefet.
- **Ejer + deadline er ufravigeligt** på handlinger. Ingen fælles-ejerskab.
- **Tidsløs-vagt** (fra `diff-classification.md`) gælder stadig alt der ryger i gaten.
- **Pausede kampagner er bevidste** — aldrig flag som negativt fund. **30-dages Ads-loft** — tomt vindue = "ingen ændringer", ikke "inaktiv".
- Ingen emojis i kroppen af side-formatet (status-pills bruger SVG-ikoner der). Emoji-pills er kun til chat-formatet. Ingen tankestreger (komma/kolon i stedet).
- Marker manglende/utroværdige data i footeren; opfind aldrig kontekst.
