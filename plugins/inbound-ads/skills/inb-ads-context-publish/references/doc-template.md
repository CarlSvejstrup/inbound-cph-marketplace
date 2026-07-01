# AI Context Doc — the canonical format (Dantaxi exemplar)

This is the reference shape every per-client AI Context Google Doc follows. Built from the Dantaxi pilot, 2026-06-10. The body content comes from the client's vault note `## Klientoverblik`; only the top block (Sidst opdateret + H1 + intro + ID table) is templated.

The Doc is uploaded as plain text (auto-converts to a native Google Doc). The `#`/`-`/`|` characters render as literal text in the Doc — that is fine and intended for readable structure.

## Skeleton

```
Sidst opdateret: 2026-06-10

# Dantaxi (dantaxi4x48.com) - AI Context

Operationelt AI-kontekstdokument for Google Ads-teamet og AI-agenter, der skal optimere eller bygge kampagner på denne konto. Genereret fra Inbounds interne klientnote 2026-06-10. Kontekst er tidsløs: konkrete performance-tal hører hjemme i de daterede audits/logs, ikke her.

ID / felt | Værdi
- Google Ads ID: 414-979-1707 (4149791707)
- HubSpot company ID: 7438308806 (dantaxi.dk)
- ClickUp folder ID: 90080593462
- Drive-mappe: https://drive.google.com/drive/folders/1_NWqV1r0S_XNvlUANBiBD3h_LOerWfeC
- Changelog / optimeringslog: https://docs.google.com/document/d/1IYM8B_BD6c7e5hLUMT90GI13yxPP4px5teVIvjFvLro/edit
- Specialist: Caroline Richter, Peter Halling Hilborg, Stine Netman
- Tier: B
- Aftaleform: Retainer
- Valuta: DKK
- Budget/md: 35.000 kr. (vejledende - se budget-pacing-arket for aktuelt tal; arket er kilden til sandhed og kan ændre sig år for år): https://docs.google.com/spreadsheets/d/1_zz92JGdM3zh8PE1xt7AsVCrOUlsQEI3XRbDS2qZljA/edit
- Markeder: DK
- Andre ydelser: SEO (Freja)

## Om virksomheden
<note's Om virksomheden, if present>

## Kontaktpersoner
<note's contacts, if present>

## Kunderelation & noter
<note's Kunderelation, if present>

## Klientoverblik
<the note's ## Klientoverblik VERBATIM — intro italic line + the five ### subsections:
 ### Overblik / ### Hårde rammer (læs før du handler) / ### Mål & konverteringer /
 ### Sådan kører vi den / ### Aktuel status & åbne håndtag>

## Drive-filer (rangeret efter relevans for Google Ads search-optimering)
### Vigtige
- <name>: <full URL>
### Mindre relevante
- <name>: <full URL>
```

## Notes
- Some clients have no standalone Om virksomheden / Kontaktpersoner / Kunderelation sections (the context is folded into Klientoverblik). Omit those headers rather than fabricate — the Doc is then ID table + Klientoverblik + Drive-filer. That is faithful and acceptable.
- The live Dantaxi Doc (the format reference): https://docs.google.com/document/d/18aI3oetgFfDUuA92JG5Uw73ylnBpuxWqP6JW2iu7gNo/edit
- Budget appears twice with the pacing-ark caveat: once in the ID table, once on the Overblik budget bullet (if that bullet exists).
