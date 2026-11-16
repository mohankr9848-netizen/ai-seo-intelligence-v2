"""Offline SEO strategy heuristics. No fabricated search metrics or AI claims."""
import re, math, json
from collections import Counter, defaultdict
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

STOP=set(ENGLISH_STOP_WORDS)|{'home','read','more','click','contact','privacy','terms','cookie','cookies','copyright'}

def tokens(s):
    return [x for x in re.findall(r'[a-z][a-z0-9-]{2,}', (s or '').lower()) if x not in STOP]

def business_profile(pages, override=''):
    if not pages: return {'business':'Unknown','topics':[],'audience':'Not determined'}
    seed=pages[:min(8,len(pages))]
    words=Counter(w for p in seed for w in tokens(' '.join([p.get('title',''),p.get('h1',''),p.get('description','')])) )
    topics=[w for w,n in words.most_common(12)]
    return {'business':override.strip() or (seed[0].get('title') or urlsplit(seed[0]['url']).hostname)[:100], 'topics':topics,'audience':'Review manually; not inferred reliably'}

def keywords(pages, n_clusters=5):
    docs=[]; urls=[]
    for p in pages:
        t=' '.join([p.get('title','')]*3+[p.get('h1','')]*2+[p.get('description',''),p.get('text','')[:4000]])
        if tokens(t): docs.append(t);urls.append(p['url'])
    if not docs:return [],[]
    v=TfidfVectorizer(stop_words='english',ngram_range=(1,2),max_features=400,min_df=1)
    X=v.fit_transform(docs)
    terms=v.get_feature_names_out()
    weights=X.sum(axis=0).A1
    ranked=sorted(zip(terms,weights),key=lambda x:-x[1])
    candidates=[{'keyword':term,'relative_relevance':round(float(score),3),'search_volume':'Not available','difficulty':'Not available','intent': ('Commercial' if any(x in term for x in ['software','service','solution','pricing','platform','agency','buy']) else 'Informational / review'),'source':'On-site content'} for term,score in ranked[:min(60,len(ranked))] if len(term)>3]
    k=min(max(1,n_clusters),len(docs))
    labels=KMeans(n_clusters=k,random_state=42,n_init=10).fit_predict(X) if k>1 else [0]*len(docs)
    groups=defaultdict(list)
    for i,label in enumerate(labels):groups[int(label)].append(i)
    clusters=[]
    for label,idx in groups.items():
        sums=X[idx].sum(axis=0).A1
        top=[terms[j] for j in sums.argsort()[-6:][::-1]]
        clusters.append({'cluster':f'Topic {label+1}: {top[0]}','keywords':', '.join(top),'pages':len(idx),'example_url':urls[idx[0]]})
    return candidates,clusters

def linking(pages,limit=35):
    if len(pages)<2:return []
    docs=[' '.join([p.get('title',''),p.get('h1',''),p.get('description',''),p.get('text','')[:2500]]) or p['url'] for p in pages]
    X=TfidfVectorizer(stop_words='english').fit_transform(docs)
    sim=cosine_similarity(X)
    out=[]
    for i,source in enumerate(pages):
        existing=set(source.get('links',[]))
        for j,target in enumerate(pages):
            if i==j or target['url'] in existing or sim[i,j]<0.08:continue
            out.append({'source_url':source['url'],'target_url':target['url'],'suggested_anchor':(target.get('h1') or target.get('title') or 'Related resource')[:85], 'similarity':round(float(sim[i,j]),3),'reason':'Topical similarity; editorial review required'})
    return sorted(out,key=lambda x:-x['similarity'])[:limit]

def competitor_gaps(own,competitor_pages):
    own_terms=set(w for p in own for w in tokens(' '.join([p.get('title',''),p.get('h1',''),p.get('description','')])))
    out=[]
    for domain,pages in competitor_pages.items():
        freq=Counter(w for p in pages for w in tokens(' '.join([p.get('title',''),p.get('h1',''),p.get('description','')])))
        for term,count in freq.most_common(40):
            if term not in own_terms and count>=1:
                out.append({'competitor':domain,'topic_term':term,'mentions':count,'finding':'Term appears in competitor metadata/headings but not your crawled metadata/headings','confidence':'Exploratory'})
    return out[:75]

