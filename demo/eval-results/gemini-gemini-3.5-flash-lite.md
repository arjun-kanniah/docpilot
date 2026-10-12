# Evaluation: gemini-gemini-3.5-flash-lite

21 questions over 11 chunks; embeddings BAAI/bge-small-en-v1.5; chunks 1000 chars with 150 overlap; top 6. Graded by claude-opus-5-5.

- Retrieval: expected page in top 6 for 100% (MRR 0.97)
- Answers: 19 correct, 0 partial, 0 incorrect of 19 (score 100%); 0 declined wrongly
- Abstention: declined 2 of 2 questions the document can't answer
- Citations: 100% of answers cite the expected page
- Tokens: answers 32,328 in / 752 out (n/a); grader 18,078 in / 1,568 out ($0.104)
- Median time to a full answer: 0.7s

| ID | Category | Question | Retrieval | Verdict | Cites page | Grader's reason |
|---|---|---|---|---|---|---|
| q01 | factual | When was Aurora Instruments founded? | #1 | correct | yes | The system answer states the founding year 2019, matching the reference answer exactly. |
| q02 | factual | Where is Aurora Instruments headquartered? | #1 | correct | yes | The system answer states Boulder, Colorado, USA, which matches the reference exactly. |
| q03 | factual | Who founded the company? | #1 | correct | yes | The system names both founders, Dr. Elena Varga and Marcus Reed, matching the reference answer. |
| q04 | factual | How many people does Aurora Instruments employ as of 2026? | #1 | correct | yes | The system states 112 people, matching the reference answer. |
| q05 | factual | How much does the SkyNode Pro cost? | #1 | correct | yes | The system states the price of $299, matching the reference answer. |
| q06 | factual | How many sensors does the SkyNode Max include? | #1 | correct | yes | The system answer states 14 sensors, matching the reference exactly. |
| q07 | numeric | What is the price difference between the cheapest and most expensive SkyNode models? | #1 | correct | yes | The system correctly identifies SkyNode Lite at $149 and SkyNode Max at $499, and gives the $350 difference, matching the reference. |
| q08 | comparative | Which SkyNode model should I choose if my location has no Wi-Fi coverage? | #1 | correct | yes | The system answer recommends the SkyNode Max for its cellular backup and ability to operate without Wi-Fi, and notes that the Lite and Pro need 2.4 GHz Wi-Fi. This matches every key fact in the reference. |
| q09 | factual | How accurate are the temperature readings? | #1 | correct | yes | The system states ±0.3°C accuracy, matching the reference; the extra mounting details don't contradict it. |
| q10 | numeric | What is the annual price of the Pro cloud plan, and roughly how much does paying annually save versus monthly? | #1 | correct | yes | The system answer gives the $129 annual price and the roughly 18% saving, both of which match the reference. |
| q11 | factual | Which cloud plan do I need for API access and CSV data export? | #1 | correct | yes | The system correctly identifies the Pro plan as providing API access and CSV export, matching the reference. The reference also says Pro is the only such plan, but that detail is implicit in the answer and isn't a contradiction. |
| q12 | conditional | How long is the warranty if I register my station in the app within 30 days of purchase? | #1 | correct | yes | The system correctly states the warranty is extended to 3 years when registered within 30 days. Omitting the standard 2-year baseline is minor, since the key fact is the 3-year duration. |
| q13 | factual | What is the return window for hardware bought directly from Aurora? | #1 | correct | yes | The system gives the 45-day window from delivery and the resalable-condition requirement, matching the reference. Not stating 'full refund' explicitly is a minor omission that doesn't affect the answer to the question. |
| q14 | procedural | How do I reset a SkyNode station to factory settings? | #1 | correct | yes | The system answer states every key fact: hold the hub button for 10 seconds until the light flashes red, after which the hub restarts into setup mode. The added detail about a 5-minute app reconfiguration doesn't contradict the reference. |
| q15 | factual | What type of batteries do the outdoor sensor modules use? | #2 | correct | yes | The system correctly states two AA lithium batteries, matching the reference; extra detail about cold performance doesn't contradict it. |
| q16 | conditional | What discount do schools and non-profits receive? | #1 | correct | yes | The system answer states the 40% discount on Plus and Pro plans and on hardware purchases of five or more stations, and notes verification by saying "verified" schools and non-profits. This covers all key facts in the reference. |
| q17 | comparative | I'm a Pro-plan subscriber whose device needs repair. What do I get while I wait, and how long does a repair usually take? | #1 | correct | yes | The system answer gives both key facts in the reference: Pro-plan subscribers get a loaner unit, and repairs typically take 10 business days from when Aurora receives the device. |
| q18 | comparative | Can I still see my data during an internet outage, and how far back? | #1 | correct | yes | The system answer matches every key fact: yes, local network access to the hub, and 7/30/90 days of storage for Lite/Pro/Max. |
| q19 | negative | What colors is the SkyNode available in? | – | correct | – | The question is unanswerable from the documents, and the system correctly abstained by saying the sources lack color information, without guessing any colors. |
| q20 | inference | Does Aurora Instruments sell a home security camera? | #1 | correct | yes | The system says Aurora's only product line is the SkyNode home weather station and that no security camera is mentioned. This matches the reference and implies the answer is no; it is a substantive answer rather than an abstention. |
| q21 | negative | Who is the current CEO of Aurora Instruments? | – | correct | – | The system correctly states the sources don't name the CEO and only mentions the founders, which is related information in the documents, without guessing. |
