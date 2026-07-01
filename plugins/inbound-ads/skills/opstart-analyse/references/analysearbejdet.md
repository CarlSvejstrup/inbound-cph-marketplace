# Analysearbejdet (Search) — opstarts-tjeklisten

Dette er **den autoritative tjekliste** for opstarts-analysen, ordret fra Inbounds ClickUp
*Opstartscheckliste: Analysearbejdet (Search)* (35 punkter). Indtil ClickUp-MCP er koblet på, ER
denne fil checklisten. Rediger her for at justere ét punkt — skillet læser strukturen herfra.

Hvert punkt har:
- **Punkt** — spørgsmålet ordret fra ClickUp (det eksperten genkender).
- **Sådan tjekkes det** — den konkrete MCP-vej (GAQL eller MCP-værktøj) der besvarer det READ-ONLY.
- **Dom** — hvad der tæller som OK / advarsel (`~`) / kritisk (`✗`). Forankret i Inbounds
  Google Ads-playbook; juster her hvis best practice ændrer sig.

**Lokalisér hvert fund (`evidence`).** Et fund uden adresse er ubrugeligt for specialisten: "der er
en stavefejl" → hvor? Når et punkt peger på noget konkret (en stavefejl, en POOR-annonce, en tom ad
group, en kampagne med forkert indstilling), fang HVOR i et `evidence`-array: **kampagne › ad group
› annonce/asset › den nøjagtige streng**. GAQL'en henter allerede `campaign.name`/`ad_group.name`
til de fleste punkter , brug dem. For tunge moduler (C, G) brug også `details` til dybde og `pointer`
til at henvise videre til `optimering-loop` når en fuld gennemgang sprænger opstartsrapporten
(se SKILL.md Trin 3 c2/c3 for den fulde kontrakt).

**`kind` pr. punkt , lookup vs. judgment (autoritativ liste , kopiér herfra).** Hvert punkt er enten
et **opslag** (agenten læser et faktum , intet for eksperten at efterse → INGEN Ekspert-boks i
tjeklisten) eller en **vurdering** (agentens skøn → eksperten bekræfter → Ekspert-boks). Sæt `kind`
på hvert punkt efter denne liste:
- **`lookup`** (kun Agent-boks): **1-12, 16, 17, 19, 20, 21, 22, 33, 34, 35** , eksistens/optælling
  af udvidelser (1-10), kontoverificering/adgangsroller (11), tomme ad groups (12), konvertering
  tracket/værdisat (16-17), display select / search partners fra (19-20), geo+sprog korrekt (21),
  delt budget (22), device-bud findes (33), hvilke remarketing-lister findes (34), observation-mode
  (35).
- **`judgment`** (begge bokse): **13, 14, 15, 18, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32** , annonce-
  kvalitet/relevans/ad strength (13-15), optimerer mod mål (18), struktur+navngivning (23-24),
  broad-styring/matchtyper/search-term-hygiejne/keyword-dækning/brand-ekskludering/QS-billede
  (25-30), budstrategier+mål-CPA fornuft (31-32).
(Besluttet med Carl 2026-06-10. Grænsen: kan svaret aflæses direkte fra en GAQL-værdi = lookup;
kræver det et fagligt skøn = judgment.)

**Significance-disciplin (samme som optimering-loop):** Inbounds konti er små danske annoncører. På
en frisk opstart er der ofte SLET ingen historik (kontoen er lige overdraget). Døm aldrig en asset
på CTR/CVR ved opstart — opstartsanalysen er en **struktur- og hygiejne-gennemgang**, ikke en
performance-dom. Hvor et punkt kræver data der ikke findes endnu, skriv `Mangler data (ny konto)`
frem for at fabrikere et fund.

**Pausede kampagner er bevidste** (repo-regel) — ekskludér dem fra performance-tællinger, flag dem
ALDRIG som negativt fund. Brug `campaign.status = 'ENABLED'` i tællinger; `!= 'REMOVED'` når du blot
kortlægger strukturen.

