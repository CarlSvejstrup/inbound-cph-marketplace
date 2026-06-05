# "Generelle negative søgeord" — EXAMPLE SNAPSHOT (NOT canonical)

> WARNING: This is a documented EXAMPLE only. The canonical source is the live MCC shared
> negative keyword list. Pull it live every run:
> ```
> SELECT shared_criterion.keyword.text, shared_criterion.keyword.match_type
> FROM shared_criterion WHERE shared_set.id = 6688642473
> ```
> against customer_id `1138360630` (Inbound CPH Clients MCC). The agency edits the master
> list; this snapshot WILL drift. Use it only as a fallback if the MCC is unreachable in a
> run, and say so in the output.

**Snapshot taken 2026-06-03** — shared_set `6688642473`, 277 members
(242 broad / 34 phrase / 1 exact). Use as the "already-covered" set so generation does not
re-propose these as novel client-specific negatives.

## Intent clusters (what the list already covers)

- **Info-seekers / research:** guide, guider, guides, manual, manualer, tutorial, wiki,
  wikipedia, faq, artikel, artikler, blog, blogs, brugsanvisning, vejledning, brugervejledning,
  hvordan, hvad er, hvem, information, inspiration, bog, bøger, user guide (phrase)
- **Job-seekers:** job, jobs, jobnet, jobindex, karriere, ansøgning, ansøgninger, praktik,
  praktikplads, lærling, læreplads, arbejde, deltid, fuldtid, ansat, ansæt, hyrer, løn, resume,
  "arbejde hos/med/som/i" (phrase), "job hos/i/med/som" (phrase)
- **Price / free / cheap:** gratis, free, gul og gratis (phrase), gul & gratis (phrase),
  blå avis (phrase), loppemarked, auktion, auktioner, prissammenligning, pricerunner
- **Used / rental / swap:** brugt, brugte, second hand, genbrug, antik, antikvitet, refurbished,
  lease, leje, lej, udlejning, udlej, bytte, byttes, ombytte, dba, dba.dk
- **Complaints / fraud / quality:** klage, klag, anmeldelse, anmeldelser, bedømmelse, dårlig,
  dårligt, dårlig kvalitet (phrase), elendig, svindel, svindler, snyd, snydt, bedrag, bedraget,
  reklamation, retur, returnering
- **Competitors / retailers:** ikea, bauhaus, føtex, bilka, illum, magasin, ilva, jysk-style
  retail names
- **Education / courses (when not the offering):** kursus i/med (phrase), kurser i/med (phrase),
  uddannelse med/som/til (phrase), skole, skoler, klasse, universitet, træning, lære
- **Malware / piracy:** virus, vira, virusser, antivirus, trojan, trojansk, malware, spyware,
  hijack, torrent, torrents
- **Legal / health / misc:** lov, lovgivning, regel, regler, jura, læge, læger, hospital,
  sygdom, klinik, politi, tyveri, reservedele, reparation
- **Small Danish town names** (likely geo/location negatives): Nakskov, Skagen, Næstved, Lejre,
  Rørvig, Fejø, Bevtoft, Regstrup, Engesvang, Beder, Skals, Dybvad, Klippinge, Boeslunde,
  Errindlev, Trustrup, Bedsted Thy, Sporup, Bække, Blommenslyst, Viuf, Lem, Vils, Gram

## How to use this in generation

Read these clusters as "do not regenerate." The skill's job is to find what is MISSING for
THIS client — e.g. a B2B SaaS client might need its competitors' brand names added; a local
service might need adjacent-but-irrelevant service terms blocked. Generate only those gaps as
client-specific additions; the 277 are handled by attaching the shared list.
