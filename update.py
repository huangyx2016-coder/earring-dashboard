"""GitHub Actions: daily update - Earring + Daily Orders dashboard."""
import json, os, requests
from datetime import datetime, timedelta
from collections import defaultdict

APP_ID = os.environ["FEISHU_APP_ID"]
APP_SECRET = os.environ["FEISHU_APP_SECRET"]
DAYS = 7
SKIP_KW = ['合计','总计','销售','月份','平均','汇总','小计','总数','sum','total']

def cl(n):
    r = ''
    while n > 0: n -= 1; r = chr(65 + n % 26) + r; n //= 26
    return r

def api_get(url, token):
    return requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30).json()

token = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=30).json()["tenant_access_token"]
print(f"[{datetime.now()}] Token obtained")

# ============================================================
# DATA SOURCE 1: Earring Sales
# ============================================================
ST1 = "XZsPs8MwohIMLqtbhKxcqfkHnUh"
earring_data = {}
dates_earring = []

for sid, nrows, ncols, label in [("4bd447", 234, 1267, "耳环"), ("HVRDRB", 209, 913, "耳环-新店")]:
    end_col = None
    for base in range(ncols, 100, -50):
        cs = max(base - 49, 101); ce = base
        try:
            v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST1}/values/{sid}!{cl(cs)}1:{cl(ce)}12", token)
            rows = v['data']['valueRange']['values']
            if len(rows) < 2: continue
            r1 = rows[0]
            for j in range(len(r1)-1, -1, -1):
                val = r1[j]
                if isinstance(val, (int,float)) and val > 40000:
                    if any(j < len(dr) and isinstance(dr[j],(int,float)) and dr[j] > 0 for dr in rows[2:]):
                        end_col = cs + j; break
            if end_col: break
        except: continue

    if end_col is None: print(f"  {label}: no data"); continue
    sc = end_col - DAYS + 1
    print(f"  {label}: cols {sc}-{end_col}")

    v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST1}/values/{sid}!{cl(sc)}1:{cl(end_col)}1", token)
    r1 = v['data']['valueRange']['values'][0]
    if not dates_earring:
        for val in r1:
            if isinstance(val, (int,float)) and val > 40000:
                dates_earring.append((datetime(1899,12,30)+timedelta(days=int(val))).strftime('%m/%d'))

    names = []
    for s in range(1, nrows+1, 50):
        v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST1}/values/{sid}!A{s}:A{min(s+49,nrows)}", token)
        for row in v['data']['valueRange']['values']:
            names.append(str(row[0]).strip() if row and row[0] else '')

    sd = defaultdict(lambda: {'daily': {d: 0 for d in dates_earring}, 'total': 0})
    for s in range(1, nrows+1, 50):
        er = min(s+49, nrows)
        try:
            v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST1}/values/{sid}!{cl(sc)}{s}:{cl(end_col)}{er}", token)
            rows = v['data']['valueRange']['values']
            for ri, row in enumerate(rows):
                ni = s + ri - 1
                name = names[ni] if ni < len(names) else ''
                if not name or name == 'None': continue
                if any(kw in name.lower() for kw in [k.lower() for k in SKIP_KW]): continue
                vals = [int(x) if isinstance(x,(int,float)) else 0 for x in row[:DAYS]]
                total = sum(vals)
                if total > 100000 or total <= 0 or len(name) >= 30: continue
                for i, d in enumerate(dates_earring): sd[name]['daily'][d] = vals[i]
                sd[name]['total'] = total
        except: pass

    earring_data[label] = dict(sorted(sd.items(), key=lambda x: x[1]['total'], reverse=True))
    print(f"    {len(earring_data[label])} stores, total={sum(d['total'] for d in earring_data[label].values())}")

