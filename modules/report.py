"""Generate a client-readable PDF without paid services."""
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch

def pdf_report(result):
    buffer=BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=(595,842),rightMargin=42,leftMargin=42,topMargin=45,bottomMargin=45)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CoverTitleX',parent=styles['Title'],fontSize=21,leading=26,textColor=colors.HexColor('#174A8B'),spaceAfter=16))
    story=[]
    def para(t,sty='BodyText'):
        story.append(Paragraph(escape(str(t)),styles[sty]));story.append(Spacer(1,9))
    para('SEO Intelligence | Website Audit & Strategy','CoverTitleX')
    para('Website: '+result['url']);para('Business context: '+result['profile']['business'])
    para('This report combines measured crawl findings with heuristic recommendations. It does not contain verified search volume, rankings, or AI citation measurements.')
    para('Executive summary','Heading2')
    para(f"Pages crawled: {len(result['pages'])} | Technical findings: {len(result['issues'])} | Content topics: {len(result['keywords'])} | Competitor gap hypotheses: {len(result['gaps'])}")
    para('Top technical priorities','Heading2')
    for item in result['priorities'][:12]:
        para(f"{item['opportunity']} ({item['severity']}, {item['affected_pages']} pages): {item['recommendation']} Example: {item['sample_url']}")
    para('Keyword opportunities (on-site relevance, not search volume)','Heading2')
    for item in result['keywords'][:15]:para(item['keyword']+' — '+item['intent'])
    para('Competitor topic hypotheses','Heading2')
    if not result['gaps']:para('No competitor comparison supplied or no gaps found in the sampled pages.')
    for item in result['gaps'][:12]:para(item['competitor']+': '+item['topic_term'])
    para('90-day SEO roadmap','Heading2')
    for item in result['strategy']:para(item['period']+' — '+item['focus']+': '+item['actions'])
    para('12-week editorial calendar','Heading2')
    for item in result['calendar']:para(f"Week {item['week']}: {item['working_title']}")
    para('Methodology & limitations','Heading2')
    para('Crawl scope is bounded and may omit blocked, JavaScript-rendered, paginated or undiscovered pages. Recommendations are hypotheses until validated with business objectives and first-party search data. PageSpeed results are API-dependent and not included unless separately obtained.')
    doc.build(story)
    return buffer.getvalue()
