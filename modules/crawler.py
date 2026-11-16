"""Bounded, robots-aware, public-HTTP crawler for an educational SEO SaaS MVP."""
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit, urldefrag
from urllib.robotparser import RobotFileParser
import ipaddress
import socket
import time
import re
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

USER_AGENT = "SEOIntelligenceMVP/0.1 (+public SEO audit; respects robots.txt)"
MAX_BYTES = 1_000_000
MAX_REDIRECTS = 4
TIMEOUT = (3, 8)

class CrawlError(Exception):
    pass

def normalize_url(value):
    value = value.strip()
    if not value:
        raise CrawlError("Enter a website URL.")
    if '://' not in value:
        value = 'https://' + value
    p = urlsplit(value)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise CrawlError("Only public http:// and https:// website URLs are supported.")
    try:
        port = p.port
    except ValueError as exc:
        raise CrawlError("Invalid port.") from exc
    if port not in (None, 80, 443):
        raise CrawlError("Custom ports are not supported.")
    host = p.hostname.lower().rstrip('.')
    if not host or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
        raise CrawlError("Local or internal hosts are not allowed.")
    netloc = host if ':' not in host else '[' + host + ']'
    if port and port != (443 if p.scheme == 'https' else 80):
        netloc += ':' + str(port)
    return urlunsplit((p.scheme, netloc, p.path or '/', p.query, ''))

