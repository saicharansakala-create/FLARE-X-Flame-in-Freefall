from __future__ import annotations
import json, sqlite3, hashlib, io, os, re, urllib.request, urllib.request
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd
from scipy import stats
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; DB=DATA/'flarex.sqlite3'
FILES={'flame':'flame_research.json','catalogue':'investigation_catalogue.json','prevention':'prevention_database.json'}
DATASETS={k:json.loads((DATA/v).read_text(encoding='utf-8')) for k,v in FILES.items()}
app=FastAPI(title='FLARE-X Scientific Research API',version='2.0.0',description='Evidence-grounded combustion research, reproducible data checks, mission relevance ranking and safety decision support. Not a flight-certification tool.')
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5500','http://localhost:5500','http://127.0.0.1:5500/','null'],allow_methods=['*'],allow_headers=['*'])

# Persist every source collection as JSON records in a local SQLite database.
def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
 DATA.mkdir(exist_ok=True)
 with conn() as c:
  c.execute('CREATE TABLE IF NOT EXISTS records (collection TEXT NOT NULL, record_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(collection,record_id))')
  c.execute('CREATE TABLE IF NOT EXISTS workbook_rows (sheet TEXT NOT NULL, row_no INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(sheet,row_no))')
  for coll,obj in DATASETS.items():
   for group,rows in obj.items():
    if not isinstance(rows,list): continue
    for i,row in enumerate(rows):
     if not isinstance(row,dict): row={'value':row}
     rid=str(row.get('id') or row.get('ID') or row.get('measure_id') or row.get('Row_ID') or row.get('source_id') or row.get('accident_id') or i)
     c.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)',(f'{coll}.{group}',rid,json.dumps(row,ensure_ascii=False)))
  wb=DATA/'source_workbook.xlsx'
  if wb.exists():
   xls=pd.ExcelFile(wb)
   for sheet in xls.sheet_names:
    if sheet.strip().lower() in ('readme','summary'): continue
    df=pd.read_excel(wb,sheet_name=sheet).replace({np.nan:None})
    for i,row in enumerate(df.to_dict(orient='records'),start=2):
     clean={k:(v.item() if isinstance(v,np.generic) else v) for k,v in row.items()}
     c.execute('INSERT OR REPLACE INTO workbook_rows VALUES(?,?,?)',(sheet,i,json.dumps(clean,ensure_ascii=False,default=str)))
  c.commit()
init_db()

def records(coll):
 with conn() as c: return [json.loads(r['payload']) for r in c.execute('SELECT payload FROM records WHERE collection=?',(coll,)).fetchall()]
def wb_records(sheet):
 with conn() as c: return [json.loads(r['payload']) for r in c.execute('SELECT payload FROM workbook_rows WHERE sheet=? ORDER BY row_no',(sheet,)).fetchall()]
def all_sources(): return DATASETS['flame']['sources']
def srcmap():
 out={s.get('id'):s for s in all_sources()}
 for r in DATASETS['catalogue'].get('refs',[]): out[r.get('id')]= {'id':r.get('id'),'title':r.get('t'),'url':r.get('u'),'grade':'Catalogue reference'}
 for r in DATASETS['prevention'].get('sources',[]): out[r.get('source_id')]= {'id':r.get('source_id'),'title':r.get('title'),'url':r.get('url'),'grade':r.get('type_and_grade')}
 return out
def evidence_text(r): return ' '.join(str(v) for v in r.values() if v is not None)

@app.get('/')
def root(): return {'project':'FLARE-X','status':'ready','api_docs':'/docs','health':'/api/health','version':'2.0.0'}
@app.get('/api/health')
def health():
 with conn() as c: n=c.execute('select count(*) from records').fetchone()[0]; w=c.execute('select count(*) from workbook_rows').fetchone()[0]
 return {'status':'ok','database':'SQLite connected','indexed_records':n,'workbook_rows':w}
