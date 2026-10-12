# Evaluation: openai-gpt-6.1-sol

21 questions over 11 chunks; embeddings BAAI/bge-small-en-v1.5; chunks 1000 chars with 150 overlap; top 6. Graded by claude-opus-5-5.

- Retrieval: expected page in top 6 for 100% (MRR 1.00)
- Answers: 19 correct, 0 partial, 0 incorrect of 19 (score 100%); 0 declined wrongly
- Abstention: declined 2 of 2 questions the document can't answer
- Citations: 100% of answers cite the expected page
- Tokens: answers 30,501 in / 790 out ($0.069); grader 18,058 in / 1,451 out ($0.101)
- Median time to a full answer: 1.9s

| ID | Category | Question | Retrieval | Verdict | Cites page | Grader's reason |
|---|---|---|---|---|---|---|
| q01 | factual | When was Aurora Instruments founded? | #1 | correct | yes | The system answer states the founding year 2019, matching the reference answer exactly. |
| q02 | factual | Where is Aurora Instruments headquartered? | #1 | correct | yes | The system answer matches the reference: Boulder, Colorado, USA. |
| q03 | factual | Who founded the company? | #1 | correct | yes | The system names both founders, Dr. Elena Varga and Marcus Reed, matching the reference. The extra details (company name, 2019) don't contradict it. |
| q04 | factual | How many people does Aurora Instruments employ as of 2026? | #1 | correct | yes | The system answer states 112 people, matching the reference answer exactly. |
| q05 | factual | How much does the SkyNode Pro cost? | #1 | correct | yes | The system states the SkyNode Pro costs $299, matching the reference answer; adding 'USD' doesn't contradict it. |
| q06 | factual | How many sensors does the SkyNode Max include? | #1 | correct | yes | The system answer states 14 sensors, matching the reference answer exactly. |
| q07 | numeric | What is the price difference between the cheapest and most expensive SkyNode models? | #1 | correct | yes | The system answer gives the $350 difference and correctly identifies the SkyNode Max at $499 and the SkyNode Lite at $149, matching the reference. |
| q08 | comparative | Which SkyNode model should I choose if my location has no Wi-Fi coverage? | #1 | correct | yes | The system answer recommends the SkyNode Max for its cellular backup and notes that the Lite and Pro need Wi-Fi to sync, which covers the reference's key facts. It omits the 2.4 GHz detail, which is minor, and the extra note about local logging does not contradict the reference. |
| q09 | factual | How accurate are the temperature readings? | #1 | correct | yes | The system states ±0.3°C accuracy, matching the reference; the extra mounting advice does not contradict it. |
| q10 | numeric | What is the annual price of the Pro cloud plan, and roughly how much does paying annually save versus monthly? | #1 | correct | yes | The system correctly states the $129 annual price and the roughly 18% savings, matching the reference. |
| q11 | factual | Which cloud plan do I need for API access and CSV data export? | #1 | correct | yes | The system correctly identifies the Pro plan as the one that includes API access and CSV export. The extra pricing and trial details do not contradict the reference. |
| q12 | conditional | How long is the warranty if I register my station in the app within 30 days of purchase? | #1 | correct | yes | The system correctly states the warranty is extended to 3 years when registered within 30 days. Omitting the standard 2-year baseline is a minor detail that doesn't change the key fact. |
| q13 | factual | What is the return window for hardware bought directly from Aurora? | #1 | correct | yes | The system answer states the 45-day window from delivery, full refund, and resalable condition, matching all key facts in the reference. |
| q14 | procedural | How do I reset a SkyNode station to factory settings? | #1 | correct | yes | The answer gives every key fact: hold the hub button for 10 seconds until the light flashes red, and the hub restarts into setup mode. The extra detail about reconfiguring through the app does not contradict the reference. |
| q15 | factual | What type of batteries do the outdoor sensor modules use? | #1 | correct | yes | The system answer matches the reference exactly: two AA lithium batteries. |
| q16 | conditional | What discount do schools and non-profits receive? | #1 | correct | yes | The system answer states the 40% discount on Plus and Pro plans and on hardware purchases of five or more stations, with verification required. This matches all key facts, and the extra application details don't contradict the reference. |
| q17 | comparative | I'm a Pro-plan subscriber whose device needs repair. What do I get while I wait, and how long does a repair usually take? | #1 | correct | yes | The system answer states both key facts: Pro-plan subscribers get a loaner unit, and repairs take 10 business days from when Aurora receives the device. This matches the reference. |
| q18 | comparative | Can I still see my data during an internet outage, and how far back? | #1 | correct | yes | The system answer gives every key fact: the app reads from the hub over the local network, with local storage of 7, 30 and 90 days by tier. The extra cellular backup detail doesn't contradict the reference. |
| q19 | negative | What colors is the SkyNode available in? | – | correct | – | The system correctly abstained, stating the sources don't specify SkyNode colors, without inventing any information. |
| q20 | inference | Does Aurora Instruments sell a home security camera? | #1 | correct | yes | The system correctly says no and identifies the single SkyNode weather station product line; the extra model details don't contradict the reference. |
| q21 | negative | Who is the current CEO of Aurora Instruments? | – | correct | – | The system correctly abstains, noting the sources name founders Varga and Reed but do not identify a CEO, without guessing. |
