from modules.intelligence import keywords,linking,schema_for,validate_schema,geo_audit,prioritize,calendar,business_profile

def sample():
 return [{'url':'https://example.com/','title':'Network Software Platform','description':'Network automation software','h1':'Network Automation','text':'Network automation software helps providers manage network operations and workflows.','links':[],'schema_types':[]}, {'url':'https://example.com/network/','title':'Network Operations Guide','description':'Network monitoring operations','h1':'Network Monitoring','text':'Network automation and monitoring for network operations.','links':[],'schema_types':[]}]

def test_keywords_clusters():
 k,c=keywords(sample());assert k and c

def test_linking():
 assert isinstance(linking(sample()),list)

def test_schema():
 p=business_profile(sample());obj=schema_for(p,sample());assert not validate_schema(obj)

def test_geo():
 assert len(geo_audit(sample()))==10

def test_priority():
 p=prioritize([{'issue':'Missing title','severity':'High','url':'https://example.com','recommendation':'Add title'}],business_profile(sample()));assert p[0]['priority_score']>0

def test_calendar():
 assert len(calendar(business_profile(sample()),keywords(sample())[0],[]))==12
