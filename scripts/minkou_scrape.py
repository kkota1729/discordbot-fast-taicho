import csv, json, os, re, sys, time, random
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SCHOOLS = [
(1,'聖光学院高等学校',5020),(2,'浅野高等学校',291),(3,'慶應義塾高等学校',1718),(4,'横浜翠嵐高等学校',1326),(5,'洗足学園高等学校',2483),(6,'湘南高等学校',1253),(7,'栄光学園高等学校',581),(8,'サレジオ学院高等学校',2101),(9,'逗子開成高等学校',2401),(10,'フェリス女学院高等学校',3924),
(11,'柏陽高等学校',1288),(12,'相模原中等教育学校 後期課程',1242),(13,'厚木高等学校',1196),(14,'川和高等学校',1236),(15,'横浜市立横浜サイエンスフロンティア高等学校',4919),(16,'横浜緑ケ丘高等学校',1332),(17,'横浜市立南高等学校',4918),(18,'神奈川大学附属高等学校',1334),(19,'鎌倉学園高等学校',1342),(20,'平塚中等教育学校 後期課程',88873),
(21,'山手学院高等学校',4858),(22,'桐光学園高等学校',2993),(23,'法政大学第二高等学校',4205),(24,'相模原高等学校',1245),(25,'小田原高等学校',1217),(26,'公文国際学園高等部',1634),(27,'中央大学附属横浜高等学校',2706),(28,'光陵高等学校',1241),(29,'横浜共立学園高等学校',4909),(30,'神奈川総合高等学校',1224),
(31,'大和高等学校',1313),(32,'桐蔭学園高等学校',2755),(33,'横浜雙葉高等学校',4927),(34,'桐蔭学園中等教育学校 後期課程',88875),(35,'鎌倉高等学校',1227),(36,'横浜平沼高等学校',1330),(37,'平塚江南高等学校',1295),(38,'法政大学国際高等学校',4204),(39,'横浜市立金沢高等学校',4913),(40,'日本大学藤沢高等学校',3581),
(41,'新城高等学校',1259),(42,'横須賀学院高等学校',4904),(43,'鎌倉女学院高等学校',1343),(44,'茅ケ崎北陵高等学校',1277),(45,'湘南白百合学園高等学校',2361),(46,'カリタス女子高等学校',1348),(47,'横浜隼人高等学校',4925),(48,'横浜国際高等学校',1323),(49,'海老名高等学校',1213),(50,'松陽高等学校',1255),
(51,'関東学院高等学校',1372),(52,'横浜市立桜丘高等学校',4914),(53,'青山学院横浜英和高等学校',4907),(54,'日本女子大学附属高等学校',3590),(55,'麻溝台高等学校',1192),(56,'大船高等学校',1270),(57,'麻布大学附属高等学校',300),(58,'秦野高等学校',1290),(59,'川崎市立橘高等学校',1359),(60,'湘南学園高等学校',2358),
(61,'清泉女学院高等学校',2435),(62,'横浜創英高等学校',4923),(63,'鶴見大学附属高等学校',2731),(64,'港北高等学校',1240),(65,'向上高等学校',1752),(66,'神奈川学園高等学校',1188),(67,'森村学園高等部',4730),(68,'鶴見高等学校',1281),(69,'鵠沼高等学校',1570),(70,'大磯高等学校',1215),
(71,'湘南工科大学附属高等学校',2359),(72,'大和西高等学校',1271),(73,'横浜女学院高等学校',4912),(74,'自修館中等教育学校 後期課程',88874),(75,'西湘高等学校',1264),(76,'元石川高等学校',1310),(77,'立花学園高等学校',2542),(78,'聖セシリア女子高等学校',2434),(79,'横浜翠陵高等学校',4910),(80,'橘学苑高等学校',2541),
(81,'住吉高等学校',1262),(82,'アレセイア湘南高等学校',320),(83,'横浜市立横浜商業高等学校',4920),(84,'相模女子大学高等部',2075),(85,'藤嶺学園藤沢高等学校',3021),(86,'横浜高等学校',4906),(87,'横浜富士見丘学園高等学校',88876),(88,'岸根高等学校',1237),(89,'三浦学苑高等学校',4490),(90,'横浜清風高等学校',4922),
(91,'鶴嶺高等学校',1283),(92,'茅ヶ崎高等学校',1275),(93,'横浜市立みなと総合高等学校',4917),(94,'上溝南高等学校',1231),(95,'武相高等学校',4183),(96,'橋本高等学校',1289),(97,'川崎市立高津高等学校',1358),(98,'聖園女学院高等学校',4552),(99,'横浜氷取沢高等学校',1293),(100,'聖和学院高等学校',2468),
(101,'金井高等学校',1222),(102,'横浜創学館高等学校',4924),(103,'百合丘高等学校',1316),(104,'鎌倉女子大学高等部',1344),(105,'有馬高等学校',1204),(106,'藤沢清流高等学校',1302),(107,'函嶺白百合学園高等学校',1377),(108,'光明学園相模原高等学校',1829),(109,'横浜清陵高等学校',1327),(110,'神奈川歯科大学系属緑ヶ丘女子高等学校',4559),
]

