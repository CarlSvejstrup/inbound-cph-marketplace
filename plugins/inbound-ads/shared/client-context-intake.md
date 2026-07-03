# Klient-kontekst-intake (Trin 0)

Kør dette som **allerførste trin** i enhver skill der handler på en navngiven klient — før
research, audit, build, optimering eller eksport. Det er en læsning, så den er **aldrig gated**,
men den er obligatorisk: sådan arver skillen alt Inbound ved om klienten (ID'er, kontakter, hard
rammer, navngivningskonvention, budstrategi-norm, KPI'er, paused-kampagne-intent) i stedet for at
starte blind.

1. **Identificér klienten (kunden).** Tag den klient brugeren nævner (navn, domæne eller konto).
   Mangler den eller er den tvetydig → spørg hvilken klient, før du fortsætter.
2. **Åbn master-klientindekset i Drive** via Drive-connectoren: `search_files` efter Google Doc'en
   `Inbound CPH — Google Ads klient-index (AI Context)` (id
   `1EVC4h1KAhr8EoAGDQxU8gFxCsnv9_n9TJ5uCWVc_KjA`, i "A - Kunder"-mappen). Læs den med
   `read_file_content`. Den mapper hver klient til Google Ads ID, HubSpot ID, ClickUp-mappe,
   **Stage**, Drive-mappe og **AI Context-fil**.
3. **Find klientens række** (match på navn/domæne/Ads-ID) og notér **Stage** (customer / lead /
   opportunity / "ikke tagget"). En Stage ≠ `customer` betyder ingen lukket, betalende konto: vægt
   anbefalinger derefter og antag aldrig en aktiv retainer.
4. **Åbn klientens AI Context-fil** via Drive-linket i indeks-rækken (`read_file_content`) og træk
   den ind i din arbejdskontekst. Den holder den operationelle brief: ID'er, kontakter, hard rammer
   (læs før du handler), mål/KPI'er, navngivningskonvention, how-we-run-it og link til
   changelog/optimeringsloggen (læs også changelog-doc'en hvis opgaven kræver ændringshistorik —
   den holdes separat).
5. **Først derefter** starter du skillens rigtige arbejde og behandler AI Context som ground truth
   for klientfakta.

## Delte-mappe-grupper

For klienter der deler Drive-mappe — **Lime, Retriever/Infomedia, GSGroup, Nemco, Julemærket,
PhoneAlone, DI** — vælg **rækken for det specifikke marked/konto**, ikke den fælles gruppe-række.

## Fallback: ingen række / ingen fil

Har klienten ingen række i indekset eller ingen AI Context-fil endnu: **sig det**, og fortsæt med
den kontekst du kan samle (Drive-mappe, Ads MCP) — men **flag hullet**. Spring aldrig opslaget
stiltiende over.

Kan den linkede `.md`-fil ikke læses ("ineligible to be used in generative AI contexts"), søg i
klientens AI Context-mappe efter Google Doc-versionen (fx `<Klient> - Projektoverblik`) — Docs er
læsbare hvor rå `.md`-uploads ikke er.

---

Fuld rationale i repoets `CLAUDE.md` (sektionen "preload the client's AI Context first"); dette er
den operationelle tjekliste.
