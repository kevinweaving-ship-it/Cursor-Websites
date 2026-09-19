# SAS name reorder — later, not an open fault

Checked against the sailing.org.za member card for the SAS ID. Do not treat these as match bugs. On the final reorder, rewrite our stored name to the card. Do not merge two live cards.

## Not an issue now

- **Apostrophe stored as `&#039;`.** The card name is a normal apostrophe. Example: SAS 19187 is Esther O'Brien, born 1970. We stored the page code, not a different person. Same for Mi'Lan Nel, SAS 23543, born 2010.
- **Van dropped.** SAS 26851 card is Carl Van Rooyen's, born 1968. We stored Carl Rooyen's. SAS 26852 card is Seema Khehar Van Rooyen's, born 1975. We stored Seema Rooyen's. Same person, same ID. Surname words were dropped by the parser.
- **Louis has no surname.** SAS 21507 card is ", Louis", born 2023. The blank surname is on SAS. We did not invent it.
- **Lennon dropped.** SAS 22324 card is Adaikalam, Lennon, born 1985. A double comma made us store Adaikalam only. Same ID. Put Lennon back on the reorder.
- **Second Jay card is an empty page.** SAS 1581 is Jay D'Engle, born 1991. SAS 27755 returns no member. Remove 27755 on the reorder. Do not move 1581's results.
- **Same name, different card.** Andre Potgieter is four SAS cards: 3206 Andre Potgieter born 1957, 11873 Andre Harding Potgieter born 1957, 27740 born 1969, 16342 born 1972. Different people, or a middle name that makes them different. Do not merge.

Robby Balona on key `My China` is the admin login, not a sailor card.