def validate_public_url(url):
    url = normalize_url(url)
    host = urlsplit(url).hostname
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise CrawlError("Domain could not be resolved.") from exc
    if not infos:
        raise CrawlError("Domain could not be resolved.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise CrawlError("Private, reserved, or local network destinations are blocked.")
    return url

def safe_get(session, url):
    """Validate each redirect. DNS rebinding requires additional network-level egress controls."""
    for _ in range(MAX_REDIRECTS + 1):
        validate_public_url(url)
        try:
            with session.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    target = response.headers.get('Location')
                    if not target:
                        raise CrawlError("Redirect has no destination.")
                    url = normalize_url(urljoin(url, target))
                    continue
                chunks, total = [], 0
                for chunk in response.iter_content(chunk_size=16384):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise CrawlError("Response exceeded the 1 MB safety limit.")
                    chunks.append(chunk)
                response._content = b''.join(chunks)
                return response, url
        except requests.RequestException as exc:
            raise CrawlError("Request failed: " + str(exc)[:160]) from exc
    raise CrawlError("Too many redirects.")

def get_robots(session, base):
    robots_url = urljoin(base, '/robots.txt')
    try:
        r, final = safe_get(session, robots_url)
        if urlsplit(final).hostname != urlsplit(base).hostname:
            return None, 'Robots redirect to a different host; crawl stopped.'
        if r.status_code in (401, 403):
            return None, 'Robots access denied; crawl stopped.'
        if r.status_code == 404:
            parser = RobotFileParser()
            parser.parse([])
            return parser, 'robots.txt not found (404)'
        if r.status_code != 200:
            return None, f'robots.txt returned {r.status_code}; crawl stopped.'
        parser = RobotFileParser()
        parser.parse(r.text.splitlines())
        return parser, 'robots.txt loaded'
    except CrawlError as exc:
        return None, f'Could not verify robots.txt: {exc}'

def extract_page(url, html, status):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    desc = soup.find('meta', attrs={'name': lambda v: isinstance(v,str) and v.lower() == 'description'})
    description = desc.get('content', '').strip() if desc else ''
    canonical = soup.find('link', attrs={'rel': lambda v: v and 'canonical' in [str(x).lower() for x in (v if isinstance(v,list) else [v])]})
    robots = soup.find('meta', attrs={'name': lambda v: isinstance(v,str) and v.lower() == 'robots'})
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith(('#','mailto:','tel:','javascript:')):
            continue
        try:
            absolute = normalize_url(urljoin(url, href))
            links.append(absolute)
        except (CrawlError, ValueError):
            continue
    images = soup.find_all('img')
    image_count = len(images)
    missing_alt = sum(
        not isinstance(img.attrs, dict)
        or not isinstance(img.attrs.get('alt'), str)
        or not img.attrs['alt'].strip()
        for img in images
    )
    for element in soup(['script','style','noscript','svg']): element.decompose()
    body_text=' '.join(soup.stripped_strings)[:12000]
    schema_types=[]
    for script in BeautifulSoup(html,'html.parser').find_all('script',type='application/ld+json'):
        try:
            import json
            data=json.loads(script.string or script.get_text())
            for obj in (data if isinstance(data,list) else [data]):
                if isinstance(obj,dict): schema_types.append(str(obj.get('@type','Unknown')))
        except (ValueError,TypeError):schema_types.append('Invalid JSON-LD')
    return {
        'url': url, 'status': status, 'title': title, 'title_length': len(title),
        'description': description, 'description_length': len(description),
        'h1_count': len(soup.find_all('h1')),
        'h1': ' | '.join(h.get_text(' ', strip=True) for h in soup.find_all('h1'))[:300],
        'canonical': urljoin(url, canonical.get('href', '')) if canonical and canonical.get('href') else '',
        'noindex': 'noindex' in (robots.get('content','').lower() if robots else ''),
        'image_count': image_count,
        'missing_alt': missing_alt,
        'links': sorted(set(links)), 'text':body_text, 'schema_types':schema_types,
    }

def audit_pages(pages):
    issues = []
    def add(page, severity, issue, recommendation):
        issues.append({'severity':severity,'issue':issue,'url':page['url'],'recommendation':recommendation})
    title_counts = {}
    for p in pages:
        if p['title']:
            title_counts.setdefault(p['title'].casefold(), []).append(p['url'])
    for p in pages:
        if not p['title']:
            add(p,'High','Missing title','Add a unique descriptive HTML title.')
        elif len(p['title']) > 60:
            add(p,'Low','Long title','Review title length and search-result presentation.')
        if not p['description']:
            add(p,'Medium','Missing meta description','Write a useful, page-specific meta description.')
        if p['h1_count'] == 0:
            add(p,'Medium','Missing H1','Add one clear primary page heading.')
        elif p['h1_count'] > 1:
            add(p,'Low','Multiple H1 headings','Review heading hierarchy and semantics.')
        if p['noindex']:
            add(p,'Info','Noindex directive','Confirm that excluding this page from search is intentional.')
        if p['missing_alt']:
            add(p,'Low','Images without alt text',f'Review {p["missing_alt"]} images; add meaningful alt text where informative.')
        if not p['canonical']:
            add(p,'Low','No canonical tag','Consider an appropriate canonical URL where duplication is possible.')
        if p['title'] and len(title_counts[p['title'].casefold()]) > 1:
            add(p,'Medium','Duplicate title','Give distinct pages unique descriptive titles.')
    return issues

def crawl_website(input_url, max_pages=20, progress=None):
    max_pages = max(1, min(int(max_pages), 50))
    start = validate_public_url(input_url)
    host = urlsplit(start).hostname
    session = requests.Session()
    session.trust_env = False  # avoid proxy environment surprises
    session.headers.update({'User-Agent': USER_AGENT, 'Accept':'text/html,application/xhtml+xml'})
    robots, robots_status = get_robots(session, start)
    if robots is None:
        raise CrawlError(robots_status)
    sitemap_urls=[]
    sitemap_status='Not checked'
    try:
        sm, sm_final=safe_get(session,urljoin(start,'/sitemap.xml'))
        if sm.status_code==200 and urlsplit(sm_final).hostname==host and len(sm.content)<MAX_BYTES:
            root=ET.fromstring(sm.content)
            sitemap_urls=[x.text.strip() for x in root.iter() if x.tag.endswith('loc') and x.text and urlsplit(x.text.strip()).hostname==host][:max_pages*3]
            sitemap_status=f'Found {len(sitemap_urls)} same-host URLs (including possible sitemap-index references)'
        else:sitemap_status=f'HTTP {sm.status_code}'
    except (CrawlError,ET.ParseError,ValueError) as exc:sitemap_status=f'Unavailable: {str(exc)[:90]}'
    queue, seen, pages, errors = deque([start]+sitemap_urls), set(), [], []
    while queue and len(pages) < max_pages and len(seen) < max_pages * 5:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        if urlsplit(url).hostname != host:
            continue
        if not robots.can_fetch(USER_AGENT, url):
            errors.append({'url':url,'error':'Disallowed by robots.txt'})
            continue
        if progress:
            progress(len(pages), max_pages, url)
        try:
            response, final_url = safe_get(session, url)
            if urlsplit(final_url).hostname != host:
                errors.append({'url':url,'error':'Redirected outside target host'})
                continue
            if not robots.can_fetch(USER_AGENT, final_url):
                errors.append({'url':url,'error':'Redirect destination disallowed by robots.txt'})
                continue
            if 'text/html' not in response.headers.get('Content-Type','').lower():
                continue
            if response.status_code != 200:
                errors.append({'url':url,'error':f'HTTP {response.status_code}'})
                continue
            page = extract_page(final_url, response.text, response.status_code)
            pages.append(page)
            for link in page['links']:
                if urlsplit(link).hostname == host and link not in seen and link not in queue:
                    queue.append(link)
        except CrawlError as exc:
            errors.append({'url':url,'error':str(exc)})
        time.sleep(0.5)  # polite crawl pacing; increase for sensitive sites
    return {'pages':pages,'issues':audit_pages(pages),'errors':errors,
            'robots_status':robots_status,'crawled_count':len(pages),
            'discovered_count':len(seen),'limit':max_pages,'sitemap_status':sitemap_status}
