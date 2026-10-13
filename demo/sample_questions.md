# Sample questions

Questions to try, with the answer DocPilot should give and where it comes from. Questions 1-13
assume only `library/aurora_knowledge_base.pdf` is uploaded. The live demo holds the whole
[library](library/), where a newer pricing update changes two answers (marked **library:**).

## Single facts

1. **When was Aurora Instruments founded, and where is it headquartered?**
   2019, in Boulder, Colorado. *(page 1)*
2. **How much does the SkyNode Pro cost and how many sensors does it have?**
   $299, with 9 sensors. *(page 2, from a table)* **Library:** $319 since the 1 September 2026
   pricing update, which supersedes the knowledge base.
3. **What's the return window if I buy hardware directly from Aurora?**
   45 days from delivery, for a full refund. *(page 4)*
4. **How do I reset my SkyNode to factory settings?**
   Hold the hub button for 10 seconds until the status light flashes red. *(page 5)*
5. **Which cloud plan gives me API access and CSV export?**
   Only the Pro plan. *(page 3, from a table)*

## Reasoning across facts

6. **What's the price gap between the cheapest and most expensive SkyNode?**
   $350 ($499 − $149). Needs arithmetic over a table. *(page 2)* **Library:** $380 ($529 − $149).
7. **I have no Wi-Fi where I want to install this. Which model should I get, and why?**
   The SkyNode Max, because it has cellular backup. *(pages 2 and 5)*
8. **My station needs repair and I'm on the Pro plan. What do I get while I wait, and for how long?**
   A loaner unit; repairs typically take 10 business days. *(page 4)*
9. **If I register my station within 30 days, how long is my warranty?**
   3 years instead of the standard 2. *(page 4)*
10. **Can I view my data during an internet outage, and how far back?**
    Yes, from the hub's local storage: 7 days (Lite), 30 days (Pro) or 90 days (Max). *(page 5)*
11. **Does Aurora sell a home security camera?**
    No. Aurora sells a single product line, the SkyNode weather station. *(page 1)*

## Not in the document

The right response to these is to say the document doesn't cover them, not to guess.

12. **What colors does the SkyNode come in?**
    Not stated anywhere.
13. **Who is the current CEO of Aurora Instruments?**
    The founders are named, but no one is given the CEO title.

A short demo that covers all three behaviours: #2 (a cited lookup from a table), #7 (combining
two pages) and #13 (declining to name a CEO the document doesn't mention).

## Across the whole library (Research mode)

These need several of the five documents, and the live demo has them all. Try them in
**Research** mode; the full set with reference answers is
[`agent_eval_multi.json`](agent_eval_multi.json).

14. **A vineyard with no mains power and no Wi-Fi wants soil moisture readings and a full year
    of data history. What equipment and plan do they need, and what will the first two years
    cost?**
    A SkyNode Max ($529) with a SolarKit ($79), the Plus plan ($59 a year), and the cellular
    plan from the second year ($30): $756. *(knowledge base, pricing update, installation
    guide)*
15. **Our school is ordering 4 SkyNode Pro stations. Do we get the hardware discount?**
    Yes: since September 2026 the 40% hardware discount starts at 3 stations, not 5. $765.60.
    *(schools guide, pricing update; the knowledge base has the old rule)*
16. **Does the SkyNode Lite support 5 GHz Wi-Fi?**
    Revision B hubs (serials LB-) do; revision A hubs (LA-) are 2.4 GHz only. *(release notes,
    qualifying the knowledge base)*
17. **What does the SolarKit cost in euros?**
    Not stated: only $79 is given.
