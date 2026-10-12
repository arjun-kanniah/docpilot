# Evaluation: anthropic-claude-opus-5-5

21 questions over 11 chunks; embeddings BAAI/bge-small-en-v1.5; chunks 1000 chars with 150 overlap; top 6. Graded by claude-opus-5-5.

- Retrieval: expected page in top 6 for 100% (MRR 1.00)
- Answers: 19 correct, 0 partial, 0 incorrect of 19 (score 100%); 0 declined wrongly
- Abstention: declined 2 of 2 questions the document can't answer
- Citations: 100% of answers cite the expected page
- Tokens: answers 48,523 in / 3,946 out ($0.273); grader 19,755 in / 1,549 out ($0.110)
- Median time to a full answer: 2.3s

| ID | Category | Question | Retrieval | Verdict | Cites page | Grader's reason |
|---|---|---|---|---|---|---|
| q01 | factual | When was Aurora Instruments founded? | #1 | correct | yes | The system correctly states the founding year of 2019, which matches the reference. The extra details about location and founders do not contradict it. |
| q02 | factual | Where is Aurora Instruments headquartered? | #1 | correct | yes | The system correctly states the headquarters are in Boulder, Colorado, USA. The extra details about the other offices don't contradict the reference. |
| q03 | factual | Who founded the company? | #1 | correct | yes | The system names both founders, Dr. Elena Varga and Marcus Reed, matching the reference. The extra details do not contradict it. |
| q04 | factual | How many people does Aurora Instruments employ as of 2026? | #1 | correct | yes | The system answer states 112 employees, which matches the reference answer exactly. |
| q05 | factual | How much does the SkyNode Pro cost? | #1 | correct | yes | The system states the SkyNode Pro costs $299, matching the reference; extra details don't contradict it. |
| q06 | factual | How many sensors does the SkyNode Max include? | #1 | correct | yes | The system states the SkyNode Max has 14 sensors, matching the reference; the extra details (5+4+5=14) are consistent and do not contradict it. |
| q07 | numeric | What is the price difference between the cheapest and most expensive SkyNode models? | #1 | correct | yes | The system correctly states the $350 difference, along with the Lite at $149 and the Max at $499. The extra details do not contradict the reference. |
| q08 | comparative | Which SkyNode model should I choose if my location has no Wi-Fi coverage? | #1 | correct | yes | The system recommends the SkyNode Max because of its cellular backup and notes that the Lite and Pro need 2.4 GHz Wi-Fi, which covers every key fact in the reference. The extra details on storage and price don't contradict it. |
| q09 | factual | How accurate are the temperature readings? | #1 | correct | yes | The system states the accuracy as ±0.3°C, which matches the reference answer. The extra mounting advice does not contradict it. |
| q10 | numeric | What is the annual price of the Pro cloud plan, and roughly how much does paying annually save versus monthly? | #1 | correct | yes | The answer gives the $129 annual price and the roughly 18% savings stated in the document. It also correctly computes about 17% for Pro, which the reference accepts. |
| q11 | factual | Which cloud plan do I need for API access and CSV data export? | #1 | correct | yes | The system correctly identifies the Pro plan as the only plan with API access and CSV export, matching the reference; the extra details don't contradict it. |
| q12 | conditional | How long is the warranty if I register my station in the app within 30 days of purchase? | #1 | correct | yes | The system answer states the warranty is extended to 3 years, up from the standard 2 years, which matches the reference. The extra details about coverage don't contradict it. |
| q13 | factual | What is the return window for hardware bought directly from Aurora? | #1 | correct | yes | The system states the 45-day window from delivery, the full refund, and the resalable-condition requirement, matching the reference. The extra details do not contradict it. |
| q14 | procedural | How do I reset a SkyNode station to factory settings? | #1 | correct | yes | The system answer includes every key fact from the reference: hold the hub button for 10 seconds, the light flashes red, and the hub restarts into setup mode. The extra detail about reconfiguring in the Aurora app does not contradict the reference. |
| q15 | factual | What type of batteries do the outdoor sensor modules use? | #1 | correct | yes | The system correctly states two AA lithium batteries, matching the reference; the extra detail about cold-weather performance does not contradict it. |
| q16 | conditional | What discount do schools and non-profits receive? | #1 | correct | yes | The system answer gives the 40% discount on the Plus and Pro plans and on hardware purchases of five or more stations, and notes that verification is required. The application details it adds do not contradict the reference. |
| q17 | comparative | I'm a Pro-plan subscriber whose device needs repair. What do I get while I wait, and how long does a repair usually take? | #1 | correct | yes | The system states both key facts, a loaner unit and a 10-business-day turnaround counted from when Aurora receives the device. Its extra details don't contradict the reference. |
| q18 | comparative | Can I still see my data during an internet outage, and how far back? | #1 | correct | yes | The system answer says yes, notes that the app reads from the hub over the local network, and gives the correct storage durations (7/30/90 days). The extra details about cellular backup do not contradict the reference. |
| q19 | negative | What colors is the SkyNode available in? | – | correct | – | The system correctly states the documents don't specify colors and doesn't guess, only mentioning related specs that are covered. |
| q20 | inference | Does Aurora Instruments sell a home security camera? | #1 | correct | yes | The system answers No and states Aurora sells a single product line, the SkyNode home weather station, which matches the reference. The extra details about the models do not contradict it. |
| q21 | negative | Who is the current CEO of Aurora Instruments? | – | correct | – | The system correctly abstains, saying the sources don't identify the CEO. It mentions only the founders named in the documents and doesn't guess who holds the title. |
