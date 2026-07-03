# GAQL-hjælpespørgsmål (account-audit)

De eksakte GAQL-spørgsmål `ads-analyst`-agenten kører for de moduler hvor MCP-værktøjerne suppleres med rå GAQL via `run_custom_gaql`. SKILL.md § 3 lister hvilket modul der bruger hvilket værktøj, denne fil holder de nøjagtige queries. Alt er read-only (SELECT). Skriv aldrig til kontoen herfra.

## Kontostruktur (struktur- og brand-split-detektion)

```sql
SELECT campaign.name, campaign.status, campaign.advertising_channel_type,
       campaign.bidding_strategy_type, ad_group.name
FROM ad_group
WHERE campaign.status != 'REMOVED'
ORDER BY campaign.name
```

Brug til at udlede STAG/SKAG/Hagakure-mønstre, brand vs. non-brand-opdeling, og navngivningskonsistens på tværs af kampagner og ad groups.

## Konverteringshandlinger (tracking & bid management)

```sql
SELECT conversion_action.name, conversion_action.category,
       conversion_action.counting_type, conversion_action.value_settings.default_value,
       conversion_action.status
FROM conversion_action
WHERE conversion_action.status = 'ENABLED'
```

Bruges til at se om konverteringer er kategoriseret, opdelt i primary/secondary, og om de har tildelte værdier.

## Delte negativlister (keywords & negative keywords)

```sql
SELECT shared_set.name, shared_set.type, shared_set.member_count
FROM shared_set
WHERE shared_set.type = 'NEGATIVE_KEYWORDS'
```

## Audience-lister (målretning & audiences)

```sql
SELECT user_list.name, user_list.size_for_search,
       user_list.type, user_list.membership_status
FROM user_list
WHERE user_list.membership_status = 'OPEN'
```

## Øvrige moduler

For de resterende `run_custom_gaql`-moduler i SKILL.md § 3 (Indstillinger: search partners / display select / geo / sprog / DSA / IP-ekskluderinger / ACA-flag; Feed & merchant center: shopping campaigns / merchant center-link / feed-status; pMax: asset groups / audience signals / search themes / brand exclusions / asset-typer; Display & Demand Gen: placement-ekskluderinger / kreativtyper; YouTube: ad formats / frequency capping / retargeting-lister) skriver agenten den relevante `SELECT` mod det passende resource ud fra modulets tjekliste i SKILL.md § 6.2. Hold dem read-only og filtrér altid `campaign.status != 'REMOVED'` hvor kampagne-grain er relevant.

## Quality score

Quality score trækkes IKKE med rå GAQL her. Brug MCP-værktøjet `get_quality_score_audit` efter den delte kontrakt i `../../shared/quality-score-pull.md` (rå `LAST_90_DAYS` er et ugyldigt GAQL-literal — det er netop derfor QS går gennem tool'et, ikke gennem denne fil).