@app.get('/api/datasets/summary')
def dataset_summary():
 return {'catalogue_investigations':len(DATASETS['catalogue']['inv']),'test_condition_rows':len(DATASETS['catalogue']['tc']),'accidents':len(DATASETS['flame']['accidents']),'accident_timeline_events':len(DATASETS['flame']['timeline']),'damaged_components':len(DATASETS['flame']['components']),'temperature_records':len(DATASETS['flame']['temps']),'phenomena':len(DATASETS['flame']['phenomena']),'prevention_measures':len(DATASETS['prevention']['measures']),'sources':len(DATASETS['flame']['sources']),'workbook_sheets_imported':[s for s in ['Accidents','Timeline','Damaged_Components','PSI_Combustion','Sources'] if wb_records(s)]}
@app.get('/api/data/{dataset}/{collection}')
def get_collection(dataset:str,collection:str,q:str|None=None,limit:int=Query(500,ge=1,le=2000)):
 if dataset not in DATASETS or collection not in DATASETS[dataset] or not isinstance(DATASETS[dataset][collection],list): raise HTTPException(404,'Dataset collection not found')
 rows=records(f'{dataset}.{collection}')
 if q:
  term=q.casefold(); rows=[r for r in rows if term in evidence_text(r).casefold()]
 return {'total':len(rows),'items':rows[:limit]}
@app.get('/api/workbook/{sheet}')
def workbook_sheet(sheet:str,limit:int=Query(500,ge=1,le=2000)):
 rows=wb_records(sheet)
 if not rows: raise HTTPException(404,'Workbook sheet not found or contains no imported data')
 return {'sheet':sheet,'total':len(rows),'items':rows[:limit]}

# Mission ranking retains the feature matrix and weights authored in the supplied frontend.
@app.get('/api/mission/rank')
def mission_rank(habitat:str='Moon base',limit:int=12):
 cat=DATASETS['catalogue']; scenario=next((x for x in cat['scen'] if x['name'].casefold()==habitat.casefold()),None)
 if not scenario: raise HTTPException(422,detail={'message':'Unknown habitat','available':[x['name'] for x in cat['scen']]})
 weights=scenario['w']; feats=cat['feat']; ranked=[]
 for inv in cat['inv']:
  vector=cat['codes'].get(inv['ID'],[0]*len(weights)); denom=sum(weights) or 1
  score=10*sum(float(a or 0)*float(b) for a,b in zip(vector,weights))/denom
  contributions=sorted([{'feature':feats[i],'value':float(v or 0),'weight':float(weights[i]),'contribution':float(v or 0)*float(weights[i])} for i,v in enumerate(vector)],key=lambda z:z['contribution'],reverse=True)
  ranked.append({'id':inv['ID'],'investigation':inv['Investigation'],'acronym':inv['Acronym'],'score':round(score,2),'relevance':inv['Spacecraft-fire relevance'],'platform':inv['Platform / facility'],'fuel':inv['Fuel / sample'],'gravity':inv['Gravity regime'],'data_quality':inv['Data quality'],'sources':inv['Sources'],'top_reasons':contributions[:3]})
 ranked.sort(key=lambda x:(-x['score'],x['id']))
 return {'habitat':scenario['name'],'method':'Original frontend weighted feature score: 10 × weighted feature sum / sum of scenario weights. This is a transparent relevance heuristic, not a trained model or safety certification.','weights':dict(zip(feats,weights)),'items':ranked[:max(1,min(limit,24))]}

# Rule-based, evidence-grounded retrieval assistant. Optional Ollama is not required.
class Ask(BaseModel): question:str=Field(min_length=4,max_length=1200); habitat:str|None=None