# ============================================================
# DATA SOURCE 2: Daily Orders
# ============================================================
ST2 = "DhN8s0apZhaDJltlW60cuZtKnMg"
SID2 = "0f1400"
end_col2 = None
for base in range(3305, 2000, -30):
    cs = max(base - 29, 2001)
    try:
        v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST2}/values/{SID2}!{cl(cs)}1:{cl(base)}12", token)
        rows = v['data']['valueRange']['values']
        if len(rows) < 2: continue
        r1 = rows[0]
        for j in range(len(r1)-1, -1, -1):
            if isinstance(r1[j], (int,float)) and r1[j] > 40000:
                if any(j < len(dr) and isinstance(dr[j],(int,float)) and dr[j] > 0 for dr in rows[2:]):
                    end_col2 = cs + j; break
        if end_col2: break
    except: continue

if end_col2 is None: end_col2 = 1206
# Align start to group boundary: each group = US,EU,CA,SUM (serial at US=col 0)
# Groups are 4 cols apart. Serial at end_col is US. Go back (DAYS-1)*4 for start.
sc2 = end_col2 - (DAYS - 1) * 4
print(f"  Orders: cols {sc2}-{end_col2+3}")

v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST2}/values/{SID2}!{cl(sc2)}1:{cl(end_col2+3)}1", token)
r1 = v['data']['valueRange']['values'][0]
dates_orders = []
for val in r1:
    if isinstance(val, (int,float)) and val > 40000 and len(dates_orders) < DAYS:
        dates_orders.append((datetime(1899,12,30)+timedelta(days=int(val))).strftime('%m/%d'))

onames = []
for s in range(1, 197, 50):
    v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST2}/values/{SID2}!A{s}:A{min(s+49,196)}", token)
    for row in v['data']['valueRange']['values']:
        onames.append(str(row[0]).strip() if row and row[0] else '')

od = defaultdict(lambda: {'daily_us': {d:0 for d in dates_orders}, 'daily_eu': {d:0 for d in dates_orders},
                           'daily_ca': {d:0 for d in dates_orders}, 'total': 0})
for s in range(1, 197, 50):
    er = min(s+49, 196)
    try:
        v = api_get(f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ST2}/values/{SID2}!{cl(sc2)}{s}:{cl(end_col2+3)}{er}", token)
        rows = v['data']['valueRange']['values']
        for ri, row in enumerate(rows):
            ni = s + ri - 1
            name = onames[ni] if ni < len(onames) else ''
            if not name or name == 'None': continue
            if any(kw in name.lower() for kw in [k.lower() for k in SKIP_KW]): continue
            if '出单' in name or len(name) >= 30: continue
            total = 0
            for di in range(min(DAYS, len(dates_orders))):
                b = di * 4
                # Column order within each 4-col group: US, EU, CA, SUM
                us = int(row[b]) if b < len(row) and isinstance(row[b],(int,float)) else 0
                eu = int(row[b+1]) if b+1 < len(row) and isinstance(row[b+1],(int,float)) else 0
                ca = int(row[b+2]) if b+2 < len(row) and isinstance(row[b+2],(int,float)) else 0
                d = dates_orders[di]
                od[name]['daily_us'][d] = us; od[name]['daily_eu'][d] = eu; od[name]['daily_ca'][d] = ca
                total += us + eu + ca
            if total > 0: od[name]['total'] = total
    except: pass

orders_data = dict(sorted(od.items(), key=lambda x: x[1]['total'], reverse=True))
print(f"    {len(orders_data)} stores, total={sum(d['total'] for d in orders_data.values())}")

# ============================================================
# DATA SOURCE 3: Lingxing ERP (from local lingxing_data.json)
# ============================================================
lingxing_data = None
try:
    with open("lingxing_data.json", "r", encoding="utf-8") as f:
        lingxing_data = json.load(f)
    print(f"  Lingxing: {lingxing_data.get('total_orders',0)} orders, {lingxing_data.get('shops_count',0)} stores, FBA {lingxing_data['stock_summary']['available']} available")
except Exception as e:
    print(f"  Lingxing: skipped ({e})")