> **GAQL-regel (verificeret live 2026-06-10 — overhold ordret):**
> 1. **Ethvert felt i `WHERE` SKAL også stå i `SELECT`.** Filtrerer du på `campaign.status`, skal
>    `campaign.status` med i SELECT (`EXPECTED_REFERENCED_FIELD_IN_SELECT_CLAUSE` ellers). Gælder
>    også `ad_group.status`, `ad_group_ad.status`, `ad_group_criterion.type`, `campaign_criterion.type`,
>    `user_list.membership_status`, `shared_set.type`. Alle queries nedenfor er rettet til dette.
> 2. **Filtrér ikke `campaign_asset.field_type` i WHERE** — `IMAGE` og `LOCATION` er ikke gyldige
>    WHERE-enum-konstanter (`BAD_ENUM_CONSTANT`). Hent ALLE assets og bucket `field_type` i koden
>    bagefter.
> 3. Visse felt-kombinationer kan ikke selectes sammen (`PROHIBITED_FIELD_COMBINATION`), fx
>    `product_link.{data_partner,google_ads,merchant_center}.*`. Hent `product_link.type` alene.

---

## Modul A — Annonceudvidelser (extensions/assets)

MCP: `get_ad_extensions(customer_id)` + GAQL mod `asset` / `campaign_asset` / `asset_set` for typer
og godkendelsesstatus.

GAQL til asset-typer + status (kampagne-niveau) — hent ALLE og bucket `field_type` i koden
(filtrér IKKE field_type i WHERE):
```sql
SELECT campaign.name, campaign.status, asset.type, asset.id,
       campaign_asset.status, campaign_asset.field_type
FROM campaign_asset
WHERE campaign.status = 'ENABLED'
```
(Bemærk: `field_type` rummer SITELINK, CALLOUT, STRUCTURED_SNIPPET, BUSINESS_NAME, LOGO,
LANDSCAPE_LOGO, CALL, LOCATION, PROMOTION m.fl. — tæl pr. type fra rækkerne. Konto-niveau-assets
ligger i `customer_asset` (samme felter, uden `campaign.*`) — kør den separat til punkt 2/4's
"kun konto-niveau"-tjek.)
GAQL til godkendelsesstatus (policy):
```sql
SELECT asset.type, asset.policy_summary.approval_status, asset.policy_summary.review_status
FROM asset
```

| # | Punkt | Sådan tjekkes det | Dom |
|---|---|---|---|
| 1 | **Sitelinks:** min. 4 på hver kampagne | Tæl `field_type = SITELINK` per ENABLED kampagne | OK ≥4 per kampagne · `~` 1-3 · `✗` 0 |
| 2 | **Sitelinks:** kampagne/keyword-specifikke | Er sitelinks sat på kampagne/ad-group-niveau (specifik) vs. kun konto-niveau (generisk)? Tjek `campaign_asset` vs. `customer_asset` | OK hvis kampagne-specifikke findes · `~` kun konto-niveau |
| 3 | **Callouts:** min. 4 på hver kampagne | Tæl `field_type = CALLOUT` per ENABLED kampagne | OK ≥4 · `~` 1-3 · `✗` 0 |
| 4 | **Callouts:** kampagnespecifikke | Samme niveau-tjek som sitelinks | OK kampagne-specifikke · `~` kun konto |
| 5 | **Image extensions:** aktiveret og godkendt | `field_type = IMAGE` findes + `approval_status = APPROVED` | OK aktiveret+godkendt · `~` afventer review · `✗` ingen/afvist |
| 6 | **Business name extension:** tilføjet | `field_type = BUSINESS_NAME` findes | OK findes · `✗` mangler |
| 7 | **Business logo extension:** tilføjet | `field_type = LOGO`/`BUSINESS_LOGO` findes | OK findes · `✗` mangler |
| 8 | **Location extension:** tilføjet (når relevant) | `field_type = LOCATION` findes (kun relevant for fysisk forretning) | OK findes / N/A · `~` mangler men relevant |
| 9 | **Call extension:** tilføjet (når relevant) | `field_type = CALL` findes | OK findes / N/A · `~` mangler men relevant |
| 10 | **Structured snippet extensions:** tilføjet og godkendt | `field_type = STRUCTURED_SNIPPET` findes + godkendt | OK findes+godkendt · `~` afventer · `✗` mangler |

## Modul B — Kontoverificering & adgang

MCP: `get_account_details` + `customer_user_access` GAQL (se Det-praktiske-overlap).

| # | Punkt | Sådan tjekkes det | Dom |
|---|---|---|---|
| 11 | **Få kontoen verificeret** (så firmanavn mv. kan tilføjes) | `get_account_details` — er kontoen aktiv? Business-name-extension kræver verificeret konto; krydstjek mod punkt 6 | OK hvis business-name-asset findes (impliceret verificeret) · `~` ingen business-name (måske uverificeret) |

## Modul C — Annoncetekster (ad copy)

MCP: `get_ad_performance(customer_id)` + GAQL mod `ad_group_ad` + `ad_group` for tomme grupper.

