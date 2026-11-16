"""SEO Intelligence: all-in-one, zero-paid-API Streamlit prototype."""
import json
import streamlit as st
import pandas as pd
from urllib.parse import urlsplit
from modules.crawler import crawl_website, CrawlError
from modules.intelligence import business_profile,keywords,linking,competitor_gaps,geo_audit,schema_for,validate_schema,prioritize,calendar,strategy
from modules.speed import inspect
from modules.report import pdf_report

st.set_page_config(page_title='SEO Intelligence | Free SEO Audit',page_icon='🔎',layout='wide')
st.title('🔎 SEO Intelligence')
st.caption('All-in-one SEO audit & business-specific strategy prototype • No paid APIs required')
st.info('Prototype: bounded public-page crawling; keyword volume, competitor rankings and AI citations are NOT measured. Use only on sites you own or are authorized to assess. Do not expose to unrestricted public traffic without network-level SSRF controls and abuse protection.',icon='⚠️')
with st.sidebar:
    st.header('Audit setup')
    url=st.text_input('Website URL',placeholder='https://example.com')
    business=st.text_input('Business description (optional)',placeholder='e.g., B2B network software provider')
    competitors=st.text_area('Competitor URLs (optional, one per line)',height=100,placeholder='https://competitor-one.com\nhttps://competitor-two.com')
    max_pages=st.slider('Own website pages',2,50,15)
    comp_pages=st.slider('Pages per competitor',1,12,5)
    run_speed=st.checkbox('Run PageSpeed diagnostics (external API)',value=False)
    api_key=st.text_input('Optional PageSpeed API key',type='password',help='Can be left blank; unauthenticated access may be limited or unavailable.')
    start=st.button('🚀 Run complete SEO analysis',type='primary',use_container_width=True)
    st.caption('Crawls are synchronous and may take several minutes. No login or persistence is provided.')

if start:
    if not url.strip():st.error('Enter a website URL.');st.stop()
    with st.status('Analyzing website and competitors...',expanded=True) as status:
        try:
            st.write('Crawling target website...')
            own=crawl_website(url,max_pages=max_pages)
            if not own['pages']:raise CrawlError('No eligible HTML pages were crawled. Check robots.txt and URL.')
            profile=business_profile(own['pages'],business)
            st.write('Extracting keyword candidates and topic clusters...')
            kw,clusters=keywords(own['pages'])
            links=linking(own['pages'])
            competitor_results={}; competitor_errors=[]
            for raw in [x.strip() for x in competitors.splitlines() if x.strip()][:3]:
                st.write('Sampling competitor: '+raw)
                try:
                    result=crawl_website(raw,max_pages=comp_pages)
                    competitor_results[urlsplit(result['pages'][0]['url']).hostname if result['pages'] else raw]=result['pages']
                except CrawlError as exc:competitor_errors.append(f'{raw}: {exc}')
            gaps=competitor_gaps(own['pages'],competitor_results)
            geo=geo_audit(own['pages'])
            priority=prioritize(own['issues'],profile)
            cal=calendar(profile,kw,priority)
            road=strategy(profile,priority,cal,gaps)
            speed=inspect(own['pages'][0]['url'],api_key) if run_speed else []
            st.session_state['audit']={'url':own['pages'][0]['url'],'profile':profile,'pages':own['pages'],'issues':own['issues'],'errors':own['errors'],'robots_status':own['robots_status'],'sitemap_status':own.get('sitemap_status','Not checked'),'keywords':kw,'clusters':clusters,'links':links,'gaps':gaps,'geo':geo,'priorities':priority,'calendar':cal,'strategy':road,'speed':speed,'competitor_errors':competitor_errors}
            status.update(label='Analysis completed',state='complete')
        except (CrawlError,ValueError,RuntimeError) as exc:
            status.update(label='Analysis could not complete',state='error')
            st.error(str(exc))

if 'audit' not in st.session_state:
    st.markdown('### What the tool analyzes')
    for name,desc in [('AI Keyword Research & Clustering','On-site keyword extraction, relevance scores and topic grouping'),('Competitor Content Gap Analyzer','Competitor page samples and missing topic-term hypotheses'),('Internal Linking Opportunity Finder','Contextually similar pages without existing links'),('Core Web Vitals & Speed Diagnostics','Optional Google PageSpeed API, lab metrics and available field metrics'),('AI Content Strategy & Calendar Generator','12-week editorial suggestions and 90-day roadmap'),('Schema Markup Generator & Validator','Editable JSON-LD templates and local structural checks'),('AI Search Readiness Audit (GEO)','Heuristic checks for clear content, answers and structured data'),('SEO Opportunity Prioritization Engine','Transparent weighted impact, reach, confidence and effort scoring'),('Client-Ready SEO Audit & Strategy Report','Downloadable PDF and CSV exports')]:
        st.write(f'**{name}** — {desc}')
    st.stop()

