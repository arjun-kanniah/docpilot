# Research mode evaluation: agent-openai-gpt-6-luna

8 research tasks over 11 chunks; up to 2 rounds of 6 tool calls, 5 passages per search. Graded by claude-opus-5-5.

- Answers: 6 correct, 0 partial, 0 incorrect of 6
- Declined correctly: 2 of 2 tasks the document can't answer
- Evidence: found every needed page in 100% of runs, cited it in 100%
- Key figures stated: 5 of 5
- Effort: 1.2 rounds and 4.6 tool calls per task
- Tokens: agent 88,375 in / 9,528 out ($0.014); grader 8,881 in / 850 out ($0.053)
- Median time per task: 16s

| ID | Category | Task | Verdict | Found evidence | Key figures | Rounds / tools | Grader's reason |
|---|---|---|---|---|---|---|---|
| r01 | multi-page | What does the SkyNode warranty cover, how can I extend it, and what isn't covered? | correct | yes | – | 1 / 4 | The system answer gives every key fact: a 2-year warranty covering manufacturing defects, extension to 3 years by registering in the Aurora app within 30 days, and the exclusions for misuse, unauthorized modification, and lightning strikes. The note about missing claim details does not contradict the reference. |
| r02 | calculation | A school wants 6 SkyNode stations: 4 at the main campus (has Wi-Fi) and 2 at a field site with no Wi-Fi. Students need wind direction and UV readings. Recommend the models and cloud plan, and estimate the first-year cost with the education discount. | correct | yes | all | 2 / 10 | The system answer matches every key fact in the reference: 4 Pro and 2 Max, one Pro plan covering 10 stations, and the 40% education discount on hardware and plan. Its totals ($1,316.40 hardware, $77.40 plan, $1,393.80 first year) are also the same. |
| r03 | calculation | A farm with no Wi-Fi wants soil moisture and leaf wetness readings, a full year of data history and custom alerts. Which model and cloud plan fit, and what is the first-year cost paying annually? | correct | yes | all | 2 / 6 | The system names the SkyNode Max and the Plus plan at $49/year, and gives a $548 total that includes the $499 model price. It matches every key fact in the reference, and its caveats do not contradict it. |
| r04 | conditional | My SkyNode stopped working 2.5 years after I bought it. I registered it in the app the week I bought it and I'm on the Pro cloud plan. Is the repair covered, how long will it take, what do I get meanwhile, and can I phone support? | correct | yes | – | 1 / 4 | The system answer covers the 3-year extended warranty with its exclusions, the 10 business days, the loaner unit and phone support hours, matching the reference. It omits that the $59-plus-parts fee shouldn't apply, but that follows from the repair being covered, and its extra details don't contradict the reference. |
| r05 | calculation | For 3 stations on one account, how much does the Plus plan cost over two years paying monthly versus annually, and how much does annual billing save? | correct | yes | all | 1 / 4 | The system answer matches every key fact in the reference: one account covers the 3 stations, $119.76 monthly, $98 annually, and $21.76 saved. The extra 18.2% figure is accurate and doesn't contradict anything. |
| r06 | multi-page | If my internet goes down for two weeks, which SkyNode models keep all of my readings, and can I still see them during the outage? | correct | yes | – | 1 / 2 | The system answer gives the same storage durations as the reference (7, 30 and 90 days), so it correctly identifies Pro and Max as retaining two weeks and Lite as not. It also states that readings can be viewed locally over the network during the outage, and the cellular backup detail does not contradict the reference. |
| r07 | negative | Who is Aurora Instruments' current CEO, and what was the company's revenue in 2025? | correct | – | – | 1 / 3 | The system correctly abstains, stating the documents don't identify the CEO or 2025 revenue, and only mentions the founders, who do appear in the documents, without claiming either is CEO. |
| r08 | negative | How does the SkyNode Max compare on price and sensors with weather stations from Davis Instruments and Netatmo? | correct | – | – | 1 / 4 | The system correctly gives the SkyNode Max details from the documents and states there is no information on Davis Instruments or Netatmo, so no comparison is made. It invents nothing about the competitors. |
