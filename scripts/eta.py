#!/usr/bin/env python3
import argparse, os, sqlite3, time, uuid, json, statistics
from pathlib import Path
P=Path(os.getenv('AGENT_ETA_DB',str(Path.home()/'.agent-eta'/'history.sqlite3')))
def dbopen():
 P.parent.mkdir(parents=True,exist_ok=True); d=sqlite3.connect(P); d.row_factory=sqlite3.Row
 d.execute('CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,title TEXT,agent TEXT,model TEXT,category TEXT,complexity INTEGER,started REAL,ended REAL,outcome TEXT)')
 d.execute('CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY,value TEXT)'); d.commit(); return d
def main():
 p=argparse.ArgumentParser(description='Agent ETA local forecasting'); s=p.add_subparsers(dest='cmd',required=True)
 for cmd in ('estimate','start'):
  x=s.add_parser(cmd); x.add_argument('title'); x.add_argument('--agent',default='unknown'); x.add_argument('--model',default='unknown'); x.add_argument('--category',default='other'); x.add_argument('--complexity',type=int,choices=range(1,6),default=3)
 x=s.add_parser('finish'); x.add_argument('id'); x.add_argument('--outcome',choices=['success','failed','abandoned'],default='success')
 x=s.add_parser('config'); x.add_argument('--mode',choices=['automatic','on-demand']); x.add_argument('--share',choices=['yes','no'])
 s.add_parser('history'); a=p.parse_args(); d=dbopen()
 if a.cmd=='config':
  for k,v in [('mode',a.mode),('share',a.share)]:
   if v:d.execute('INSERT OR REPLACE INTO config VALUES(?,?)',(k,v))
  d.commit(); print(dict(d.execute('SELECT * FROM config').fetchall())); return
 if a.cmd=='start':
  i=uuid.uuid4().hex[:12]; d.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,NULL,NULL)',(i,a.title,a.agent,a.model,a.category,a.complexity,time.time())); d.commit(); print(json.dumps({'id':i,'status':'started'})); return
 if a.cmd=='finish':
  r=d.execute('SELECT started FROM tasks WHERE id=? AND ended IS NULL',(a.id,)).fetchone()
  if not r:p.error('unknown or already finished task id')
  elapsed=time.time()-r['started']; d.execute('UPDATE tasks SET ended=?,outcome=? WHERE id=?',(time.time(),a.outcome,a.id)); d.commit(); print(json.dumps({'id':a.id,'minutes':round(elapsed/60,2),'outcome':a.outcome})); return
 if a.cmd=='history':
  print(json.dumps([dict(r) for r in d.execute('SELECT * FROM tasks ORDER BY started DESC LIMIT 30')],indent=2)); return
 rows=d.execute("SELECT * FROM tasks WHERE outcome='success' AND ended>started").fetchall(); weighted=[]
 for r in rows:
  weight=(1 if r['model']==a.model else .2)*(1 if r['agent']==a.agent else .5)*(1 if r['category']==a.category else .3)/(1+abs(r['complexity']-a.complexity))
  if weight>=.15:weighted.append(((r['ended']-r['started'])/60,weight))
 if not weighted:print(json.dumps({'estimate':None,'confidence':'insufficient-data','message':'No comparable completed tasks; do not invent a time estimate.','samples':0})); return
 weighted.sort(); total=sum(w for _,w in weighted)
 def quantile(q):
  acc=0
  for v,w in weighted:
   acc+=w
   if acc>=total*q:return round(v,1)
  return round(weighted[-1][0],1)
 print(json.dumps({'p20_minutes':quantile(.2),'p50_minutes':quantile(.5),'p80_minutes':quantile(.8),'samples':len(weighted),'confidence':'low' if len(weighted)<10 else 'moderate','warning':'Historical observations are not a guarantee; sample may be biased.'}))
if __name__=='__main__':main()