r=st.session_state['audit']
st.subheader('Overview')
a,b,c,d=st.columns(4)
a.metric('Pages crawled',len(r['pages']))
b.metric('Technical findings',len(r['issues']))
c.metric('Keyword candidates',len(r['keywords']))
d.metric('Link suggestions',len(r['links']))
st.caption('These are counts of observed items or generated hypotheses, not a Google ranking score.')
tabs=st.tabs(['Technical SEO','Keyword clusters','Competitor gaps','Internal links','Core Web Vitals','Content strategy','Schema markup','GEO readiness','Priorities','Client report'])

def table(rows,filename=None):
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df,use_container_width=True,hide_index=True)
        if filename:st.download_button('⬇ Download '+filename,df.to_csv(index=False).encode('utf-8'),filename,mime='text/csv',key=filename)
    else:st.info('No data found in the sampled pages.')

with tabs[0]:
    st.write('**Robots:**',r['robots_status'],' | **Sitemap:**',r['sitemap_status'])
    st.caption('Sitemap support reads a direct /sitemap.xml and does not recursively resolve sitemap indexes.')
    st.subheader('Technical issues');table(r['issues'],'technical_issues.csv')
    st.subheader('Crawled pages')
    fields=['url','status','title','description','h1','h1_count','canonical','noindex','image_count','missing_alt']
    table([{k:p.get(k,'') for k in fields} for p in r['pages']],'pages.csv')
    with st.expander('Crawl errors / skipped pages'):table(r['errors'])
with tabs[1]:
    st.caption('Relevance is relative to crawled content. No paid keyword volume or difficulty data is used.')
    st.subheader('Keyword candidates');table(r['keywords'],'keywords.csv')
    st.subheader('Topic clusters');table(r['clusters'],'clusters.csv')
with tabs[2]:
    st.caption('These are sampled competitor content terms absent from your sampled titles, descriptions and H1s. They are NOT verified ranking gaps.')
    table(r['gaps'],'competitor_gaps.csv')
    for err in r['competitor_errors']:st.warning(err)
with tabs[3]:
    st.caption('Suggestions are based on TF-IDF topical similarity; confirm editorial relevance and existing navigation before applying.')
    table(r['links'],'internal_links.csv')
with tabs[4]:
    if not r['speed']:st.info('Enable PageSpeed diagnostics in the sidebar and rerun. Google may enforce API quotas or require a key.')
    else:table(r['speed'],'pagespeed.csv')
    st.caption('LCP, INP and CLS field metrics may be unavailable; Lighthouse lab results are not the same as real-user Core Web Vitals.')
with tabs[5]:
    st.subheader('12-week content calendar');table(r['calendar'],'content_calendar.csv')
    st.subheader('Business-specific 90-day roadmap');table(r['strategy'],'strategy.csv')
    st.caption('Titles and intent are heuristically generated draft suggestions, not validated AI editorial output.')
with tabs[6]:
    schema_type=st.selectbox('Schema template',['Organization','WebSite','Service','FAQPage'])
    generated=schema_for(r['profile'],r['pages'],schema_type)
    raw=st.text_area('Editable JSON-LD',value=json.dumps(generated,indent=2),height=290,key=f'schema_{schema_type}')
    try:
        obj=json.loads(raw);problems=validate_schema(obj)
        if problems:
            for problem in problems:st.warning(problem)
        else:st.success('Basic local structural checks passed. This does NOT verify Google rich-result eligibility or full Schema.org semantics.')
        st.download_button('⬇ Download JSON-LD',raw,'schema.jsonld','application/ld+json')
    except json.JSONDecodeError as exc:st.error('Invalid JSON: '+str(exc))
    st.markdown('[Google Rich Results Test](https://search.google.com/test/rich-results) · [Schema.org Validator](https://validator.schema.org/)')
with tabs[7]:
    st.caption('Readiness checklist only. It cannot measure citations in ChatGPT, Google AI Overviews or other AI search engines.')
    passed=sum(x['passed'] for x in r['geo'])
    st.metric('Heuristic checklist completion',f'{passed}/{len(r["geo"])}')
    table(r['geo'],'geo_readiness.csv')
with tabs[8]:
    st.caption('Illustrative score = weighted impact, reach and confidence divided by estimated effort. Scores are not forecast traffic or revenue.')
    table(r['priorities'],'priorities.csv')
with tabs[9]:
    st.write('**Report website:**',r['url'])
    st.write('**Business context:**',r['profile']['business'])
    st.write('**Included:** technical findings, keyword ideas, competitor hypotheses, 90-day roadmap and 12-week calendar.')
    try:
        pdf=pdf_report(r)
        st.download_button('📄 Download client-ready PDF',pdf,'seo_intelligence_audit.pdf','application/pdf',type='primary')
    except Exception as exc:st.error('PDF generation failed: '+str(exc))
    export={k:v for k,v in r.items() if k!='pages'}
    st.download_button('⬇ Download complete JSON data',json.dumps(export,indent=2,default=str).encode(),'seo_audit_data.json','application/json')