def corpus():
 out=[]
 for group in ['inv','tc','hw','atm','grav','cases','earth']:
  for r in DATASETS['catalogue'].get(group,[]): out.append({'kind':group,'id':r.get('ID') or r.get('Row_ID') or r.get('name') or r.get('Hardware'),'text':evidence_text(r),'record':r,'sources':r.get('Sources','')})
 for group in ['accidents','flame','phenomena','temps','mechanisms','propellants']:
  for r in DATASETS['flame'].get(group,[]): out.append({'kind':group,'id':r.get('id'),'text':evidence_text(r),'record':r,'sources':r.get('src','')})
 for r in DATASETS['prevention']['measures']: out.append({'kind':'prevention_measure','id':r.get('measure_id'),'text':evidence_text(r),'record':r,'sources':r.get('source_ids','')})
 return out
CORPUS=corpus(); CORPUS_TEXT=[x['text'] for x in CORPUS]
VECT=TfidfVectorizer(stop_words='english',ngram_range=(1,2),max_features=25000).fit(CORPUS_TEXT)
MATRIX=VECT.transform(CORPUS_TEXT)
@app.post('/api/assistant/ask')
def assistant_ask(payload:Ask):
 q=payload.question.strip()
 habitat=(payload.habitat or 'Moon base').strip()
 # The assistant shares the exact weighted mission-ranking engine used by the
 # Mission Intelligence panel, so habitat selection affects retrieval context.
 try:
  mission=mission_rank(habitat,limit=5)
 except HTTPException:
  raise HTTPException(422,detail={'message':'Unknown habitat','available':[x['name'] for x in DATASETS['catalogue']['scen']]})
 qv=VECT.transform([q]); scores=cosine_similarity(qv,MATRIX).ravel(); idx=np.argsort(scores)[::-1][:8]
 hits=[{**CORPUS[i],'_similarity':float(scores[i])} for i in idx if scores[i]>.025]
 top=mission['items'][:3]
 mission_lines=[f"{x['acronym']} ({x['investigation']}, relevance {x['score']}/10): {x.get('relevance','')}" for x in top]
 mission_context={'habitat':mission['habitat'],'ranking_method':mission['method'],'top_investigations':top}
 citations=[]
 for h in hits[:5]:
  raw=h.get('sources',''); ids=[x.strip() for x in re.split(r'[;,]',str(raw)) if x.strip()]
  for sid in ids:
   src=srcmap().get(sid)
   if src and sid not in [c['id'] for c in citations]: citations.append({'id':sid,'title':src.get('title'),'url':src.get('url'),'grade':src.get('grade')})
 if not hits:
  answer=(f"Mission context for {mission['habitat']}: the current weighted relevance ranking prioritises "
          + '; '.join(mission_lines) + ". I could not retrieve sufficiently relevant records for the specific question. "
          "Try naming an investigation, fuel, atmosphere, gravity level, fire-safety control or accident.")
  return {'answer':answer,'mode':'mission-aware local evidence retrieval','records_used':[],'citations':citations,'mission_context':mission_context,'limitations':['No relevant indexed record crossed the retrieval threshold.','The ranking is a transparent relevance heuristic, not a trained model or fire-risk prediction.']}
 # Extractive evidence remains the default; the assistant must distinguish evidence
 # from the mission relevance heuristic and must not fabricate missing results.
 lines=[]
 for h in hits[:5]:
  r=h['record']; title=r.get('Investigation') or r.get('name') or r.get('q') or r.get('measure_description') or r.get('phenomenon') or h['id']
  body=r.get('key_findings') or r.get('fire_safety_relevance') or r.get('objective') or r.get('Outcome') or r.get('measure_description') or r.get('why') or r.get('notes') or h['text']
  lines.append(f"• {title}: {str(body)[:520]}")
 answer=(f"Mission context: {mission['habitat']}. The current weighted relevance ranking prioritises "
         + '; '.join(mission_lines) + ".\n\nEvidence retrieved from the project data:\n" + '\n'.join(lines))
 mode='mission-aware TF-IDF retrieval + extractive evidence synthesis'
 model=os.getenv('OLLAMA_MODEL','').strip(); ollama=os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')
 if model:
  prompt=('You are the FLARE-X research assistant. Answer using ONLY the evidence and mission ranking below. '
          'Treat ranking scores as relevance heuristics, not fire probabilities or model confidence. '
          'If evidence is insufficient, say so. Do not invent numbers or claim a model is validated. '
          'Distinguish reported observations from inference. Cite source IDs in square brackets. '
          f"\n\nMISSION / HABITAT: {mission['habitat']}\nTOP RELEVANT INVESTIGATIONS (heuristic ranking):\n"+
          '\n'.join(mission_lines)+'\n\nRETRIEVED EVIDENCE:\n'+'\n'.join(lines)+'\n\nQUESTION: '+q)
  try:
   req=urllib.request.Request(ollama+'/api/generate',data=json.dumps({'model':model,'prompt':prompt,'stream':False}).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=45) as response: generated=json.loads(response.read().decode()).get('response','').strip()
   if generated: answer=generated; mode='mission-aware local Ollama generation grounded in retrieved project evidence'
  except Exception: mode+=' (Ollama unavailable; extractive fallback used)'
 caveats=['Default mode is local TF-IDF retrieval with extractive synthesis. Set OLLAMA_MODEL to enable optional local Ollama generation; no paid/cloud API is used.','Mission rankings use the project weighted-feature heuristic and do not predict fire probability.','Investigation metadata and narrative summaries are not equivalent to raw experimental time-series data.','Use source links to verify context, scope and evidence grade before engineering decisions.']
 return {'answer':answer,'mode':mode,'records_used':[{'kind':h['kind'],'id':h['id'],'similarity':round(float(h['_similarity']),3)} for h in hits[:5]],'citations':citations,'mission_context':mission_context,'limitations':caveats}

