#!/usr/bin/env python3
import json,pathlib,sys
root=pathlib.Path(__file__).resolve().parent.parent
issue=sys.argv[1]
data=json.loads((root/'issues'/issue/'issue.json').read_text())
assert data['issue_id']==issue and isinstance(data['articles'],list)
assert len({a['id'] for a in data['articles']})==len(data['articles'])
for article in data['articles']:
 assert article['type'] in ('feature','regatta_report','brief')
 for block in article['blocks']: assert block['type'] in ('paragraph','heading','image','quote','results','video')
out=root/'public'/'issues'/issue/'issue.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(data,ensure_ascii=False,indent=2))
print(str(out),len(data['articles']),'articles')
