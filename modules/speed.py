"""Optional PageSpeed Insights diagnostics; API quota/availability dependent."""
import requests

def inspect(url, api_key=''):
    rows=[]
    for strategy in ('mobile','desktop'):
        try:
            params={'url':url,'strategy':strategy,'category':'performance'}
            if api_key:params['key']=api_key
            r=requests.get('https://www.googleapis.com/pagespeedonline/v5/runPagespeed',params=params,timeout=35)
            r.raise_for_status()
            data=r.json()
            lighthouse=data.get('lighthouseResult',{})
            audits=lighthouse.get('audits',{})
            crux=data.get('loadingExperience',{}).get('metrics',{})
            def metric(k):
                v=audits.get(k,{})
                return v.get('displayValue','Not available')
            rows.append({'device':strategy,'performance_score':round(100*lighthouse.get('categories',{}).get('performance',{}).get('score',0)),'LCP_lab':metric('largest-contentful-paint'),'CLS_lab':metric('cumulative-layout-shift'),'INP_field':crux.get('INTERACTION_TO_NEXT_PAINT',{}).get('percentile','Not available'),'LCP_field':crux.get('LARGEST_CONTENTFUL_PAINT_MS',{}).get('percentile','Not available'),'CLS_field':crux.get('CUMULATIVE_LAYOUT_SHIFT_SCORE',{}).get('percentile','Not available'),'note':'Lab and field metrics differ; field data may be absent.'})
        except (requests.RequestException,ValueError,KeyError) as exc:
            rows.append({'device':strategy,'error':str(exc)[:220]})
    return rows
