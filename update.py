"""GitHub Actions: daily update earring sales dashboard."""
import json, os, requests
from datetime import datetime, timedelta
from collections import defaultdict

APP_ID = os.environ["FEISHU_APP_ID"]
APP_SECRET = os.environ["FEISHU_APP_SECRET"]
ST = "XZsPs8MwohIMLqtbhKxcqfkHnUh"
DAYS = 7
SKIP_KW = ['合计','总计','销售','月份','平均','汇总','小计','总数','sum','total']

def cl(n):
    r = ''
    while n > 0: n -= 1; r = chr(65 + n % 26) + r; n //= 26
    return r

def api_get(url, token):
    return requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30).json()

def get_token():
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=30)
    return r.json()["tenant_access_token"]

token = get_token()
print(f"[{datetime.now()}] Token obtained")

sheets = [("4bd447", 234, 1267), ("HVRDRB", 209, 913)]
sheet_names = {"4bd447": "耳环", "HVRDRB": "耳环-新店"}
all_results = {}
dates = []

for sid, nrows, ncols in sheets:
    # Scan backwards for last date WITH data
    end_col = None
    chunk = 50
    for base in range(ncols, 100, -chunk):
        c_start = max(base - chunk + 1, 101)
        c_end = base
        try:
            v = api_get(
                f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST}/values/{sid}!{cl(c_start)}1:{cl(c_end)}12",
                token)
            rows = v['data']['valueRange']['values']
            if len(rows) < 2: continue
            r1 = rows[0]
            for j in range(len(r1) - 1, -1, -1):
                val = r1[j]
                if isinstance(val, (int, float)) and val > 40000:
                    has_data = False
                    for dr in rows[2:]:
                        if j < len(dr) and dr[j] is not None and isinstance(dr[j], (int,float)) and dr[j] > 0:
                            has_data = True; break
                    if has_data:
                        end_col = c_start + j; break
            if end_col: break
        except: continue

    if end_col is None:
        print(f"Sheet {sid}: no data found"); continue

    start_col = end_col - DAYS + 1
    print(f"Sheet {sid}: cols {start_col}-{end_col}")

    # Dates
    v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST}/values/{sid}!{cl(start_col)}1:{cl(end_col)}1", token)
    r1 = v['data']['valueRange']['values'][0]
    if not dates:
        for val in r1:
            if isinstance(val, (int,float)) and val > 40000:
                dates.append((datetime(1899,12,30)+timedelta(days=int(val))).strftime('%m/%d'))

    # Names
    names = []
    for s in range(1, nrows+1, 50):
        v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST}/values/{sid}!A{s}:A{min(s+49,nrows)}", token)
        for row in v['data']['valueRange']['values']:
            names.append(str(row[0]).strip() if row and row[0] else '')

    # Data
    store_data = defaultdict(lambda: {'daily': {d: 0 for d in dates}, 'total': 0})
    for s in range(1, nrows+1, 50):
        end_row = min(s+49, nrows)
        try:
            v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST}/values/{sid}!{cl(start_col)}{s}:{cl(end_col)}{end_row}", token)
            rows = v['data']['valueRange']['values']
            for ri, row in enumerate(rows):
                ni = s + ri - 1
                name = names[ni] if ni < len(names) else ''
                if not name or name == 'None': continue
                if any(kw in name.lower() for kw in [k.lower() for k in SKIP_KW]): continue
                vals = [int(x) if isinstance(x,(int,float)) else 0 for x in row[:DAYS]]
                total = sum(vals)
                if total > 100000: continue
                if total > 0:
                    for i, d in enumerate(dates): store_data[name]['daily'][d] = vals[i]
                    store_data[name]['total'] = total
        except: pass

    clean = {n: d for n, d in store_data.items() if d['total'] > 0 and len(n) < 30}
    all_results[sid] = dict(sorted(clean.items(), key=lambda x: x[1]['total'], reverse=True))
    print(f"  {len(clean)} stores")