OUT = Path('minkou_output')
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

def parse_num(raw):
    raw = clean(raw)
    m = re.search(r'([0-9][0-9,]*)\s*人', raw)
    if m: return int(m.group(1).replace(',',''))
    return None

def status_of(raw):
    t=clean(raw)
    if not t: return 'blank'
    if t in {'-','－','―','–'}: return 'hyphen'
    if parse_num(t) is not None: return 'number'
    return 'text'

def section_text_between(heading):
    parts=[]
    for el in heading.find_all_next():
        if el is heading: continue
        if el.name == heading.name:
            break
        if el.name in {'h1','h2'} and heading.name in {'h2','h3'}:
            break
        if el.name in {'li','p','div','span','td','th'}:
            t=clean(el.get_text(' ', strip=True))
            if t and (not parts or t != parts[-1]): parts.append(t)
    return '\n'.join(parts)

def preceding_heading(table):
    h = table.find_previous(['h2','h3','h4'])
    return clean(h.get_text(' ',strip=True)) if h else ''

summary_rows=[]; university_rows=[]; other_table_rows=[]; section_rows=[]; errors=[]

for idx,(rank,expected_name,sid) in enumerate(SCHOOLS, start=1):
    url=f'https://www.minkou.jp/hischool/school/university/{sid}/'
    try:
        r=session.get(url, timeout=30)
        if r.status_code != 200:
            errors.append({'rank':rank,'school':expected_name,'id':sid,'url':url,'error':f'HTTP {r.status_code}'})
            continue
        html=r.text
        (RAW/f'{rank:03d}_{sid}.html').write_text(html,encoding='utf-8')
        soup=BeautifulSoup(html,'lxml')
        page_text=soup.get_text('\n',strip=True)
        h1=soup.find('h1')
        page_h1=clean(h1.get_text(' ',strip=True)) if h1 else ''
        page_name=re.sub(r'\s*進学実績\s*$','',page_h1).strip() or expected_name

        # Header deviation score, preferring first visible '偏差値：' occurrence.
        bias_display=''
        m=re.search(r'偏差値[：:]\s*([^\n]+)', page_text)
        if m: bias_display=clean(m.group(1))
        # Basic information's department/course string.
        course_raw=''
        for tr in soup.find_all('tr'):
            cells=tr.find_all(['th','td'])
            if len(cells)>=2 and clean(cells[0].get_text(' ',strip=True))=='学科':
                course_raw=clean(cells[1].get_text(' ',strip=True)); break

        # Difficult university aggregate heading and raw text.
        diff_heading=None
        for h in soup.find_all(['h2','h3']):
            if '難関大学合格者数' in clean(h.get_text(' ',strip=True)):
                diff_heading=h; break
        summary_year=''; summary_raw=''; summary_map={}
        if diff_heading:
            ht=clean(diff_heading.get_text(' ',strip=True))
            ym=re.search(r'(20\d{2})年度',ht)
            if ym: summary_year=ym.group(1)
            # Collect concise text until next h2, then parse category/count pairs.
            nodes=[]
            for sib in diff_heading.find_all_next():
                if sib is diff_heading: continue
                if sib.name=='h2': break
                if sib.name in {'li','p'}:
                    t=clean(sib.get_text(' ',strip=True))
                    if t and t not in nodes: nodes.append(t)
            summary_raw='\n'.join(nodes)
            for t in nodes:
                # common case: one li contains category and count
                mm=re.match(r'(.+?)\s*([0-9][0-9,]*)\s*人$',t)
                if mm:
                    summary_map[clean(mm.group(1))]=int(mm.group(2).replace(',',''))
            # Fallback: whole segment regex by known labels.
            segment='\n'.join(clean(x) for x in diff_heading.parent.stripped_strings) if diff_heading.parent else ''
            known=['東大','京大','旧帝大+一橋+科学大※','国立大(旧帝大+一橋+科学大を除く)','医学部合格者数','早慶上理ICU','GMARCH','関関同立']
            for lab in known:
                if lab not in summary_map:
                    pat=re.escape(lab)+r'\s*([0-9][0-9,]*)\s*人'
                    mm=re.search(pat, segment)
                    if mm: summary_map[lab]=int(mm.group(1).replace(',',''))

        # Locate main university-results table.
        main_table=None
        for table in soup.find_all('table'):
            tt=clean(table.get_text(' ',strip=True))
            if '大学名' in tt and '国公私立' in tt and '合格者数' in tt:
                main_table=table; break
        years=[]; main_row_count=0
        if main_table:
            head_text=clean(main_table.find('thead').get_text(' ',strip=True) if main_table.find('thead') else main_table.get_text(' ',strip=True))
            years=re.findall(r'(20\d{2})年', head_text)
            # keep first three unique in order
            years=list(dict.fromkeys(years))[:3]
            for tr in main_table.find_all('tr'):
                cells=tr.find_all(['th','td'])
                vals=[clean(c.get_text(' ',strip=True)) for c in cells]
                if not vals or vals[0] in {'大学名','---'}: continue
                # Identify data rows by presence of public/private label and enough cells.
                type_idx=next((i for i,v in enumerate(vals) if v in {'国立','公立','私立'}),None)
                if type_idx is None or type_idx<2: continue
                uni=vals[0]; uni_bias=vals[1]; sector=vals[type_idx]
                counts=vals[type_idx+1:type_idx+1+len(years)]
                counts += ['']*(len(years)-len(counts))
                main_row_count += 1
                if not years:
                    university_rows.append({'rank':rank,'school_name':expected_name,'school_id':sid,'page_name':page_name,'url':url,'university_name':uni,'university_bias':uni_bias,'sector':sector,'year':'','count_raw':'','count_num':None,'value_status':'unknown'})
                else:
                    for y,raw in zip(years,counts):
                        university_rows.append({'rank':rank,'school_name':expected_name,'school_id':sid,'page_name':page_name,'url':url,'university_name':uni,'university_bias':uni_bias,'sector':sector,'year':int(y),'count_raw':raw,'count_num':parse_num(raw),'value_status':status_of(raw)})
        else:
            errors.append({'rank':rank,'school':expected_name,'id':sid,'url':url,'error':'main university table not found'})

        # Preserve every other HTML table in structured raw form, including specialized schools/overseas if present.
        for ti,table in enumerate(soup.find_all('table')):
            if table is main_table: continue
            heading=preceding_heading(table)
            # Skip layout/basic info tables unless clearly progression-related; raw HTML still preserves everything.
            keytxt=(heading+' '+clean(table.get_text(' ',strip=True))).lower()
            if not any(k in keytxt for k in ['専門','海外','進学','合格','大学','短大','就職']):
                continue
            for ri,tr in enumerate(table.find_all('tr')):
                vals=[clean(c.get_text(' ',strip=True)) for c in tr.find_all(['th','td'])]
                if vals:
                    other_table_rows.append({'rank':rank,'school_name':expected_name,'school_id':sid,'url':url,'section_heading':heading,'table_index':ti,'row_index':ri,'cells':vals})

        # Preserve relevant text sections too.
        for h in soup.find_all(['h2','h3']):
            ht=clean(h.get_text(' ',strip=True))
            if any(k in ht for k in ['専門学校','海外大学','就職','進路実績','進学実績']) and '大学合格実績' not in ht and '難関大学合格者数' not in ht:
                section_rows.append({'rank':rank,'school_name':expected_name,'school_id':sid,'url':url,'heading':ht,'text':section_text_between(h)})

        summary_rows.append({
            'rank':rank,'expected_name':expected_name,'page_name':page_name,'school_id':sid,'url':url,
            'http_status':r.status_code,'bias_display':bias_display,'course_raw':course_raw,
            'summary_year':summary_year,'summary':summary_map,'summary_raw':summary_raw,
            'table_years':years,'university_row_count':main_row_count,
            'html_bytes':len(html.encode('utf-8')),
        })
        print(f'[{idx:03d}/110] {expected_name} id={sid} rows={main_row_count} years={years} summary={summary_year}', flush=True)
    except Exception as e:
        errors.append({'rank':rank,'school':expected_name,'id':sid,'url':url,'error':repr(e)})
        print(f'ERROR {expected_name}: {e!r}', file=sys.stderr, flush=True)
    time.sleep(0.45 + random.random()*0.35)

# Write JSON and CSV outputs.
(OUT/'school_summary.json').write_text(json.dumps(summary_rows,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'university_results_long.json').write_text(json.dumps(university_rows,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'other_table_rows.json').write_text(json.dumps(other_table_rows,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'other_sections.json').write_text(json.dumps(section_rows,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2),encoding='utf-8')

# CSVs for easy downstream processing.
def write_csv(path, rows, fields):
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
write_csv(OUT/'school_summary.csv', summary_rows, ['rank','expected_name','page_name','school_id','url','http_status','bias_display','course_raw','summary_year','university_row_count','html_bytes'])
write_csv(OUT/'university_results_long.csv', university_rows, ['rank','school_name','school_id','page_name','url','university_name','university_bias','sector','year','count_raw','count_num','value_status'])

manifest={
 'target_schools':len(SCHOOLS),'success_schools':len(summary_rows),'error_count':len(errors),
 'university_long_rows':len(university_rows),'other_table_rows':len(other_table_rows),'other_sections':len(section_rows),
 'generated_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('MANIFEST',json.dumps(manifest,ensure_ascii=False),flush=True)
if len(summary_rows)<100:
    print('Too many failures',file=sys.stderr); sys.exit(2)
