import ast, csv, json, re, sys, time, random
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Reuse the exact 110-school target list without importing/executing the progression scraper.
src = Path('scripts/minkou_scrape.py').read_text(encoding='utf-8')
mod = ast.parse(src)
SCHOOLS = None
for node in mod.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCHOOLS' for t in node.targets):
        SCHOOLS = ast.literal_eval(node.value)
        break
if not SCHOOLS:
    raise RuntimeError('SCHOOLS list not found')

OUT = Path('minkou_deviation_output')
RAW = OUT / 'raw_html'
OUT.mkdir(exist_ok=True); RAW.mkdir(exist_ok=True)

session = requests.Session()
retry = Retry(total=4, backoff_factor=1.0, status_forcelist=[429,500,502,503,504], allowed_methods=['GET'])
session.mount('https://', HTTPAdapter(max_retries=retry))
session.headers.update({
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
    'Accept-Language':'ja,en-US;q=0.8,en;q=0.6',
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
})

def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()

def parse_courses(raw):
    out=[]
    if not raw or raw in {'-','－','―','–'}:
        return out
    # Typical format: 普通科特別進学コース（70）/ 普通科進学コース（65）
    parts=[clean(x) for x in re.split(r'\s*/\s*',raw) if clean(x)]
    for part in parts:
        m=re.match(r'^(.*?)[（(]\s*([0-9]{2}(?:\.[0-9]+)?)\s*[）)]$',part)
        if m:
            out.append({'course_name':clean(m.group(1)),'deviation':float(m.group(2)) if '.' in m.group(2) else int(m.group(2)),'raw_component':part})
        else:
            out.append({'course_name':part,'deviation':None,'raw_component':part})
    return out

def find_label_value(lines, label):
    for i,line in enumerate(lines):
        if line == label or line.startswith(label):
            # exact same-line after colon
            m=re.match(r'^'+re.escape(label)+r'\s*[：:]\s*(.*)$',line)
            if m and clean(m.group(1)):
                return clean(m.group(1))
            for j in range(i+1,min(i+5,len(lines))):
                if lines[j]: return lines[j]
    return ''

def extract_rank(page_text, label):
    # Examples: 神奈川県内 7位 / 328件中
    pat=re.escape(label)+r'\s*([0-9,]+)位\s*/\s*([0-9,]+)件中'
    m=re.search(pat,page_text)
    if not m: return None,None
    return int(m.group(1).replace(',','')),int(m.group(2).replace(',',''))