# Build HTML
final = {sheet_names.get(k, k): v for k, v in all_results.items()}
data = {'dates': dates, 'sheets': final}

dates_json = json.dumps(data['dates'], ensure_ascii=False)
sheets_json = json.dumps(data['sheets'], ensure_ascii=False)
sn = list(data['sheets'].keys())
s1, s2 = sn[0], sn[1] if len(sn) > 1 else ''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{s1}销售仪表盘</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Microsoft YaHei', sans-serif; background:#f0f2f5; color:#333; padding:16px; }}
.header {{ text-align:center; margin-bottom:16px; }}
.header h1 {{ font-size:20px; color:#1a1a2e; }}
.header p {{ color:#666; margin-top:2px; font-size:12px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px; }}
.card {{ background:#fff; border-radius:10px; padding:14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); }}
.card h2 {{ font-size:14px; margin-bottom:8px; color:#1a1a2e; border-bottom:2px solid #4472C4; padding-bottom:5px; }}
.chart-wrap {{ position:relative; height:280px; }}
.table-wrap {{ max-height:420px; overflow-y:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:11px; }}
th {{ background:#4472C4; color:#fff; padding:5px 3px; position:sticky; top:0; z-index:1; text-align:center; }}
td {{ padding:3px; text-align:center; border-bottom:1px solid #eee; }}
tr:hover td {{ background:#f5f7fa; }}
td:first-child {{ text-align:left; font-weight:500; }}
.num {{ text-align:right; }}
.total-row td {{ font-weight:bold; background:#FFF2CC; border-top:2px solid #4472C4; }}
.full-width {{ grid-column:1/-1; }}
.summary-bar {{ display:flex; gap:14px; margin-bottom:14px; }}
.summary-item {{ flex:1; background:#fff; border-radius:10px; padding:12px 14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); text-align:center; }}
.summary-item .value {{ font-size:22px; font-weight:bold; color:#4472C4; }}
.summary-item .label {{ font-size:10px; color:#888; margin-top:1px; }}
.updated {{ text-align:right; color:#aaa; font-size:10px; margin-top:8px; }}
@media (max-width:768px) {{ .grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="header"><h1>{s1}销售仪表盘</h1><p id="dateRange"></p></div>
<div class="summary-bar" id="summaryBar"></div>
<div class="grid">
  <div class="card"><h2>{s1} - 销售占比</h2><div class="chart-wrap"><canvas id="pie1"></canvas></div></div>
  <div class="card"><h2>{s2} - 销售占比</h2><div class="chart-wrap"><canvas id="pie2"></canvas></div></div>
  <div class="card"><h2>{s1} - Top 10</h2><div class="chart-wrap"><canvas id="bar1"></canvas></div></div>
  <div class="card"><h2>{s2} - Top 10</h2><div class="chart-wrap"><canvas id="bar2"></canvas></div></div>
</div>
<div class="grid">
  <div class="card full-width"><h2>{s1} - 全部明细</h2><div class="table-wrap" id="t1"></div></div>
  <div class="card full-width"><h2>{s2} - 全部明细</h2><div class="table-wrap" id="t2"></div></div>
</div>
<div class="updated">更新于: <span id="updTime"></span></div>
<script>
var DATA = {dates_json};
var SHEETS = {sheets_json};
var S1 = '{s1}';
var S2 = '{s2}';
var UPD = '{datetime.now().strftime("%Y-%m-%d %H:%M")}';
document.getElementById('dateRange').textContent = DATA[0] + ' — ' + DATA[DATA.length-1] + '（'+DATA.length+'天）';
document.getElementById('updTime').textContent = UPD;
var colors = ['#4472C4','#ED7D31','#70AD47','#FFC000','#5B9BD5','#A5A5A5','#FF6B6B','#4ECDC4','#45B7D1','#96CEB4','#FFEAA7','#DDA0DD','#98D8C8'];
(function(){{
  var dates = DATA;
  var s1 = SHEETS[S1] || {{}};
  var s2 = SHEETS[S2] || {{}};
  function st(s) {{ var e=Object.entries(s); return {{cnt:e.length, total:e.reduce(function(a,x){{return a+x[1].total}},0)}}; }}
  var r1=st(s1), r2=st(s2);
  document.getElementById('summaryBar').innerHTML =
    '<div class="summary-item"><div class="value">'+r1.total.toLocaleString()+'</div><div class="label">'+S1+' ('+r1.cnt+'店铺)</div></div>'+
    '<div class="summary-item"><div class="value">'+r2.total.toLocaleString()+'</div><div class="label">'+S2+' ('+r2.cnt+'店铺)</div></div>'+
    '<div class="summary-item"><div class="value">'+(r1.total+r2.total).toLocaleString()+'</div><div class="label">合计</div></div>';
  function mkTbl(divId, sd) {{
    var e = Object.entries(sd).sort(function(a,b){{return b[1].total-a[1].total}});
    var total = e.reduce(function(s,x){{return s+x[1].total}},0);
    var h='<table><thead><tr><th>店铺</th>';
    dates.forEach(function(d){{h+='<th>'+d+'</th>';}});
    h+='<th>合计</th></tr></thead><tbody>';
    e.forEach(function(x){{
      var name=x[0], d=x[1];
      h+='<tr><td>'+name+'</td>';
      dates.forEach(function(dd){{h+='<td class="num">'+(d.daily[dd]||0)+'</td>';}});
      h+='<td class="num" style="font-weight:bold">'+d.total+'</td></tr>';
    }});
    h+='<tr class="total-row"><td>合计</td>';
    dates.forEach(function(dd){{var dt=e.reduce(function(s,x){{return s+(x[1].daily[dd]||0)}},0);h+='<td class="num">'+dt+'</td>';}});
    h+='<td class="num">'+total+'</td></tr></tbody></table>';
    document.getElementById(divId).innerHTML=h;
  }}
  function mkPie(id, sd) {{
    var e = Object.entries(sd).sort(function(a,b){{return b[1].total-a[1].total}});
    var labels, dt;
    if(e.length<=8){{labels=e.map(function(x){{return x[0]}});dt=e.map(function(x){{return x[1].total}});}}
    else{{labels=e.slice(0,8).map(function(x){{return x[0]}}).concat(['其他']);
         dt=e.slice(0,8).map(function(x){{return x[1].total}}).concat([e.slice(8).reduce(function(s,x){{return s+x[1].total}},0)]);}}
    new Chart(document.getElementById(id),{{type:'doughnut',
      data:{{labels:labels,datasets:[{{data:dt,backgroundColor:colors.slice(0,labels.length)}}]}},
      options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right',labels:{{font:{{size:10}},padding:6}}}}}}}}}});
  }}
  function mkBar(id, sd) {{
    var top = Object.entries(sd).sort(function(a,b){{return b[1].total-a[1].total}}).slice(0,10);
    new Chart(document.getElementById(id),{{type:'bar',
      data:{{labels:top.map(function(x){{return x[0].length>14?x[0].slice(0,13)+'…':x[0]}}),
            datasets:[{{data:top.map(function(x){{return x[1].total}}),backgroundColor:colors[0],borderRadius:3}}]}},
      options:{{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:true}}}}}}}}}});
  }}
  if(Object.keys(s1).length){{mkTbl('t1',s1);if(typeof Chart!=='undefined'){{mkPie('pie1',s1);mkBar('bar1',s1);}}}}
  if(Object.keys(s2).length){{mkTbl('t2',s2);if(typeof Chart!=='undefined'){{mkPie('pie2',s2);mkBar('bar2',s2);}}}}
}})();
</script>
</body>
</html>'''

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"[{datetime.now()}] HTML updated")