# Reproducible integrity and physics checks, each with formula, inputs, outputs and status.
@app.get('/api/validation/report')
def validation_report():
 f=DATASETS['flame']; c=DATASETS['catalogue']; p=DATASETS['prevention']; sources=srcmap(); checks=[]
 def add(name,passed,detail,formula=None,inputs=None,result=None): checks.append({'check':name,'status':'PASS' if passed else 'REVIEW','detail':detail,'formula':formula,'inputs':inputs,'result':result})
 temps=[t for t in f['temps'] if t.get('gray')=='Y' and isinstance(t.get('K'),(int,float)) and isinstance(t.get('wien'),(int,float))]
 errors=[]
 for t in temps:
  calc=2897.77/float(t['K'])*1000 # nm, constant expressed um K
  errors.append({'id':t['id'],'stored_nm':t['wien'],'recomputed_nm':round(calc,1),'abs_error_nm':round(abs(calc-float(t['wien'])),1)})
 add('Wien displacement law',all(x['abs_error_nm']<=1.5 for x in errors),f'{sum(x["abs_error_nm"]<=1.5 for x in errors)}/{len(errors)} rows within 1.5 nm tolerance. This checks arithmetic consistency, not pyrometer calibration.','lambda_max(nm) = 2,897,770 / T(K)',{'rows':[{t['id']:t['K']} for t in temps]},errors)
 tmap={t['id']:t for t in f['temps']};
 if 'T06' in tmap and 'T07' in tmap:
  delta=float(tmap['T06']['K'])-float(tmap['T07']['K']); add('Methane oxygen/air temperature difference',abs(delta-826)<2,f'Computed difference {delta:.1f} K; frontend workbook note says approximately 826 K. These are listed source values, not a new combustion simulation.','Delta T = T06.K - T07.K',{'T06_K':tmap['T06']['K'],'T07_K':tmap['T07']['K']},{'delta_K':delta,'reference_delta_K':826})
 src_ids=set(sources); cited=[]
 for row in f['accidents']+f['flame']+f['timeline']+f['components']:
  raw=row.get('src',''); cited += [x.strip() for x in str(raw).split(';') if x.strip()]
 missing=sorted(set(cited)-src_ids); add('Flame dataset source resolution',not missing,f'{len(set(cited))-len(missing)} unique cited IDs resolve; missing: {missing or "none"}.',inputs={'unique_cited_ids':len(set(cited))},result={'missing_source_ids':missing})
 orphan=[r.get('id') for r in f['flame'] if r.get('id') not in {a.get('id') for a in f['accidents']}]; add('Flame-to-accident linkage',not orphan,f'{len(f["flame"])-len(orphan)}/{len(f["flame"])} flame records link to an accident.',result={'orphans':orphan})
 dup=len(p['measures'])-len({m.get('measure_id') for m in p['measures']}); add('Prevention measure ID uniqueness',dup==0,f'{len(p["measures"])} measures; duplicate IDs: {dup}.',result={'duplicate_count':dup})
 unlinked=[m.get('measure_id') for m in p['measures'] if m.get('accident_id') not in {a.get('accident_id') for a in p['accidents']}]; add('Prevention-to-accident linkage',not unlinked,f'{len(p["measures"])-len(unlinked)}/{len(p["measures"])} measures link to a prevention accident record.',result={'unlinked_measure_ids':unlinked})
 # Test-condition rows have metadata and selected numeric conditions, not raw time-series traces.
 tc=c['tc']; numeric={k:sum(isinstance(r.get(k),(int,float)) and not isinstance(r.get(k),bool) for r in tc) for k in ['O2_min_pct','O2_max_pct','Pressure_psia','Flow_min_cm_s','Flow_max_cm_s','Gravity_g']}
 add('Experimental condition coverage',len(tc)>0,f'{len(tc)} condition rows; numeric value counts: {numeric}. Missing fields are not imputed.',result=numeric)
 return {'generated_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'passed':sum(x['status']=='PASS' for x in checks),'review':sum(x['status']=='REVIEW' for x in checks),'scientific_scope':'Integrity checks validate internal consistency and selected equations only. They do not validate a flame-spread predictor or certify a fire-safety design.','data_limitations':['The uploaded Excel workbook has 14 accidents, 66 timeline events, 55 damaged-component rows, 19 PSI combustion catalogue rows and 20 source rows.','The frontend embeds a separate catalogue of 24 investigations and 20 experimental condition summaries, plus 18 temperature records.','The supplied material does not contain a general raw, synchronized flame/temperature time-series suitable for training and independently validating a predictive flame-spread model.']}

@app.get('/api/analysis/temperature')
def temperature_analysis():
 rows=[r for r in DATASETS['flame']['temps'] if isinstance(r.get('K'),(int,float))]
 vals=np.array([float(r['K']) for r in rows]); measured=[r for r in rows if r.get('basis')=='Measured']
 return {'method':'Descriptive statistics over temperature records with numeric K values; records retain mixed evidence bases and are not pooled as one physical population.','n':int(len(vals)),'mean_K':float(vals.mean()),'median_K':float(np.median(vals)),'std_population_K':float(vals.std(ddof=0)),'min_K':float(vals.min()),'max_K':float(vals.max()),'records':rows,'measured_record_count':len(measured),'limitations':['Temperature entries include measured, computed and theoretical values from different contexts. Do not interpret the aggregate mean as a characteristic spacecraft fire temperature.']}

@app.post('/api/analysis/upload')
async def analyse_upload(file:UploadFile=File(...),time_column:str|None=None):
 raw=await file.read()
 try:
  if file.filename.lower().endswith('.csv'): df=pd.read_csv(io.BytesIO(raw))
  elif file.filename.lower().endswith(('.xlsx','.xls')): df=pd.read_excel(io.BytesIO(raw))
  else: raise HTTPException(415,'Upload CSV or XLSX')
 except HTTPException: raise
 except Exception as e: raise HTTPException(400,f'Could not read file: {e}')
 numeric=df.select_dtypes(include='number'); summary={}
 for col in numeric:
  s=numeric[col].dropna(); summary[col]={'n':int(s.size),'missing':int(numeric[col].isna().sum()),'mean':float(s.mean()) if len(s) else None,'median':float(s.median()) if len(s) else None,'std_sample':float(s.std(ddof=1)) if len(s)>1 else None,'min':float(s.min()) if len(s) else None,'max':float(s.max()) if len(s) else None}
 corr=numeric.corr().replace({np.nan:None}).to_dict() if len(numeric.columns)>1 else {}
 trend=None
 if time_column and time_column in df.columns:
  for col in numeric.columns:
   if col==time_column: continue
   z=df[[time_column,col]].dropna()
   if len(z)>=3:
    slope,intercept,r,pv,se=stats.linregress(z[time_column].astype(float),z[col].astype(float)); trend[col]={'slope_per_time_unit':float(slope),'intercept':float(intercept),'r_squared':float(r*r),'p_value':float(pv),'standard_error':float(se)}
 digest=hashlib.sha256(raw).hexdigest()
 return {'filename':file.filename,'sha256':digest,'rows':int(len(df)),'columns':list(df.columns),'numeric_summary':summary,'correlation':corr,'linear_trend':trend,'reproducibility':{'algorithm':'Pandas descriptive statistics; SciPy linregress for requested time column','input_sha256':digest,'missing_values_are_not_imputed':True},'warning':'Statistical description only. This endpoint does not infer chemical kinetics, flammability limits, or flame spread without an appropriate validated model and relevant measured variables.'}

@app.get('/api/recommendations')
def recommendations(habitat:str='Moon base'):
 rank=mission_rank(habitat,limit=8); top=rank['items']; measures=DATASETS['prevention']['measures']
 # Evidence-to-control recommendations are explicitly conditional, not certification.
 measures=DATASETS['prevention']['measures']
 def find_measure(mid): return next((m for m in measures if m.get('measure_id')==mid),None)
 selected=[find_measure('PM-001'),find_measure('PM-002')]
 historical=[{'priority':'1','recommendation':m.get('measure_description'),'basis':m.get('failure_mode_addressed'),'type':m.get('prevention_category'),'evidence_ids':[m.get('measure_id')],'evidence_grade':m.get('evidence_grade'),'status':m.get('measure_status')} for m in selected if m]
 controls=historical+[
 {'priority':'3','recommendation':'Design fire detection and post-event atmosphere monitoring for smoke/aerosol and toxic combustion products, not temperature alone.','basis':'Saffire measurements and smoke-characterisation investigations; verify sensor performance for the selected atmosphere and materials.','type':'Detection / monitoring','evidence_ids':['R37','R38'],'evidence_grade':'Primary NASA reports / project catalogue'},
 {'priority':'4','recommendation':'Do not assume visible flame disappearance means complete extinction; include post-suppression verification and atmosphere monitoring in procedures.','basis':'FLEX cool-flame result; cool flame was inferred rather than directly imaged and was observed for droplet combustion.','type':'Suppression verification','evidence_ids':['R19','R14'],'evidence_grade':'Research summary / primary report'},
 {'priority':'5','recommendation':'Require material, geometry and flow tests in mission-relevant conditions before extrapolating 1-g screening results to partial gravity.','basis':'Saffire and BASS findings; partial-gravity experimental coverage remains limited in the supplied catalogue.','type':'Qualification / testing','evidence_ids':['R36','R37','R28'],'evidence_grade':'NASA / experiment reports'}
 ]
 for item in controls:
  item['supporting_references']=[{'id':sid,'title':srcmap().get(sid,{}).get('title'),'url':srcmap().get(sid,{}).get('url')} for sid in item['evidence_ids'] if srcmap().get(sid)]
 return {'habitat':habitat,'ranked_investigations':top[:5],'recommendations':controls,'limitations':['Recommendations are research-informed design considerations, not certified engineering requirements or operational emergency procedures.','The ranking is the frontend weighted heuristic; it does not predict fire probability.','Validate atmosphere, materials, ventilation, detector and suppression performance for the actual habitat design.']}
