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
  facts=dict(F,slug="2026-09-24-ayc-505-nationals",title="505 Nationals",class_name="505",club="AYC",club_name="Aeolians Yacht Club",names=["Peter Funke","Thomas Funke","Kyle Klaas"],start="2026-09-24",end="2026-09-27")
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
 def test_dart_nationals_post_never_verifies_as_bottle(self):
  from evidence_pipeline import other_event_conflict
  bottle={"slug":"2026-10-10-hmyc-dam-bottle-sprints","title":"Dam Bottle Sprints","url":"https://sailingsa.co.za/regatta/2026-10-10-hmyc-dam-bottle-sprints","class_name":"","mixed_class":True,"club":"HMYC","club_name":"Henley Midmar Yacht Club","start":"2026-10-10","end":"2026-10-11","names":["Lorrian Wells","Colin Dommett","Iain Paxman"]}
  dart_post={"url":"https://www.facebook.com/share/p/1PGpY1pGh1/","title":"DART 18 NATIONALS – Final results!","body":"Congratulations to all the sailors competing in the Dart 18 Nationals. 1st Bradley Levin 2nd Kyle Boman 3rd Bradley Stemmett. 7th Lorrian Wells at Henley Midmar Yacht Club 2026."}
  self.assertEqual(other_event_conflict(dart_post,bottle),"other_event")
  self.assertFalse(verify(dart_post,bottle)["accepted"])
  official={"url":bottle["url"],"title":"Dam Bottle Sprints — SailingSA results","body":"Official SAS-sanctioned Dam Bottle Sprints at Henley Midmar Yacht Club. 1st Lorrian Wells. 2nd Colin Dommett. 3rd Iain Paxman."}
  self.assertIsNone(other_event_conflict(official,bottle))
  self.assertTrue(verify(official,bottle)["accepted"])
 def test_class_venue_year_is_not_identity(self):
  bottle={"slug":"2026-10-10-hmyc-dam-bottle-sprints","title":"Dam Bottle Sprints","url":"https://sailingsa.co.za/regatta/2026-10-10-hmyc-dam-bottle-sprints","class_name":"Dart 18","club":"HMYC","club_name":"Henley Midmar Yacht Club","start":"2026-10-10","end":"2026-10-11","names":["Lorrian Wells"]}
  item={"url":"https://example.org/hmyc-open","title":"Weekend racing at HMYC","body":"Dart 18 racing at Henley Midmar Yacht Club in 2026 with a long enough caption for the verifier."}
  self.assertFalse(verify(item,bottle)["accepted"])
 def test_mixed_recap_keeps_class_podiums_separate(self):
  from evidence_pipeline import recap
  facts={"title":"Free State Youth Provincial Champs","club_name":"Lake Deneys Yacht Club","winner":"Maximilian Malan","winner_class":"Dabchick","winner_nett":"6","winner_scores":{"R1":"1","R2":"1","R3":"1","R4":"1","R5":"1","R6":"1","R7":"14"},"races":7,"entries":26,"status":"Final","mixed_class":True,"classes":["Dabchick","Optimist A","Optimist B"],"second":"Taylor Milln","second_nett":"8","third":"Danny Coetzer","third_nett":"10","tied_first":False,"start":"2026-10-03","end":"2026-10-04","ranked_rows":[{"class_name":"Dabchick","helm_name":"Maximilian Malan"},{"class_name":"Dabchick","helm_name":"Ethan Biagio"},{"class_name":"Dabchick","helm_name":"David Smith"},{"class_name":"Optimist A","helm_name":"Taylor Milln"},{"class_name":"Optimist A","helm_name":"Luan Bester"},{"class_name":"Optimist B","helm_name":"Danny Coetzer"}]}
  text=" ".join(recap(facts,{},[{"n":1}]))
  self.assertIn("Ethan Biagio",text)
  self.assertIn("Dabchick",text)
  self.assertIn("Optimist A",text)
  self.assertNotIn("Taylor Milln finished second",text)
 def test_multi_event_feature_lists_each_event_and_has_no_week_hero(self):
  from evidence_pipeline import feature
  import datetime as dt
  reports=[
    {"id":"a","type":"regatta_report","headline":"505 Nationals at Aeolians","deck":"Aeolians","hero_image":{"url":"media/505.jpg"}},
    {"id":"b","type":"regatta_report","headline":"Dabchick Gauteng Regionals at Aeolians","deck":"Aeolians","hero_image":{"url":"media/dabchick.jpg"}},
    {"id":"c","type":"regatta_report","headline":"Dart 18 Nationals at Henley Midmar","deck":"HMYC"},
  ]
  art=feature("2026-09-28",dt.date(2026,9,28),[],reports)
  blob=" ".join(b.get("text") or "" for b in art["blocks"] if b.get("type")=="paragraph")
  self.assertIn("505 Nationals",blob)
  self.assertIn("Dabchick Gauteng Regionals",blob)
  self.assertIn("Dart 18 Nationals",blob)
  self.assertFalse(any(b.get("type")=="image" for b in art["blocks"]))
 def test_feature_uses_scored_report_not_empty_calendar_line(self):
  from evidence_pipeline import feature
  import datetime as dt
  reports=[{"id":"2026-10-04-free-state-youth-provincial-champs","type":"regatta_report","headline":"Maximilian Malan dominates Free State Youth Provincial Champs at Lake Deneys","deck":"Lake Deneys Yacht Club · 6 nett · 26 entries","kicker":"DABCHICK / OPTIMIST A / OPTIMIST B  ·  LDYC","hero_image":{"url":"media/2026-10-04-free-state-youth-provincial-champs.png","source_url":"https://sailingsa.co.za/regatta/2026-10-04-free-state-youth-provincial-champs"}}]
  events=[{"event_name":"Agulhas Race","regatta_id":None,"has_results":False}]
  art=feature("2026-10-05",dt.date(2026,10,5),events,reports)
  blob=" ".join(b.get("text") or "" for b in art["blocks"] if b.get("type")=="paragraph")
  self.assertIn("Maximilian Malan",blob)
  self.assertIn("Lake Deneys",blob)
  self.assertTrue(art.get("hero_image"))
  self.assertTrue(any(b.get("type")=="image" for b in art["blocks"]))
  self.assertNotIn("source snapshot",blob)
 def test_own_recap_paragraph_is_not_required_to_repeat_the_headline(self):
  from evidence_pipeline import other_event_conflict
  facts={"slug":"2026-10-10-hmyc-dam-bottle-sprints","title":"Lorrian Wells dominates Dam Bottle Sprints"}
  recap={"url":"","title":"","body":"Lorrian Wells won on 5 points from Colin Dommett [1]."}
  self.assertIsNone(other_event_conflict(recap,facts,require_identity=False))
  dart_quote={"url":"","title":"","body":"Bradley Levin won the Dart 18 Nationals at HMYC [2]."}
  self.assertEqual(other_event_conflict(dart_quote,facts,require_identity=False),"other_event")
if __name__=="__main__":unittest.main()
