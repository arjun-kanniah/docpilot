# Research mode evaluation: agent-anthropic-claude-haiku-5-5

8 research tasks over 11 chunks; up to 2 rounds of 6 tool calls, 5 passages per search. Graded by claude-opus-5-5.

- Answers: 6 correct, 0 partial, 0 incorrect of 6
- Declined correctly: 2 of 2 tasks the document can't answer
- Evidence: found every needed page in 100% of runs, cited it in 100%
- Key figures stated: 5 of 5
- Effort: 1.4 rounds and 4.6 tool calls per task
- Tokens: agent 165,008 in / 29,310 out ($0.031); grader 13,354 in / 830 out ($0.070)
- Median time per task: 18s

| ID | Category | Task | Verdict | Found evidence | Key figures | Rounds / tools | Grader's reason |
|---|---|---|---|---|---|---|---|
| r01 | multi-page | What does the SkyNode warranty cover, how can I extend it, and what isn't covered? | correct | yes | – | 1 / 2 | The answer states the 2-year warranty for manufacturing defects, the extension to 3 years at no extra cost by registering in the Aurora app within 30 days, and all three exclusions. The extra details do not contradict the reference. |
| r02 | calculation | A school wants 6 SkyNode stations: 4 at the main campus (has Wi-Fi) and 2 at a field site with no Wi-Fi. Students need wind direction and UV readings. Recommend the models and cloud plan, and estimate the first-year cost with the education discount. | correct | yes | all | 1 / 5 | The system recommends 4 Pro + 2 Max with the AuroraLive Pro plan and gives the same hardware ($1,316.40), plan ($77.40), and total ($1,393.80) figures as the reference, with matching justifications. The added caveats do not contradict the reference. |
| r03 | calculation | A farm with no Wi-Fi wants soil moisture and leaf wetness readings, a full year of data history and custom alerts. Which model and cloud plan fit, and what is the first-year cost paying annually? | correct | yes | all | 1 / 3 | The system answer names the SkyNode Max (sensors and cellular backup), the Plus plan at $49 a year with 1 year of history and custom alerts, and a total of $548. All of these match the reference, and the extra details, including a clearly hedged conditional discount, don't contradict it. |
| r04 | conditional | My SkyNode stopped working 2.5 years after I bought it. I registered it in the app the week I bought it and I'm on the Pro cloud plan. Is the repair covered, how long will it take, what do I get meanwhile, and can I phone support? | correct | yes | – | 1 / 6 | The system answer covers every key fact: the 3-year extended warranty from registering within 30 days, the exclusions, that the $59-plus-parts fee shouldn't apply, the 10-business-day turnaround, the loaner for Pro-plan subscribers, and phone support for Pro with the correct hours. Its added caveats don't contradict the reference. |
| r05 | calculation | For 3 stations on one account, how much does the Plus plan cost over two years paying monthly versus annually, and how much does annual billing save? | correct | yes | all | 2 / 4 | The system leads with the correct figures ($119.76 monthly, $98 annually, $21.76 savings), matching the reference. It hedges with an alternative per-station reading but favors the correct reading, which doesn't contradict the reference. |
| r06 | multi-page | If my internet goes down for two weeks, which SkyNode models keep all of my readings, and can I still see them during the outage? | correct | yes | – | 2 / 5 | The system correctly identifies Pro (30 days) and Max (90 days) as keeping two weeks of readings and Lite (7 days) as not. It also correctly says the app can read directly from the hub over the local network during the outage. Its extra caveats don't contradict the reference. |
| r07 | negative | Who is Aurora Instruments' current CEO, and what was the company's revenue in 2025? | correct | – | – | 1 / 5 | The system correctly states that the documents name no current CEO and give no revenue figures, mentioning only related facts such as the founders and without guessing. |
| r08 | negative | How does the SkyNode Max compare on price and sensors with weather stations from Davis Instruments and Netatmo? | correct | – | – | 2 / 7 | The system says the documents have no Davis or Netatmo information and makes no comparison, matching the reference. The SkyNode details it gives are drawn from the documents. |