# ============================================================
# BUILD HTML
# ============================================================
ed_json = json.dumps(earring_data, ensure_ascii=False)
od_json = json.dumps(orders_data, ensure_ascii=False)
de_json = json.dumps(dates_earring, ensure_ascii=False)
do_json = json.dumps(dates_orders, ensure_ascii=False)
lx_json = json.dumps(lingxing_data, ensure_ascii=False) if lingxing_data else "null"
enames = list(earring_data.keys())
s1 = enames[0] if enames else "耳环"
s2 = enames[1] if len(enames) > 1 else ""

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>销售仪表盘</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Microsoft YaHei', sans-serif; background:#f0f2f5; color:#333; padding:16px; }}
.header {{ text-align:center; margin-bottom:16px; }}
.header h1 {{ font-size:22px; color:#1a1a2e; }}
.header p {{ color:#666; margin-top:2px; font-size:12px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px; }}
.card {{ background:#fff; border-radius:10px; padding:14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); }}
.card h2 {{ font-size:14px; margin-bottom:8px; border-bottom:2px solid #4472C4; padding-bottom:5px; }}
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
.summary-bar {{ display:flex; gap:14px; margin-bottom:14px; flex-wrap:wrap; }}
.summary-item {{ flex:1; min-width:140px; background:#fff; border-radius:10px; padding:12px 14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); text-align:center; }}
.summary-item .value {{ font-size:22px; font-weight:bold; color:#4472C4; }}
.summary-item .label {{ font-size:10px; color:#888; margin-top:1px; }}
.updated {{ text-align:right; color:#aaa; font-size:10px; margin-top:8px; }}
.tabs {{ display:flex; gap:0; margin-bottom:0; }}
.tab {{ padding:10px 20px; background:#e8e8e8; border-radius:8px 8px 0 0; cursor:pointer; font-size:14px; font-weight:500; color:#666; }}
.tab.active {{ background:#4472C4; color:#fff; }}
.tab-content {{ display:none; }}
.tab-content.active {{ display:block; }}
@media (max-width:768px) {{ .grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="header"><h1>销售仪表盘</h1><p id="dateRange"></p></div>
<div class="tabs">
  <div class="tab active" onclick="switchTab('earring')">{s1}销售</div>
  <div class="tab" onclick="switchTab('orders')">每日下单统计</div>
  <div class="tab" onclick="switchTab('lingxing')">领星ERP</div>
</div>

<!-- TAB 1: Earring -->
<div class="tab-content active" id="tab-earring">
  <div class="summary-bar" id="smE"></div>
  <div class="grid">
    <div class="card"><h2>{s1} - 销售占比</h2><div class="chart-wrap"><canvas id="pie1"></canvas></div></div>
    <div class="card"><h2>{s2} - 销售占比</h2><div class="chart-wrap"><canvas id="pie2"></canvas></div></div>
    <div class="card"><h2>{s1} - Top 10</h2><div class="chart-wrap"><canvas id="bar1"></canvas></div></div>
    <div class="card"><h2>{s2} - Top 10</h2><div class="chart-wrap"><canvas id="bar2"></canvas></div></div>
  </div>
  <div class="grid">
    <div class="card full-width"><h2>{s1} - 明细</h2><div class="table-wrap" id="t1"></div></div>
    <div class="card full-width"><h2>{s2} - 明细</h2><div class="table-wrap" id="t2"></div></div>
  </div>
</div>

<!-- TAB 2: Orders -->
<div class="tab-content" id="tab-orders">
  <div class="summary-bar" id="smO"></div>
  <div class="grid">
    <div class="card"><h2>各店铺订单 (Top 15)</h2><div class="chart-wrap" style="height:450px"><canvas id="barOrders"></canvas></div></div>
    <div class="card"><h2>每日汇总 (US/EU/CA)</h2><div class="chart-wrap"><canvas id="barDaily"></canvas></div></div>
  </div>
  <div class="grid">
    <div class="card full-width"><h2>全部明细</h2><div class="table-wrap" id="tOrders"></div></div>
  </div>
</div>

<div class="updated">更新于: <span id="updTime"></span></div>

<!-- TAB 3: Lingxing ERP -->
<div class="tab-content" id="tab-lingxing">
  <div class="summary-bar" id="smLx"></div>
  <div class="grid">
    <div class="card"><h2>每日订单趋势</h2><div class="chart-wrap"><canvas id="lxLine"></canvas></div></div>
    <div class="card"><h2>订单状态分布</h2><div class="chart-wrap"><canvas id="lxPie"></canvas></div></div>
    <div class="card"><h2>Top 15 店铺 (按订单数)</h2><div class="chart-wrap" style="height:400px"><canvas id="lxBar"></canvas></div></div>
    <div class="card"><h2>FBA库存 - 按店铺 Top 20</h2><div class="table-wrap" id="tLxStockByStore"></div></div>
  </div>
  <div class="grid">
    <div class="card full-width"><h2>耳环订单 - 店铺明细</h2><div class="table-wrap" id="tLxCat1"></div></div>
    <div class="card full-width"><h2>新耳环店铺订单 - 店铺明细</h2><div class="table-wrap" id="tLxCat2"></div></div>
  </div>
  <div class="grid">
    <div class="card full-width"><h2>银饰店铺订单 - 店铺明细</h2><div class="table-wrap" id="tLxCat3"></div></div>
    <div class="card full-width"><h2>手链项链订单 - 店铺明细</h2><div class="table-wrap" id="tLxCat4"></div></div>
  </div>
</div>

<script>
var EAR = {ed_json};
var ORD = {od_json};
var DE = {de_json};
var DO = {do_json};
var S1 = '{s1}';
var S2 = '{s2}';
document.getElementById('updTime').textContent = '{datetime.now().strftime("%Y-%m-%d %H:%M")}';
document.getElementById('dateRange').textContent = '最近7天 | 更新于 {datetime.now().strftime("%H:%M")}';

var colors = ['#4472C4','#ED7D31','#70AD47','#FFC000','#5B9BD5','#A5A5A5','#FF6B6B','#4ECDC4','#45B7D1','#96CEB4','#FFEAA7','#DDA0DD','#98D8C8'];

// ===== EAR RING =====
(function(){{
  var s1 = EAR[S1] || {{}};
  var s2 = EAR[S2] || {{}};
  function st(s){{ var e=Object.entries(s); return {{cnt:e.length,total:e.reduce(function(a,x){{return a+x[1].total}},0)}}; }}
  var r1=st(s1), r2=st(s2);
  document.getElementById('smE').innerHTML =
    '<div class="summary-item"><div class="value">'+r1.total.toLocaleString()+'</div><div class="label">'+S1+' ('+r1.cnt+'店铺)</div></div>'+
    '<div class="summary-item"><div class="value">'+r2.total.toLocaleString()+'</div><div class="label">'+S2+' ('+r2.cnt+'店铺)</div></div>'+
    '<div class="summary-item"><div class="value">'+(r1.total+r2.total).toLocaleString()+'</div><div class="label">合计</div></div>';

  function mt(divId, sd){{
    var e=Object.entries(sd).sort(function(a,b){{return b[1].total-a[1].total}});
    var t=e.reduce(function(s,x){{return s+x[1].total}},0);
    var h='<table><thead><tr><th>店铺</th>';
    DE.forEach(function(d){{h+='<th>'+d+'</th>';}});
    h+='<th>合计</th></tr></thead><tbody>';
    e.forEach(function(x){{ h+='<tr><td>'+x[0]+'</td>';
      DE.forEach(function(dd){{h+='<td class=\"num\">'+(x[1].daily[dd]||0)+'</td>';}});
      h+='<td class=\"num\" style=\"font-weight:bold\">'+x[1].total+'</td></tr>'; }});
    h+='<tr class=\"total-row\"><td>合计</td>';
    DE.forEach(function(dd){{var dt=e.reduce(function(s,x){{return s+(x[1].daily[dd]||0)}},0);h+='<td class=\"num\">'+dt+'</td>';}});
    h+='<td class=\"num\">'+t+'</td></tr></tbody></table>';
    document.getElementById(divId).innerHTML=h;
  }}

  function mp(id,sd){{
    var e=Object.entries(sd).sort(function(a,b){{return b[1].total-a[1].total}});
    var l,d;
    if(e.length<=8){{l=e.map(function(x){{return x[0]}});d=e.map(function(x){{return x[1].total}});}}
    else{{l=e.slice(0,8).map(function(x){{return x[0]}}).concat(['其他']);
         d=e.slice(0,8).map(function(x){{return x[1].total}}).concat([e.slice(8).reduce(function(s,x){{return s+x[1].total}},0)]);}}
    if(typeof Chart!=='undefined')new Chart(document.getElementById(id),{{type:'doughnut',
      data:{{labels:l,datasets:[{{data:d,backgroundColor:colors.slice(0,l.length)}}]}},
      options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right',labels:{{font:{{size:10}},padding:6}}}}}}}}}});
  }}

  function mb(id,sd){{
    var top=Object.entries(sd).sort(function(a,b){{return b[1].total-a[1].total}}).slice(0,10);
    if(typeof Chart!=='undefined')new Chart(document.getElementById(id),{{type:'bar',
      data:{{labels:top.map(function(x){{return x[0].length>14?x[0].slice(0,13)+'…':x[0]}}),
            datasets:[{{data:top.map(function(x){{return x[1].total}}),backgroundColor:colors[0],borderRadius:3}}]}},
      options:{{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:true}}}}}}}}}});
  }}

  if(Object.keys(s1).length){{mt('t1',s1);mp('pie1',s1);mb('bar1',s1);}}
  if(Object.keys(s2).length){{mt('t2',s2);mp('pie2',s2);mb('bar2',s2);}}
}})();

// ===== ORDERS =====
(function(){{
  var od=ORD;
  var ent=Object.entries(od).sort(function(a,b){{return b[1].total-a[1].total}});
  var tO=ent.reduce(function(s,x){{return s+x[1].total}},0);
  var tUS=0,tEU=0,tCA=0;
  ent.forEach(function(x){{ DO.forEach(function(d){{tUS+=x[1].daily_us[d]||0;tEU+=x[1].daily_eu[d]||0;tCA+=x[1].daily_ca[d]||0;}}); }});
  document.getElementById('smO').innerHTML =
    '<div class="summary-item"><div class="value">'+tO.toLocaleString()+'</div><div class="label">总订单 ('+ent.length+'店铺)</div></div>'+
    '<div class="summary-item"><div class="value">'+tUS.toLocaleString()+'</div><div class="label">US</div></div>'+
    '<div class="summary-item"><div class="value">'+tEU.toLocaleString()+'</div><div class="label">EU</div></div>'+
    '<div class="summary-item"><div class="value">'+tCA.toLocaleString()+'</div><div class="label">CA</div></div>';

  if(typeof Chart!=='undefined' && ent.length){{
    var top=ent.slice(0,15);
    var c2=['#4472C4','#ED7D31','#70AD47'];
    var ds=[];
    ['US','EU','CA'].forEach(function(r,ri){{
      var k='daily_'+r.toLowerCase();
      ds.push({{label:r,data:top.map(function(x){{return DO.reduce(function(s,d){{return s+(x[1][k][d]||0)}},0);}}),backgroundColor:c2[ri],borderColor:'#333',borderWidth:0.5}});
    }});
    new Chart(document.getElementById('barOrders'),{{type:'bar',
      data:{{labels:top.map(function(x){{return x[0].length>14?x[0].slice(0,13)+'…':x[0]}}),datasets:ds}},
      options:{{responsive:true,maintainAspectRatio:false,indexAxis:'y',
        plugins:{{legend:{{position:'top'}}}},scales:{{x:{{stacked:true,grid:{{display:true}}}},y:{{stacked:true}}}}}}}});
  }}

  if(typeof Chart!=='undefined'){{
    var du=[],de=[],dc=[];
    DO.forEach(function(dd){{du.push(ent.reduce(function(s,x){{return s+(x[1].daily_us[dd]||0)}},0));
      de.push(ent.reduce(function(s,x){{return s+(x[1].daily_eu[dd]||0)}},0));
      dc.push(ent.reduce(function(s,x){{return s+(x[1].daily_ca[dd]||0)}},0));}});
    new Chart(document.getElementById('barDaily'),{{type:'bar',
      data:{{labels:DO,datasets:[{{label:'US',data:du,backgroundColor:c2[0]}},{{label:'EU',data:de,backgroundColor:c2[1]}},{{label:'CA',data:dc,backgroundColor:c2[2]}}]}},
      options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'top'}}}},scales:{{x:{{grid:{{display:true}}}},y:{{stacked:true}}}}}}}});
  }}

  var h='<table><thead><tr><th>店铺</th>';
  DO.forEach(function(d){{h+='<th colspan="4">'+d+'</th>';}});
  h+='<th>合计</th></tr><tr><th></th>';
  DO.forEach(function(d){{h+='<th>US</th><th>EU</th><th>CA</th><th>计</th>';}});
  h+='<th></th></tr></thead><tbody>';
  ent.forEach(function(x){{ h+='<tr><td>'+x[0]+'</td>';
    DO.forEach(function(dd){{var us=x[1].daily_us[dd]||0,eu=x[1].daily_eu[dd]||0,ca=x[1].daily_ca[dd]||0;
      h+='<td class=\"num\">'+us+'</td><td class=\"num\">'+eu+'</td><td class=\"num\">'+ca+'</td><td class=\"num\" style=\"font-weight:bold\">'+(us+eu+ca)+'</td>'; }});
    h+='<td class=\"num\" style=\"font-weight:bold\">'+x[1].total+'</td></tr>'; }});
  h+='<tr class=\"total-row\"><td>合计</td>';
  DO.forEach(function(dd){{var us=ent.reduce(function(s,x){{return s+(x[1].daily_us[dd]||0)}},0);
    var eu=ent.reduce(function(s,x){{return s+(x[1].daily_eu[dd]||0)}},0);
    var ca=ent.reduce(function(s,x){{return s+(x[1].daily_ca[dd]||0)}},0);
    h+='<td class=\"num\">'+us+'</td><td class=\"num\">'+eu+'</td><td class=\"num\">'+ca+'</td><td class=\"num\">'+(us+eu+ca)+'</td>';}});
  h+='<td class=\"num\">'+tO+'</td></tr></tbody></table>';
  document.getElementById('tOrders').innerHTML=h;
}})();

// ===== LINGXING ERP =====
var LX = {lx_json};
if (LX) {{
  document.getElementById('smLx').innerHTML =
    '<div class="summary-item"><div class="value">'+LX.total_orders.toLocaleString()+'</div><div class="label">总订单 ('+LX.shops_count+'店铺)</div></div>'+
    '<div class="summary-item"><div class="value">$'+LX.total_amount.toLocaleString()+'</div><div class="label">订单总额</div></div>'+
    '<div class="summary-item"><div class="value">'+LX.stock_summary.available.toLocaleString()+'</div><div class="label">FBA可售库存</div></div>'+
    '<div class="summary-item"><div class="value">'+LX.stock_summary.unsellable.toLocaleString()+'</div><div class="label">FBA不可售</div></div>'+
    '<div class="summary-item"><div class="value">'+LX.stock_summary.inbound.toLocaleString()+'</div><div class="label">在途</div></div>';

  // Daily order line chart
  if(typeof Chart!=='undefined' && LX.dates.length){{
    var dailyOrders = LX.dates.map(function(d, i){{
      var total = 0;
      Object.values(LX.orders).forEach(function(s){{ total += (s.daily[d]||0); }});
      return total;
    }});
    new Chart(document.getElementById('lxLine'),{{type:'line',
      data:{{labels:LX.dates, datasets:[{{data:dailyOrders, borderColor:'#4472C4', backgroundColor:'rgba(68,114,196,0.1)', fill:true, tension:0.3, pointRadius:5, pointBackgroundColor:'#4472C4'}}]}},
      options:{{responsive:true, maintainAspectRatio:false,
        plugins:{{legend:{{display:false}}, tooltip:{{callbacks:{{label:function(c){{return c.raw+' 单'}}}}}}}},
        scales:{{y:{{beginAtZero:true, grid:{{display:true}}}}}}}}}});
  }}

  // Order status doughnut
  if(typeof Chart!=='undefined' && LX.status){{
    var sc = LX.status;
    var slabels = Object.keys(sc), sdata = Object.values(sc);
    var scols = ['#4472C4','#70AD47','#ED7D31','#FFC000','#A5A5A5'];
    new Chart(document.getElementById('lxPie'),{{type:'doughnut',
      data:{{labels:slabels, datasets:[{{data:sdata, backgroundColor:scols.slice(0,slabels.length)}}]}},
      options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'right', labels:{{font:{{size:10}}, padding:6}}}}}}}}}});
  }}

  // Top 15 stores by orders
  if(typeof Chart!=='undefined'){{
    var topO = Object.entries(LX.orders).sort(function(a,b){{return b[1].total-a[1].total;}}).slice(0,15);
    new Chart(document.getElementById('lxBar'),{{type:'bar',
      data:{{labels:topO.map(function(x){{return x[0].length>18?x[0].slice(0,17)+'...':x[0];}}),
            datasets:[{{data:topO.map(function(x){{return x[1].total;}}), backgroundColor:colors[0], borderRadius:3}}]}},
      options:{{responsive:true, maintainAspectRatio:false, indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales:{{x:{{grid:{{display:true}}}}}}}}}});
  }}

  // FBA stock grouped by store (top 20)
  (function(){{
    var storeStock = {{}};
    var suffixes = ['美国仓','加拿大仓','北美仓','欧洲仓','英国仓','墨西哥仓','巴西仓'];
    Object.entries(LX.warehouse_stock || {{}}).forEach(function(e){{
      var wname = e[0], stock = e[1];
      var sname = wname;
      suffixes.forEach(function(suf){{ if(sname.endsWith(suf)) sname = sname.slice(0, -suf.length); }});
      if(!storeStock[sname]) storeStock[sname] = {{available:0, pending:0, inbound:0, unsellable:0, skus:0}};
      storeStock[sname].available += stock.available;
      storeStock[sname].pending += stock.pending;
      storeStock[sname].inbound += stock.inbound;
      storeStock[sname].unsellable += stock.unsellable;
      storeStock[sname].skus += stock.skus;
    }});
    var top20 = Object.entries(storeStock).sort(function(a,b){{return b[1].available-a[1].available;}}).slice(0,20);
    var h = '<table><thead><tr><th>店铺</th><th>可售</th><th>待发货</th><th>在途</th><th>不可售</th><th>SKU数</th></tr></thead><tbody>';
    top20.forEach(function(x){{
      h += '<tr><td>'+x[0]+'</td><td class="num">'+x[1].available.toLocaleString()+'</td><td class="num">'+x[1].pending.toLocaleString()+'</td><td class="num">'+x[1].inbound.toLocaleString()+'</td><td class="num">'+x[1].unsellable.toLocaleString()+'</td><td class="num">'+x[1].skus+'</td></tr>';
    }});
    h += '</tbody></table>';
    document.getElementById('tLxStockByStore').innerHTML = h;
  }})();

  // Categorized order detail tables (all stores, order count only)
  (function(){{
    var norm = function(s){{ return s.toLowerCase().replace(/\\s+/g,''); }};
    var cats = [
      {{id:'tLxCat1', kw:['GIORGIA GIBBS','SLMYUER','GIULIA LEONI','varger','KATIE OTTE','ELEBEST','AMELINE','Selroper','SHERRIE DOBBIE','SPLIM','vuiikhir','AIGAMIT','Fanglcy','DZCYAN','Degerde','Aidomiya','TONYAUTOPARTS','GLOSOLE','Verniflloga','HaoShuFu','SPACMAG','ENROSE','KFERAXSZ','SPOINT','JADE KOS','CHLOÉ LOVETT','SANDRA REDD','HOBATS','MOMELF','NEARLAND','USESMTLE','Kelli Myers','Chantel Yorke','COSSA','BANGALO','Kate','Eterbeau','Amoxos','Fureoai','TAKUGI','VESTACE','Fureylenx','BalaBelle','LISHUIHAOMI']}},
      {{id:'tLxCat2', kw:['Cendyess','worfey','Magifurni','Tuogzzdq','EXRSANCH','VSK','KKR','POHYEOL','CALLIOPE','ESSIE ODILA','YFdeSi','Maodeso','JOZZFEE','nuoxun','Daolianlo','Lageza','iewrsox','Yiidcii','Aolumio','kvvkii','Howe rai','Sincere-ljh','Yezhenhan','SPARSE FOREST','PWQIEE','DOXVO','FOCALLIVE','niratty','YAUVC','Raysam','UUBUUCD','VTEVER','BEAUSPA','gotoeewigs','Lamdesa','SREEOWER','TECYOW','Charmire','Eloqueen']}},
      {{id:'tLxCat3', kw:['LIEBLICH','ESSIE','Annamate','CHICLOVE','Billie Bijoux','Van Chloe','ANNIS MUNN','ANNIS','AmorAime','BlingGem','NinaMaid']}},
      {{id:'tLxCat4', kw:['MELELIFE','KYAYE','HIROM JOINS','Moonfox','Simlayton','STREYANT','LOKFAM','FEGER','CANNCI','CISSIEPERAL','ERIN MARIE','BENOITE','AOZELAN','OR OLD RUBIN','OLD RUBIN','PPRLIFE','Rewizoo','KROMPG','MONA MILANI','PESFIOLO','gcwen','WONRUN','CROCHETFUN','iSunat','CKUSCAPO','UHEPROKIT','LUXCUTY','EYUMOI','Naiswan','LEMKAY','BYBAIZ','YIYEPUTI','Qeces','TOBENO','Yzytdgzy','Rinponain','TUOIXPI','KHFGDS','ODIHUI','LOUISE VELLA','MISSZHI','koolfin','FENMI']}}
    ];
    var allStores = Object.entries(LX.orders).sort(function(a,b){{return b[1].total-a[1].total;}});
    var assigned = {{}};

    cats.forEach(function(cat){{
      var stores = [];
      allStores.forEach(function(x){{
        if(assigned[x[0]]) return;
        var match = false;
        cat.kw.forEach(function(k){{ if(norm(x[0]).indexOf(norm(k)) !== -1) match = true; }});
        if(match){{ assigned[x[0]] = true; stores.push(x); }}
      }});

      var h = '<table><thead><tr><th>店铺</th>';
      LX.dates.forEach(function(d){{ h += '<th>'+d+'</th>'; }});
      h += '<th>合计</th></tr></thead><tbody>';
      var total = 0;
      stores.forEach(function(x){{
        h += '<tr><td>'+x[0]+'</td>';
        LX.dates.forEach(function(d){{ h += '<td class="num">'+(x[1].daily[d]||0)+'</td>'; }});
        h += '<td class="num" style="font-weight:bold">'+x[1].total+'</td></tr>';
        total += x[1].total;
      }});
      h += '<tr class="total-row"><td>合计 ('+stores.length+'店铺)</td>';
      LX.dates.forEach(function(d){{
        var dt = stores.reduce(function(s,x){{return s+(x[1].daily[d]||0);}},0);
        h += '<td class="num">'+dt+'</td>';
      }});
      h += '<td class="num">'+total+'</td></tr></tbody></table>';
      document.getElementById(cat.id).innerHTML = stores.length ? h : '<p style="color:#999;text-align:center;padding:20px">该分类暂无匹配店铺</p>';
    }});
  }})();
}}

function switchTab(name){{
  document.querySelectorAll('.tab').forEach(function(t){{t.classList.remove('active');}});
  document.querySelectorAll('.tab-content').forEach(function(c){{c.classList.remove('active');}});
  document.getElementById('tab-'+name).classList.add('active');
  event.target.classList.add('active');
}}
</script>
</body>
</html>'''

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"[{datetime.now()}] HTML generated")
