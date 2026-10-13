# Research mode evaluation: agent-gemini-gemini-3.5-flash-lite

8 research tasks over 11 chunks; up to 2 rounds of 6 tool calls, 5 passages per search. Graded by claude-opus-5-5.

- Answers: 5 correct, 0 partial, 1 incorrect of 6
- Declined correctly: 2 of 2 tasks the document can't answer
- Evidence: found every needed page in 100% of runs, cited it in 83%
- Key figures stated: 2 of 5
- Effort: 1.0 rounds and 2.6 tool calls per task
- Tokens: agent 69,142 in / 4,134 out (n/a); grader 9,584 in / 1,067 out ($0.060)
- Median time per task: 4s

| ID | Category | Task | Verdict | Found evidence | Key figures | Rounds / tools | Grader's reason |
|---|---|---|---|---|---|---|---|
| r01 | multi-page | What does the SkyNode warranty cover, how can I extend it, and what isn't covered? | correct | yes | – | 1 / 3 | The system answer matches all key facts: 2-year coverage of manufacturing defects, extension to 3 years free by registering in the Aurora app within 30 days, and the exclusions of misuse, unauthorized modification, and lightning strikes to the hub. |
| r02 | calculation | A school wants 6 SkyNode stations: 4 at the main campus (has Wi-Fi) and 2 at a field site with no Wi-Fi. Students need wind direction and UV readings. Recommend the models and cloud plan, and estimate the first-year cost with the education discount. | correct | yes | all | 1 / 3 | The system recommends 4 Pro and 2 Max with correct reasoning, the Pro cloud plan (up to 10 stations), the 40% discount on hardware and plan, and the correct $1,393.80 total. It omits that Plus allows only 3 stations, but that is a supporting detail and doesn't change the recommendation. |
| r03 | calculation | A farm with no Wi-Fi wants soil moisture and leaf wetness readings, a full year of data history and custom alerts. Which model and cloud plan fit, and what is the first-year cost paying annually? | correct | yes | all | 1 / 2 | The answer identifies the SkyNode Max at $499 and the Plus plan at $49/year, for a first-year total of $548. It also lists the Pro plan as an alternative that meets the requirements, which is accurate and does not contradict the reference. |
| r04 | conditional | My SkyNode stopped working 2.5 years after I bought it. I registered it in the app the week I bought it and I'm on the Pro cloud plan. Is the repair covered, how long will it take, what do I get meanwhile, and can I phone support? | correct | yes | – | 1 / 1 | The system answer covers every key fact in the reference: the warranty extended to 3 years by registration, the 10-business-day turnaround, the loaner unit and Pro-only phone support with hours. It omits the misuse, modification and lightning exclusion caveat, but that is a minor qualifier rather than a contradiction. |
| r05 | calculation | For 3 stations on one account, how much does the Plus plan cost over two years paying monthly versus annually, and how much does annual billing save? | incorrect | yes | missing 119.76, 98, 21.76 | 1 / 2 | The system multiplied by 3 stations, but per the reference one Plus account covers up to 3 stations at a single price. Its totals ($359.28, $294, $65.28 saved) therefore contradict the reference ($119.76, $98, $21.76 saved). |
| r06 | multi-page | If my internet goes down for two weeks, which SkyNode models keep all of my readings, and can I still see them during the outage? | correct | yes | – | 1 / 1 | The system answer correctly states that the Pro (30 days) and Max (90 days) keep two weeks of readings while the Lite (7 days) does not. It also says the app can read directly from the hub over the local network during the outage, matching every key fact. |
| r07 | negative | Who is Aurora Instruments' current CEO, and what was the company's revenue in 2025? | correct | – | – | 1 / 4 | The system correctly states that the documents don't identify the CEO or give 2025 revenue, and it mentions the founders only as related context without claiming either is CEO. It invents nothing. |
| r08 | negative | How does the SkyNode Max compare on price and sensors with weather stations from Davis Instruments and Netatmo? | correct | – | – | 1 / 5 | The system correctly gave the SkyNode Max's documented price and sensor count, then stated that the documents do not cover Davis Instruments or Netatmo, so no comparison could be made. It invented no competitor data. |
