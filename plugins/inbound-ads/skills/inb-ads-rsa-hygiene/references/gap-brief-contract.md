# Gap-brief-kontrakt (delt med `inb-ads-rsa-copy`)

Dette skill *producerer* gap-brief'et; `inb-ads-rsa-copy` *forbruger* det, i samme form. Denne fil er den fulde kontrakt; SKILL.md Trin 4 viser eksempel-formen inline og peger hertil.

## Hvad gap-brief'et er

En liste over de vinkler der IKKE har en serveret asset per ad group, plus et konkret forslag til hvilke challenger-headlines `inb-ads-rsa-copy` skal skrive for at fylde hullerne. Det er her build→operate→iterate-loopet lukkes: outputtet fra dette skill er inputtet til næste `inb-ads-rsa-copy`-kørsel.

## Transport-medium (løs kobling)

Brugeren kopierer blokken **manuelt** ind i den næste kørsel. Den skrives IKKE til en delt fil, og forbrugeren parser hverken xlsx-fanen eller `analysis.json`. Det holder de to Cowork-kørsler løst koblet. `inb-ads-rsa-hygiene` og `inb-ads-rsa-copy` er søster-skills i samme plugin (`inbound-ads`), så loopet lukker uden krav om at installere flere plugins.

## Formen (kopiér-klar, én linje per ad group)

Ud over `gap_brief`-feltet i `analysis.json` (til arkets Gap-brief-fane), udskriv gap-brief'et i dit svar i denne form:

```
- Ad group: <navn> | Manglende vinkler: <vinkel1>, <vinkel2> | Forslag: <kort tekst>
```

## Vinkel-taksonomi (skal matche forbrugeren)

Vinkel-navnene SKAL være fra taksonomien i `../../shared/headline-craft.md`:

**benefit, trust, urgency, CTA, feature, keyword-led, brand, location, garanti.**

Det er dén liste `inb-ads-rsa-copy` bruger til at forvælge vinklerne direkte. Bruger du et navn udenfor taksonomien, kan forbrugeren ikke matche det. Nævn i outputtet at brugeren kan indsætte blokken i en `inb-ads-rsa-copy`-kørsel for at få challenger-annoncer der fylder hullerne.
