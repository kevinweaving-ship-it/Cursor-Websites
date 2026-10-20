import json,pathlib,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"app"))
from evidence_pipeline import verify,verified_cluster,extract,recap,source_notes
F={"slug":"2026-09-25-tsc-420-nationals","url":"https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals",
"title":"420 Nationals","class_name":"420","club":"TSC","club_name":"Theewater Sports Club","start":"2026-09-26","end":"2026-09-27",
"names":["Dale Rae","James Rae","Timothy Weaving","Hayden Miller"],"ranked_rows":[]}
class EvidenceRegression(unittest.TestCase):
 def test_source_label_never_bypasses_identity(self):
  for engine in ("seed","facebook","host_club_post","class_catalog","source_media"):
   self.assertFalse(verify({"url":"https://example.org/other-event","title":"Dart 18 at Royal Yorkshire","description":"A long report about an entirely unrelated event at another venue.","engine":engine},F)["accepted"])
 def test_wrong_year_even_with_names(self):
  item={"url":"https://example.org/story","title":"420 Nationals","body":"Dale Rae and James Rae won the 420 Nationals at Theewater Sports Club in 2024.","published":"2024-09-27"}
  self.assertFalse(verify(item,F)["accepted"])
 def test_home_and_group_are_discovery_only(self):
  for url in ("https://aeolians.co.za/","https://facebook.com/groups/120115671476306/"):
   self.assertFalse(verify({"url":url,"body":"Dale Rae and James Rae at the 420 Nationals at Theewater Sports Club 2026."},F)["accepted"])
 def test_share_and_repost_content_deduplicate(self):
  body="Dale Rae and James Rae won the 420 Nationals at Theewater Sports Club in September 2026. The same post is cross-shared."
  candidates=[{"url":"https://example.org/report/","body":body},{"url":"https://example.org/report?utm_source=fb","body":body},{"url":"https://another.org/cross-share","body":body}]
  result=verified_cluster(F,candidates,fetch=False)
  self.assertEqual(len(result["articles"]),1)
  self.assertEqual(len(result["rejected"]),2)
 def test_full_body_is_extracted(self):
  paras=["This is paragraph number "+str(i)+" with enough article text to remain in the body." for i in range(7)]
  html=("<html><article>"+"".join("<p>"+x+"</p>" for x in paras)+"</article></html>").encode()
  class Response:
   url="https://example.org/report"
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,*a):return html
  with patch("urllib.request.urlopen",return_value=Response()):
   result=extract(Response.url)
  self.assertIn(paras[-1],result["body"])
 def test_youth_names_must_match_actual_sailors(self):
  item={"url":"https://example.org/youth","title":"420 Nationals",
      "body":"Hermanus High School celebrates Timothy Weaving and his crew partner Hayden Miller. They secured 1st place in the U17 420 National Championship at Theewater Sports Club in September 2026."}
  notes=source_notes({"articles":[item]},F,[{"url":item["url"],"n":2}])
  self.assertEqual(len(notes),1)
  self.assertIn("Timothy Weaving and Hayden Miller",notes[0])
  self.assertNotIn("Hermanus High and",notes[0])
 def test_final_race_claim_not_inferred_from_three_late_wins(self):
  facts=dict(F,winner="Dale Rae and James Rae",winner_nett="10",winner_scores={"R1":"1","R2":"1","R3":"1","R4":"2"},races=4,entries=10,status="Final",second="",third="",tied_first=False)
  text=" ".join(recap(facts,{},[{"n":1}]))
  self.assertNotIn("won the final race",text)
 def test_delayed_primary_report_needs_event_and_competitor_proof(self):
  facts=dict(F,slug="2026-09-24-ayc-505-nationals",class_name="505",club="AYC",club_name="Aeolians Yacht Club",names=["Peter Funke","Thomas Funke","Kyle Klaas"],start="2026-09-24")
  item={"url":"https://rsa505.org.za/report","title":"505 Nationals 2026 at Aeolians","body":"The 505 Class held its 2026 Nationals at Aeolians. Peter Funke and Thomas Funke tied with Kyle Klaas.","published":"2026-10-13"}
  self.assertTrue(verify(item,facts)["accepted"])
  self.assertEqual(verify(item,facts)["reason"],"late_report_matched")
  self.assertFalse(verify(dict(item,published="2025-10-13"),facts)["accepted"])
 def test_verified_youth_photo_caption_names_sailors(self):
  from evidence_pipeline import photo_caption
  item={"url":"https://example.org/youth","body":"Timothy Weaving and Hayden Miller won the U17 420 National Championship. Hermanus High School congratulates them."}
  caption=photo_caption({"source_url":item["url"]},F,{"articles":[item]})
  self.assertEqual(caption,"Timothy Weaving and Hayden Miller — under-17 champions.")
 def test_2025_collage_is_explicitly_excluded(self):
  from evidence_pipeline import MEDIA_EXCLUSIONS,canonical
  self.assertIn(canonical("https://rsa505.org.za/images/20261013_101619-COLLAGE.jpg"),MEDIA_EXCLUSIONS)
 def test_stale_pdf_cannot_satisfy_staged_validation(self):
  from safe_publish import validate
  import tempfile
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp);out=root/"public/issues/2026-09-28";out.mkdir(parents=True)
   (out/"issue.json").write_text(json.dumps({"articles":[]}))
   source=root/"issues/2026-09-28/sources";source.mkdir(parents=True)
   (source/"events-weekend.json").write_text(json.dumps({"events":[]}))
   (out/"index.html").write_text("<html>New edition</html>")
   with self.assertRaisesRegex(ValueError,"Missing PDF"):
    validate(root,"2026-09-28")
 def test_equal_scores_do_not_prove_countback(self):
  facts=dict(F,winner="Dale Rae and James Rae",winner_nett="10",winner_scores={},races=4,entries=10,status="Final",second="Other Crew",second_nett="10",third="",tied_first=True)
  text=" ".join(recap(facts,{},[{"n":1}]))
  self.assertNotIn("countback",text)
  self.assertIn("level on nett points",text)
if __name__=="__main__":unittest.main()
