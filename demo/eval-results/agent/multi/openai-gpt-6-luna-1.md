# Research mode evaluation: agent-multi-openai-gpt-6-luna

10 research tasks over 5 documents (23 chunks); up to 2 rounds of 6 tool calls, 5 passages per search. Graded by claude-opus-5-5.

- Answers: 6 correct, 2 partial, 0 incorrect of 8
- Declined correctly: 2 of 2 tasks the document can't answer
- Evidence: found every needed page in 100% of runs, cited it in 88%
- Key figures stated: 5 of 6
- Effort: 1.0 rounds and 3.5 tool calls per task
- Tokens: agent 104,549 in / 12,207 out ($0.017); grader 10,777 in / 1,285 out ($0.069)
- Median time per task: 13s

| ID | Category | Task | Verdict | Found evidence | Key figures | Rounds / tools | Grader's reason |
|---|---|---|---|---|---|---|---|
| m01 | conflict | How much does a SkyNode Pro cost, and how much is the Plus cloud plan per year? | correct | yes | all | 1 / 3 | The system gives the current prices from the reference, $319 for the SkyNode Pro and $59/year for the Plus plan. It leaves out the earlier prices and the monthly price, but those are context rather than contradictions. |
| m02 | calculation | A school wants 6 SkyNode stations: 4 at the main campus (has Wi-Fi) and 2 at a field site with no Wi-Fi. Students need wind direction and UV readings. Recommend the models and cloud plan, and estimate the first-year cost with the education discount. | correct | yes | all | 1 / 6 | The answer matches the reference on models (4 Pro, 2 Max), the Pro cloud plan, hardware of $2,334 discounted to $1,400.40, the plan at $77.40, and the total of $1,477.80. It does not say why Plus is ruled out (its 4-station limit), but the plan choice and cost are correct and the extra details don't contradict the reference. |
| m03 | calculation | A vineyard with no mains power and no Wi-Fi wants soil moisture readings and a full year of data history. What equipment and plan do they need, and what will the first two years cost? | partial | yes | missing 756 | 1 / 5 | The equipment, plan and structure match the reference, but the Max is priced at $499 instead of $529, so the two-year total of $726 is wrong (the reference gives $756). |
| m04 | conditional | Can I run a SkyNode Lite on the SolarKit at a site without mains power? | partial | yes | – | 1 / 3 | The system correctly says no, because the Lite uses a different connector and needs mains power. It omits that the SolarKit fits the Pro and Max hubs, and so misses the recommended alternative of a Pro or Max with the SolarKit. |
| m05 | conflict | Does the SkyNode Lite support 5 GHz Wi-Fi? | correct | yes | – | 1 / 2 | The answer correctly says revision B (LB- serials) supports 5 GHz and revision A (LA- serials) is 2.4 GHz only, which covers the key distinction. It omits minor details (the January 2026 shipping date and the firmware update) but contradicts nothing. |
| m06 | conditional | We're a Title I school and want 2 weather stations. What can we get free, and what discount applies if we buy them instead? | correct | yes | – | 1 / 4 | The system states the free option (up to 2 SkyNode Lite stations, Feb 1 to Mar 31) and the 15% discount for buying 1 or 2 stations, which covers all the key facts. The extra details, including the $253.30 total (2 × $149 × 0.85), are consistent and don't contradict the reference. |
| m07 | conflict | Our school is ordering 4 SkyNode Pro stations. Do we get the hardware discount, and what will the stations cost? | correct | yes | all | 1 / 3 | The system confirms that 4 stations qualify under the 3-or-more rule and gives $319 each with a discounted total of $765.60. The $1,276 list price is implied by the stated savings ($765.60 + $510.40), so all key facts are covered. |
| m08 | calculation | After the first year, what does cellular data for a SkyNode Max cost, and which billing option is cheaper? | correct | yes | all | 1 / 2 | The system answer gives $3/month or $30/year after the first 12 months and identifies annual billing as cheaper ($30 vs $36), matching all key facts. The 1 GB per month detail is consistent with the reference. |
| m09 | negative | What does the SolarKit cost in euros, and is it sold in the EU? | correct | – | – | 1 / 3 | The system correctly states only the $79 USD price and says the euro price and EU availability are not given, without guessing at either. |
| m10 | negative | When is the SkyNode Ultra launching, and what will it cost? | correct | – | – | 1 / 4 | The system correctly abstained, stating the sources don't mention the SkyNode Ultra. It noted only the Lite, Pro and Max models, without inventing a launch date or price. |
