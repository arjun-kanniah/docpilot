# Evaluation: anthropic-claude-haiku-5-5

21 questions over 11 chunks; embeddings BAAI/bge-small-en-v1.5; chunks 1000 chars with 150 overlap; top 6. Graded by claude-opus-5-5.

- Retrieval: expected page in top 6 for 100% (MRR 0.97)
- Answers: 19 correct, 0 partial, 0 incorrect of 19 (score 100%); 0 declined wrongly
- Abstention: declined 2 of 2 questions the document can't answer
- Citations: 100% of answers cite the expected page
- Tokens: answers 48,523 in / 3,403 out ($0.007); grader 18,609 in / 1,502 out ($0.104)
- Median time to a full answer: 1.4s

| ID | Category | Question | Retrieval | Verdict | Cites page | Grader's reason |
|---|---|---|---|---|---|---|
| q01 | factual | When was Aurora Instruments founded? | #1 | correct | yes | The system correctly states the founding year 2019; the additional location and founder details do not contradict the reference. |
| q02 | factual | Where is Aurora Instruments headquartered? | #1 | correct | yes | The system correctly states the headquarters is in Boulder, Colorado, matching the reference; extra details don't contradict it. |
| q03 | factual | Who founded the company? | #1 | correct | yes | The system names both founders, Dr. Elena Varga and Marcus Reed, matching the reference. The extra detail about their prior work does not contradict it. |
| q04 | factual | How many people does Aurora Instruments employ as of 2026? | #1 | correct | yes | The system states 112 employees, matching the reference answer. |
| q05 | factual | How much does the SkyNode Pro cost? | #1 | correct | yes | The system states the price as $299, matching the reference answer. The added currency label and citation marker don't change the fact. |
| q06 | factual | How many sensors does the SkyNode Max include? | #1 | correct | yes | The system answer states 14 sensors, matching the reference exactly. |
| q07 | numeric | What is the price difference between the cheapest and most expensive SkyNode models? | #1 | correct | yes | The system correctly identifies SkyNode Lite at $149 and SkyNode Max at $499, and gives the $350 difference, matching the reference. |
| q08 | comparative | Which SkyNode model should I choose if my location has no Wi-Fi coverage? | #1 | correct | yes | The system answer recommends the SkyNode Max for its cellular backup and ability to run without Wi-Fi. It also notes that the Lite and Pro need 2.4 GHz Wi-Fi, which matches every key fact in the reference. |
| q09 | factual | How accurate are the temperature readings? | #1 | correct | yes | The system states the ±0.3°C accuracy, matching the reference, and its extra mounting advice doesn't contradict it. |
| q10 | numeric | What is the annual price of the Pro cloud plan, and roughly how much does paying annually save versus monthly? | #1 | correct | yes | The system correctly states the $129 annual price and the roughly 18% savings, and its $27 calculation is accurate and consistent with the reference. |
| q11 | factual | Which cloud plan do I need for API access and CSV data export? | #1 | correct | yes | The system answer identifies the Pro plan as the only plan with both API access and CSV export, matching the reference. |
| q12 | conditional | How long is the warranty if I register my station in the app within 30 days of purchase? | #1 | correct | yes | The system states the warranty extends to 3 years with registration within 30 days, versus the standard 2 years, which matches the reference. |
| q13 | factual | What is the return window for hardware bought directly from Aurora? | #1 | correct | yes | The system answer states the 45-day window from delivery and the full refund for items in resalable condition, which covers every key fact in the reference. The extra details about shipping and refund timing do not contradict it. |
| q14 | procedural | How do I reset a SkyNode station to factory settings? | #1 | correct | yes | The system answer gives every key fact: hold the button on the central hub for 10 seconds until the light flashes red, after which the hub restarts into setup mode. The extra detail about reconfiguration time does not contradict the reference. |
| q15 | factual | What type of batteries do the outdoor sensor modules use? | #2 | correct | yes | The system answer states two AA lithium batteries, matching the reference; the extra detail about cold performance does not contradict it. |
| q16 | conditional | What discount do schools and non-profits receive? | #1 | correct | yes | The system states the 40% discount on Plus and Pro plans and on hardware purchases of five or more stations, with verification required. The extra application details do not contradict the reference. |
| q17 | comparative | I'm a Pro-plan subscriber whose device needs repair. What do I get while I wait, and how long does a repair usually take? | #1 | correct | yes | The system states both key facts: a loaner unit for Pro-plan subscribers and a typical 10-business-day turnaround from receipt. The extra out-of-warranty fee detail doesn't contradict the reference. |
| q18 | comparative | Can I still see my data during an internet outage, and how far back? | #1 | correct | yes | The answer states local access over the network during outages and gives the correct retention for each model: 7, 30 and 90 days. This matches the reference. The extra detail about Lite and Pro logging locally doesn't contradict it. |
| q19 | negative | What colors is the SkyNode available in? | – | correct | – | The system correctly states that the documents don't specify color options and doesn't invent any. |
| q20 | inference | Does Aurora Instruments sell a home security camera? | #1 | correct | yes | The system answer conveys that no security camera is mentioned and that Aurora sells a single product line, the SkyNode weather station, matching the reference. Since that is an actual answer, it is not an abstention. |
| q21 | negative | Who is the current CEO of Aurora Instruments? | – | correct | – | The system correctly states that the sources don't name a current CEO and does not guess. It only mentions related facts from the documents, such as the founders and the employee count. |
