# Evaluation: openai-gpt-6-luna

21 questions over 11 chunks; embeddings BAAI/bge-small-en-v1.5; chunks 1000 chars with 150 overlap; top 6. Graded by claude-opus-5-5.

- Retrieval: expected page in top 6 for 100% (MRR 1.00)
- Answers: 19 correct, 0 partial, 0 incorrect of 19 (score 100%); 0 declined wrongly
- Abstention: declined 2 of 2 questions the document can't answer
- Citations: 100% of answers cite the expected page
- Tokens: answers 30,501 in / 743 out ($0.003); grader 17,770 in / 1,548 out ($0.102)
- Median time to a full answer: 1.1s

| ID | Category | Question | Retrieval | Verdict | Cites page | Grader's reason |
|---|---|---|---|---|---|---|
| q01 | factual | When was Aurora Instruments founded? | #1 | correct | yes | The system answer states the founding year 2019, matching the reference exactly. |
| q02 | factual | Where is Aurora Instruments headquartered? | #1 | correct | yes | The system answer states Boulder, Colorado, USA, matching the reference exactly. |
| q03 | factual | Who founded the company? | #1 | correct | yes | The system names both founders, Dr. Elena Varga and Marcus Reed, matching the reference answer. |
| q04 | factual | How many people does Aurora Instruments employ as of 2026? | #1 | correct | yes | The system states 112 people, matching the reference answer. |
| q05 | factual | How much does the SkyNode Pro cost? | #1 | correct | yes | The system answer states the price as $299, matching the reference answer exactly. |
| q06 | factual | How many sensors does the SkyNode Max include? | #1 | correct | yes | The system answer states 14 sensors, matching the reference answer exactly. |
| q07 | numeric | What is the price difference between the cheapest and most expensive SkyNode models? | #1 | correct | yes | The system answer correctly identifies both models, their prices ($149 and $499), and the $350 difference, matching the reference. |
| q08 | comparative | Which SkyNode model should I choose if my location has no Wi-Fi coverage? | #1 | correct | yes | The system correctly identifies the SkyNode Max and gives the reason that it has cellular backup and can operate without Wi-Fi. It leaves out the supporting detail that the Lite and Pro require Wi-Fi, but the core answer is fully covered. |
| q09 | factual | How accurate are the temperature readings? | #1 | correct | yes | The system answer states ±0.3°C accuracy, which matches the reference answer exactly. |
| q10 | numeric | What is the annual price of the Pro cloud plan, and roughly how much does paying annually save versus monthly? | #1 | correct | yes | The system gives the $129 annual price and the roughly 18% saving, both of which match the reference. |
| q11 | factual | Which cloud plan do I need for API access and CSV data export? | #1 | correct | yes | The system correctly identifies the Pro plan as providing both API access and CSV export, matching the reference. |
| q12 | conditional | How long is the warranty if I register my station in the app within 30 days of purchase? | #1 | correct | yes | The system correctly states the warranty extends to 3 years with registration within 30 days, matching the reference's key fact; omitting the standard 2-year baseline is minor. |
| q13 | factual | What is the return window for hardware bought directly from Aurora? | #1 | correct | yes | The system correctly gives the return window as 45 days from delivery, which answers the question. It omits the full-refund and resalable-condition detail, but that is supplementary to the window asked about. |
| q14 | procedural | How do I reset a SkyNode station to factory settings? | #1 | correct | yes | The system answer gives every key fact: hold the hub button for 10 seconds until the light flashes red, and the hub restarts in setup mode. The extra detail about about 5 minutes of reconfiguration does not contradict the reference. |
| q15 | factual | What type of batteries do the outdoor sensor modules use? | #1 | correct | yes | The system answer matches the reference exactly: two AA lithium batteries per outdoor sensor module. |
| q16 | conditional | What discount do schools and non-profits receive? | #1 | correct | yes | The system answer states the 40% discount on Plus and Pro plans and on hardware purchases of five or more stations, and conveys verification by saying 'verified' schools and non-profits. This matches all key facts in the reference. |
| q17 | comparative | I'm a Pro-plan subscriber whose device needs repair. What do I get while I wait, and how long does a repair usually take? | #1 | correct | yes | The system answer gives both key facts from the reference: Pro-plan subscribers get a loaner unit, and repairs typically take 10 business days from when Aurora receives the device. |
| q18 | comparative | Can I still see my data during an internet outage, and how far back? | #1 | correct | yes | The system answer matches all key facts: local access via the hub over the local network during an outage and storage durations of 7/30/90 days for Lite/Pro/Max. |
| q19 | negative | What colors is the SkyNode available in? | – | correct | – | The system correctly states that the sources don't specify SkyNode colors. It does not invent any color options. |
| q20 | inference | Does Aurora Instruments sell a home security camera? | #1 | correct | yes | The system answer says no, identifies the single SkyNode weather station product line, and notes that no security camera is mentioned. This matches the reference; the detail about three models is extra but doesn't contradict it. |
| q21 | negative | Who is the current CEO of Aurora Instruments? | – | correct | – | The system correctly states that the sources do not identify the CEO, and it does not invent a name. |