def geo_audit(pages):
    out=[]
    for p in pages:
        checks=[('Clear primary heading',bool(p.get('h1')),'Add a clear descriptive H1.'),('Meta description',bool(p.get('description')),'Summarize page purpose in metadata.'),('Structured data',bool(p.get('schema_types')),'Consider accurate relevant structured data.'),('Substantial extractable text',len(p.get('text',''))>=300,'Provide useful crawlable text and answers.'),('Question-answer formatting',bool(re.search(r'\b(what|how|why|when|who|faq)\b',p.get('text','')[:3500],re.I)),'Consider relevant FAQs where helpful.')]
        for name,passed,advice in checks:out.append({'url':p['url'],'check':name,'passed':passed,'recommendation':advice})
    return out

def schema_for(profile, pages, schema_type='Organization'):
    host=urlsplit(pages[0]['url']) if pages else None
    base=f'{host.scheme}://{host.netloc}/' if host else ''
    if schema_type=='WebSite':obj={'@context':'https://schema.org','@type':'WebSite','name':profile['business'],'url':base}
    elif schema_type=='Service':obj={'@context':'https://schema.org','@type':'Service','name':'REPLACE: service name','provider':{'@type':'Organization','name':profile['business'],'url':base}}
    elif schema_type=='FAQPage':obj={'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':'REPLACE: question','acceptedAnswer':{'@type':'Answer','text':'REPLACE: accurate answer'}}]}
    else:obj={'@context':'https://schema.org','@type':'Organization','name':profile['business'],'url':base}
    return obj

def validate_schema(data):
    issues=[]
    if not isinstance(data,dict):return ['Root must be a JSON object.']
    if data.get('@context')!='https://schema.org':issues.append('Use https://schema.org as @context.')
    if not data.get('@type'):issues.append('Missing @type.')
    if any('REPLACE:' in str(v) for v in data.values()):issues.append('Template placeholders must be replaced with factual information.')
    if not data.get('name') and data.get('@type') in ('Organization','WebSite','Service'):issues.append('Missing name.')
    return issues

def prioritize(issues, profile):
    severity={'High':4,'Medium':3,'Low':2,'Info':1}
    groups=defaultdict(list)
    for x in issues:groups[x['issue']].append(x)
    result=[]
    for name,rows in groups.items():
        impact=severity.get(rows[0]['severity'],2)
        reach=min(5,1+math.log2(len(rows)))
        effort=2 if any(x in name.lower() for x in ['title','description','h1','alt']) else 3
        confidence=4 if rows[0]['severity']!='Info' else 2
        score=round((impact*0.45+reach*0.25+confidence*0.3)/effort*20,1)
        result.append({'opportunity':name,'affected_pages':len(rows),'severity':rows[0]['severity'],'priority_score':score,'effort_estimate':('Low' if effort==2 else 'Medium'),'recommendation':rows[0]['recommendation'],'sample_url':rows[0]['url']})
    return sorted(result,key=lambda r:-r['priority_score'])

def calendar(profile, keywords_list, opportunities, days=90):
    topics=[x['keyword'] for x in keywords_list if len(x['keyword'].split())>1][:12]
    if not topics:topics=profile['topics'][:12] or ['business overview']
    out=[]
    for i in range(12):
        topic=topics[i%len(topics)]
        out.append({'week':i+1,'day':1+i*7,'topic':topic,'working_title':f'{topic.title()}: Practical Guide and Key Questions','format':'Guide' if i%3 else 'FAQ / explainer','intent':'Informational (estimated)','action':'Verify demand, audience fit, uniqueness and accuracy before publishing'})
    return out

def strategy(profile, priority, calendar_rows, gaps):
    return [
      {'period':'Days 1–30','focus':'Technical foundation','actions':'Resolve high-severity crawl findings, validate indexability and review canonicals.','evidence':f'{len(priority)} distinct issue types identified'},
      {'period':'Days 31–60','focus':'Information architecture and content','actions':'Review keyword clusters, add contextual internal links and publish validated topic briefs.','evidence':f'{len(calendar_rows)} draft content briefs'},
      {'period':'Days 61–90','focus':'Expansion and measurement','actions':'Review competitor topic hypotheses, add accurate schema and connect Search Console for measured outcomes.','evidence':f'{len(gaps)} exploratory competitor gaps'}]