summaries=[]; courses=[]; errors=[]
for idx,(rank,expected_name,sid) in enumerate(SCHOOLS,start=1):
    url=f'https://www.minkou.jp/hischool/school/deviation/{sid}/?c=1'
    try:
        r=session.get(url,timeout=30)
        if r.status_code != 200:
            errors.append({'rank':rank,'school':expected_name,'id':sid,'url':url,'error':f'HTTP {r.status_code}'})
            continue
        html=r.text
        (RAW/f'{rank:03d}_{sid}.html').write_text(html,encoding='utf-8')
        soup=BeautifulSoup(html,'lxml')
        page_text=soup.get_text('\n',strip=True)
        lines=[clean(x) for x in page_text.splitlines() if clean(x)]
        h1=soup.find('h1')
        page_h1=clean(h1.get_text(' ',strip=True)) if h1 else ''
        # Strip common suffixes to compare school name.
        page_name=re.sub(r'\s*偏差値.*$','',page_h1).strip() or expected_name

        bias_year=''
        # Prefer a heading explicitly saying 偏差値YYYY年度版
        for h in soup.find_all(['h2','h3']):
            ht=clean(h.get_text(' ',strip=True))
            m=re.search(r'偏差値\s*(20\d{2})年度版',ht)
            if m:
                bias_year=m.group(1); break
        if not bias_year:
            m=re.search(r'偏差値\s*(20\d{2})年度版',page_text)
            if m: bias_year=m.group(1)

        # Overall display: first top-level 偏差値： value. Avoid explanatory prose.
        bias_display=''
        for i,line in enumerate(lines[:120]):
            m=re.match(r'^偏差値[：:]\s*(.+)$',line)
            if m:
                v=clean(m.group(1))
                if re.match(r'^(?:-|[0-9]{2}(?:\s*-\s*[0-9]{2})?)$',v):
                    bias_display=v; break
            if line == '偏差値：':
                for j in range(i+1,min(i+4,len(lines))):
                    v=lines[j]
                    if re.match(r'^(?:-|[0-9]{2}(?:\s*-\s*[0-9]{2})?)$',v):
                        bias_display=v; break
                if bias_display: break
        if not bias_display:
            # Fallback near heading: stand-alone value immediately following "...偏差値YYYY年度版"
            for i,line in enumerate(lines):
                if re.search(r'偏差値\s*20\d{2}年度版',line):
                    for j in range(i+1,min(i+8,len(lines))):
                        if re.match(r'^(?:-|[0-9]{2}(?:\s*-\s*[0-9]{2})?)$',lines[j]):
                            bias_display=lines[j]; break
                    break

        course_raw=''
        # Locate the exact 学科： section. In current pages it is a label + next line.
        for i,line in enumerate(lines):
            if line == '学科：' or line.startswith('学科：'):
                same=clean(line.split('：',1)[1]) if '：' in line else ''
                if same:
                    course_raw=same
                else:
                    # next non-label line; allow '-' for no recruitment data
                    for j in range(i+1,min(i+6,len(lines))):
                        if lines[j] not in {'偏差値：','学科：'}:
                            course_raw=lines[j]; break
                break
        # HTML-text regex fallback
        if not course_raw:
            m=re.search(r'学科[：:]\s*([^\n]+)',page_text)
            if m: course_raw=clean(m.group(1))

        parsed=parse_courses(course_raw)
        for c in parsed:
            courses.append({
                'rank':rank,'school_name':expected_name,'school_id':sid,'url':url,
                'bias_year':int(bias_year) if bias_year else None,'bias_display':bias_display,
                'course_name':c['course_name'],'deviation':c['deviation'],'raw_component':c['raw_component']
            })

        pref_rank,pref_total=extract_rank(page_text,'神奈川県内')
        priv_rank,priv_total=extract_rank(page_text,'神奈川県内私立')
        nat_rank,nat_total=extract_rank(page_text,'全国')
        summaries.append({
            'rank':rank,'expected_name':expected_name,'page_name':page_name,'school_id':sid,'url':url,
            'http_status':r.status_code,'bias_year':int(bias_year) if bias_year else None,
            'bias_display':bias_display,'course_raw':course_raw,'course_count':len(parsed),
            'pref_rank':pref_rank,'pref_total':pref_total,'private_pref_rank':priv_rank,'private_pref_total':priv_total,
            'national_rank':nat_rank,'national_total':nat_total,'html_bytes':len(html.encode('utf-8')),
        })
        print(f'[{idx:03d}/110] {expected_name} id={sid} bias={bias_display!r} year={bias_year} courses={len(parsed)}',flush=True)
    except Exception as e:
        errors.append({'rank':rank,'school':expected_name,'id':sid,'url':url,'error':repr(e)})
        print(f'ERROR {expected_name}: {e!r}',file=sys.stderr,flush=True)
    time.sleep(0.35+random.random()*0.25)

(OUT/'deviation_summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'deviation_courses.json').write_text(json.dumps(courses,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2),encoding='utf-8')

def write_csv(path,rows,fields):
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
write_csv(OUT/'deviation_summary.csv',summaries,['rank','expected_name','page_name','school_id','url','http_status','bias_year','bias_display','course_raw','course_count','pref_rank','pref_total','private_pref_rank','private_pref_total','national_rank','national_total','html_bytes'])
write_csv(OUT/'deviation_courses.csv',courses,['rank','school_name','school_id','url','bias_year','bias_display','course_name','deviation','raw_component'])
manifest={'target_schools':len(SCHOOLS),'success_schools':len(summaries),'error_count':len(errors),'course_rows':len(courses),'generated_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('MANIFEST',json.dumps(manifest,ensure_ascii=False),flush=True)
if len(summaries)<100:
    sys.exit(2)