GAQL til ad groups uden aktive annoncer:
```sql
SELECT campaign.status, ad_group.status, ad_group.name, ad_group.id,
       ad_group_ad.status, ad_group_ad.ad.type
FROM ad_group_ad
WHERE campaign.status = 'ENABLED' AND ad_group.status = 'ENABLED'
```
(Grupper der IKKE optræder med en ENABLED `ad_group_ad` = tomme. For den fulde liste af ENABLED
ad groups , kør en `FROM ad_group`-query med samme filtre og diff'e mod dem der har en aktiv annonce.)

GAQL til ad strength + RSA-tekster:
```sql
SELECT campaign.status, ad_group_ad.status, ad_group_ad.ad.type,
       ad_group.name, ad_group_ad.ad.id, ad_group_ad.ad_strength,
       ad_group_ad.ad.responsive_search_ad.headlines,
       ad_group_ad.ad.responsive_search_ad.descriptions
FROM ad_group_ad
WHERE campaign.status = 'ENABLED' AND ad_group_ad.status = 'ENABLED'
  AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
```
(Verificeret live: returnerer `ad_strength` = POOR/AVERAGE/GOOD/EXCELLENT pr. RSA.)

| # | Punkt | Sådan tjekkes det | Dom |
|---|---|---|---|
| 12 | **Annoncegrupper uden aktive annoncer?** | ENABLED ad groups uden en ENABLED `ad_group_ad` | OK 0 tomme · `✗` ≥1 tom gruppe (list dem) |
| 13 | **Velskrevet?** USP'er, ikke generisk, indeholder søgeord, forholder sig specifikt | Læs RSA-headlines/descriptions. Vurdér: nævner USP? generisk floskel? rummer ad-group-temaets søgeord? (kvalitativ — agentens læsning, forankret i hvad de sælger) | OK specifik+USP+søgeord · `~` delvist generisk · `✗` tom/generisk |
| 14 | **Sammenhæng mellem annonce og landingsside?** | Hent `final_urls` fra RSA'erne, scrap siden (Firecrawl), sammenlign annonce-budskab mod side-H1/CTA | OK match · `~` løs sammenhæng · `✗` mismatch |
| 15 | **Ad strength — kan det optimeres?** | `ad_group_ad.ad_strength` per RSA (POOR/AVERAGE/GOOD/EXCELLENT) | OK GOOD/EXCELLENT · `~` AVERAGE · `✗` POOR. (Rapportér som signal, ikke dom — Ad Strength er en Google-heuristik) |

## Modul D — Konverteringer

MCP: GAQL mod `conversion_action` + `customer.conversion_tracking_setting`.

GAQL:
```sql
SELECT conversion_action.name, conversion_action.type, conversion_action.category,
       conversion_action.status, conversion_action.primary_for_goal,
       conversion_action.value_settings.default_value,
       conversion_action.value_settings.always_use_default_value,
       conversion_action.counting_type
FROM conversion_action
WHERE conversion_action.status = 'ENABLED'
```
Tracking-status: `SELECT customer.conversion_tracking_setting.conversion_tracking_status FROM customer`

| # | Punkt | Sådan tjekkes det | Dom |
|---|---|---|---|
| 16 | **Relevante konverteringer tracket?** | Findes ENABLED `conversion_action`-rækker? Dækker de kontoens formål (lead/køb/opkald)? Tracking-status ≠ `NOT_CONVERSION_TRACKED` | OK relevante findes · `~` få/uklare · `✗` ingen tracking |
| 17 | **Konverteringer tildelt en værdi?** | `value_settings.default_value > 0` eller værdi sendes ved konvertering | OK værdisat · `~` nogle uden værdi · `✗` ingen værdier |

## Modul E — Kampagneindstillinger

MCP: GAQL mod `campaign` + `campaign_criterion` (geo/sprog) + `campaign_budget`.

GAQL til kerne-settings:
```sql
SELECT campaign.name, campaign.status, campaign.advertising_channel_type,
       campaign.network_settings.target_search_network,
       campaign.network_settings.target_content_network,
       campaign.network_settings.target_partner_search_network,
       campaign.network_settings.target_google_search,
       campaign.campaign_budget, campaign.bidding_strategy_type
FROM campaign
WHERE campaign.status = 'ENABLED'
```
(Verificeret live: `target_content_network`/`target_partner_search_network` returneres rent pr.
kampagne , det er display-select- og search-partners-tjekkene, punkt 19-20.)
GAQL til geo + sprog:
```sql
SELECT campaign.name, campaign.status, campaign_criterion.type,
       campaign_criterion.location.geo_target_constant,
       campaign_criterion.language.language_constant,
       campaign_criterion.negative
FROM campaign_criterion
WHERE campaign.status = 'ENABLED'
  AND campaign_criterion.type IN ('LOCATION','LANGUAGE')
```

| # | Punkt | Sådan tjekkes det | Dom |
|---|---|---|---|
| 18 | **Optimerer mod alle aktuelle mål?** | Bruger kampagnerne konto- eller kampagne-mål? Krydstjek konverteringerne fra Modul D er knyttet | OK mål dækket · `~` delvist |
| 19 | **Display select slået fra?** | På SEARCH-kampagner: `target_content_network = false` | OK false på alle Search · `✗` true (display select aktivt) |
| 20 | **Google Search partners slået fra?** | `target_partner_search_network = false` | OK false · `~` true (vurdér om bevidst) |
| 21 | **Sprog og landemålretning korrekt?** | Geo-targets matcher kundens marked (DK?), sprog matcher (dansk?). Krydstjek mod klient-notens marked | OK matcher marked · `~` bredt/uklart · `✗` forkert geo/sprog |
| 22 | **Individuelt budget per kampagne?** | Deler flere kampagner samme `campaign_budget` (delt budget)? | OK individuelle · `~` delte budgetter (vurdér om bevidst) |

## Modul F — Struktur & navngivning

MCP: GAQL mod `ad_group` (kampagne→ad-group→keyword-kortlægning).

```sql
SELECT campaign.name, campaign.status, ad_group.name, ad_group.id
FROM ad_group
WHERE campaign.status != 'REMOVED'
ORDER BY campaign.name, ad_group.name
```

| # | Punkt | Sådan tjekkes det | Dom |
|---|---|---|---|
| 23 | **Følger strukturen konventioner / meningsfyldt op?** (STAG/Hagakure/?) | Kortlæg kampagne→ad-group→keyword. Genkend mønster: STAG (single-theme), SKAG (single-keyword), Hagakure (konsolideret). Vurdér om strukturen er konsistent og giver mening | OK genkendelig+konsistent · `~` blandet · `✗` kaotisk |
| 24 | **Brugbar navngivningskonvention implementeret?** | Følger kampagne-/ad-group-navne et mønster (fx `IC \| GSN \| <Kampagne> \| <segment>`)? | OK konsistent konvention · `~` delvist · `✗` ad-hoc navne |

## Modul G — Keywords & søgeord

MCP: `get_keyword_performance` + `get_search_terms_report` + GAQL mod `ad_group_criterion` (matchtyper, brand-ekskludering) + `shared_set` (negativlister).

GAQL til keywords + matchtyper:
```sql
SELECT campaign.status, ad_group_criterion.type, ad_group.name,
       ad_group_criterion.keyword.text,
       ad_group_criterion.keyword.match_type, ad_group_criterion.negative
FROM ad_group_criterion
WHERE campaign.status = 'ENABLED' AND ad_group_criterion.type = 'KEYWORD'
```
GAQL til delte negativlister:
```sql
SELECT shared_set.name, shared_set.type, shared_set.member_count, shared_set.status
FROM shared_set WHERE shared_set.type = 'NEGATIVE_KEYWORDS'
```

| # | Punkt | Sådan tjekkes det | Dom |
|---|---|---|---|
| 25 | **Broad match — brugt kontrolleret?** | Andel `BROAD` keywords. Broad uden tCPA/tROAS + uden stærke negativer = ukontrolleret | OK lav/styret broad · `~` en del broad · `✗` mest broad uden kontrol |
| 26 | **Matchtyper — styr på brugen?** | Fordeling EXACT/PHRASE/BROAD. Er der en bevidst strategi eller blandet tilfældigt? | OK bevidst fordeling · `~` blandet |
| 27 | **Search terms — hygiejne på plads?** | `get_search_terms_report` — er der irrelevante termer der æder spend uden konvertering? (på ny konto evt. tynd data) | OK ryddet/ny konto · `~` lidt spild · `✗` markant spild. Mangler data → noter |
| 28 | **Rammer vi alle relevante keywords?** (søgeordsanalyse-behov?) | Dækker keyword-settet kundens kerne-temaer (fra landingsside/klient-note)? Huller? | OK dækkende · `~` huller (foreslå søgeordsanalyse) |
| 29 | **Brand ekskluderet fra generiske kampagner?** | Findes brand-termer som negativer i non-brand-kampagner? (`ad_group_criterion.negative = true` + brand-tekst, eller delt brand-negativliste) | OK brand ekskluderet · `~` uklart · `✗` brand løber i generisk |
| 30 | **Hvordan ser quality score ud?** | **Verificeret live-run 2026-06-10:** `get_quality_score_audit` afviser `LAST_90_DAYS` (kun `LAST_30_DAYS` virker) OG returnerer device/location-kriterier, ikke keyword-QS. Hent i stedet QS direkte via GAQL: `SELECT ad_group_criterion.keyword.text, ad_group_criterion.quality_info.quality_score, metrics.impressions FROM keyword_view WHERE campaign.status = 'ENABLED' AND segments.date DURING LAST_30_DAYS` (QS kommer som streng , konvertér til tal). Fordeling + impression-vægtet snit. Ny konto: ofte tom/tynd | OK overblik givet · Mangler data (ny konto) noteres |

## Modul H — Bidding

MCP: `campaign.bidding_strategy_type` (fra Modul E-query) + GAQL mod `campaign` for mål-CPA/ROAS.

| # | Punkt | Sådan tjekkes det | Dom |
|---|---|---|---|
| 31 | **Bruger kampagnerne de optimale budstrategier?** | `bidding_strategy_type` per kampagne. Ny konto m. lidt data → Maximize Clicks/Conversions giver mening; moden → tCPA/tROAS. Vurdér mod konverteringsvolumen | OK passer modenhed · `~` diskutabel · `✗` fx tROAS uden konverteringer |
| 32 | **Tjek mål-CPA** | Hvis tCPA-strategi: er target sat realistisk? Sammenlign mod faktisk CPA hvis data findes | OK sat+realistisk · `~` mangler/urealistisk · Mangler data noteres |
| 33 | **Tjek bud på devices — og tilpas evt.** | GAQL `campaign_criterion`/`ad_group_criterion` type `DEVICE` for bud-justeringer. Ny konto: ofte ingen (OK som start) | OK justeret/bevidst neutral · `~` ujusteret men relevant |

## Modul I — Målgrupper & remarketing

MCP: `get_age_gender_performance` + GAQL mod `user_list` + `ad_group_criterion`/`campaign_criterion` type `USER_LIST` (audience attachment + mode).

GAQL til remarketinglister:
```sql
SELECT user_list.name, user_list.type, user_list.size_for_search,
       user_list.membership_life_span, user_list.membership_status
FROM user_list WHERE user_list.membership_status = 'OPEN'
```
(`membership_status` er allerede i SELECT , OK. På en frisk konto er listen ofte tom → `no_data`.)
GAQL til audience-tilknytning + mode:
```sql
SELECT campaign.status, ad_group_criterion.type, campaign.name, ad_group.name,
       ad_group_criterion.user_list.user_list
FROM ad_group_criterion
WHERE ad_group_criterion.type = 'USER_LIST' AND campaign.status = 'ENABLED'
```

| # | Punkt | Sådan tjekkes det | Dom |
|---|---|---|---|
| 34 | **Remarketinglister** (min.: alle besøgende 7, 14, 30, 90, 180, 360, 540 dage + relevante produktsider) | Tæl `user_list`-rækker; matcher de standard-varigheds-trappen? Findes produktside-baserede lister? | OK trappen + produktsider · `~` delvist · `✗` ingen lister |
| 35 | **Audiences i Observation-mode** | Audience-tilknytninger: er de Observation (ikke Targeting), så de ikke indsnævrer? På Search vil man typisk Observation først | OK observation · `~` targeting (vurdér om bevidst) · ingen audiences noteres |

---

## Output: doms-buckets

Skillet samler de 35 punkter i fire buckets på .docx-rapportens forside:
- **OK** (`✓`) — sat op efter best practice.
- **Kan forbedres** (`~`) — fungerer, men tydeligt forbedringspunkt.
- **Kritisk** (`✗`) — fejl/mangel der bør rettes før eller lige efter opstart.
- **Mangler data** — kan ikke vurderes endnu (typisk frisk konto uden historik). Ærligt, ikke et fund.

Hvert punkt på listen får: status-ikon, det ordrette spørgsmål, og en kort dansk konstatering med
det FAKTISKE tal/fund fra MCP'en (fx "3 af 7 kampagner har <4 sitelinks: Brand, Generisk-DK,
Lufthavn"). Aldrig en påstand uden data bag.
