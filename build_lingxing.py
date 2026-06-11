"""Build standalone Lingxing ERP dashboard page."""
import json, sys
from datetime import datetime

def main():
    try:
        with open("lingxing_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("lingxing_data.json not found, exiting")
        sys.exit(1)

    lx_json = json.dumps(data, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data_time = data.get("pull_time", now)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>领星ERP仪表盘</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Microsoft YaHei', sans-serif; background:#f0f2f5; color:#333; padding:16px; }}
.header {{ text-align:center; margin-bottom:16px; }}
.header h1 {{ font-size:22px; color:#1a1a2e; }}
.header p {{ color:#666; margin-top:2px; font-size:12px; }}
.nav {{ text-align:center; margin-bottom:10px; }}
.nav a {{ color:#4472C4; text-decoration:none; font-size:13px; padding:6px 14px; background:#fff; border-radius:6px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
.nav a:hover {{ background:#4472C4; color:#fff; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px; }}
.card {{ background:#fff; border-radius:10px; padding:14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); }}
.card h2 {{ font-size:14px; margin-bottom:8px; border-bottom:2px solid #4472C4; padding-bottom:5px; }}
.chart-wrap {{ position:relative; height:280px; }}
.chart-wrap.tall {{ height:400px; }}
.table-wrap {{ max-height:500px; overflow-y:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:11px; }}
th {{ background:#4472C4; color:#fff; padding:5px 3px; position:sticky; top:0; z-index:1; text-align:center; white-space:nowrap; }}
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
.footer {{ text-align:right; color:#aaa; font-size:10px; margin-top:8px; }}
@media (max-width:768px) {{ .grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="header"><h1>领星ERP 仪表盘</h1><p id="dateRange"></p></div>
<div class="summary-bar" id="smLx"></div>

<div class="grid">
  <div class="card"><h2>每日订单趋势</h2><div class="chart-wrap"><canvas id="lxLine"></canvas></div></div>
  <div class="card"><h2>订单状态分布</h2><div class="chart-wrap"><canvas id="lxPie"></canvas></div></div>
  <div class="card"><h2>Top 15 店铺 (按订单数)</h2><div class="chart-wrap tall"><canvas id="lxBar"></canvas></div></div>
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

<div class="footer">数据拉取: {data_time} | 页面生成: {now}</div>

<script>
var LX = {lx_json};
document.getElementById('dateRange').textContent = '最近7天 | ' + LX.total_orders.toLocaleString() + ' 单 | ' + LX.shops_count + ' 店铺';

var colors = ['#4472C4','#ED7D31','#70AD47','#FFC000','#5B9BD5','#A5A5A5','#FF6B6B','#4ECDC4','#45B7D1','#96CEB4','#FFEAA7','#DDA0DD','#98D8C8'];

if (LX) {{
  document.getElementById('smLx').innerHTML =
    '<div class="summary-item"><div class="value">'+LX.total_orders.toLocaleString()+'</div><div class="label">总订单 ('+LX.shops_count+'店铺)</div></div>'+
    '<div class="summary-item"><div class="value">$'+LX.total_amount.toLocaleString()+'</div><div class="label">订单总额</div></div>'+
    '<div class="summary-item"><div class="value">'+LX.stock_summary.available.toLocaleString()+'</div><div class="label">FBA可售库存</div></div>'+
    '<div class="summary-item"><div class="value">'+LX.stock_summary.unsellable.toLocaleString()+'</div><div class="label">FBA不可售</div></div>'+
    '<div class="summary-item"><div class="value">'+LX.stock_summary.inbound.toLocaleString()+'</div><div class="label">在途</div></div>';

  // Daily order line chart
  if(typeof Chart!=='undefined' && LX.dates.length){{
    var dailyOrders = LX.dates.map(function(d){{
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
      {{id:'tLxCat1', kw:['GIORGIA GIBBS','SLMYUER','GIULIA LEONI','varger','KATIE OTTE','ELEBEST','AMELINE','Selroper','SHERRIE DOBBIE','SPLIM','vuiikhir','ALUUYANN','AIGAMIT','Fanglcy','DZCYAN','Degerde','Aidomiya','TONYAUTOPARTS','GLOSOLE','Verniflloga','HaoShuFu','SPACMAG','ENROSE','KFERAXSZ','SPOINT','JADE KOS','CHLOÉ LOVETT','SANDRA REDD','HOBATS','MOMELF','NEARLAND','USESMTLE','Kelli Myers','ongol','Chantel Yorke','COSSA','BANGALO','Kate','Eterbeau','Amoxos','Fureoai','TAKUGI','VESTACE','Fureylenx','BalaBelle','LISHUIHAOMI']}},
      {{id:'tLxCat2', kw:['Cendyess','worfey','Magifurni','Tuogzzdq','EXRSANCH','VSK','KKR','POHYEOL','CALLIOPE','ESSIE ODILA','YFdeSi','Maodeso','JOZZFEE','nuoxun','Daolianlo','Lageza','iewrsox','Yiidcii','Aolumio','kvvkii','Howe rai','Sincere-ljh','Yezhenhan','SPARSE FOREST','PWQIEE','DOXVO','FOCALLIVE','niratty','YAUVC','Raysam','UUBUUCD','VTEVER','BEAUSPA','gotoeewigs','Lamdesa','SREEOWER','TECYOW','Charmire','Eloqueen','TG544','香港諾迅','鹏宇贸易','TG411','TG400']}},
      {{id:'tLxCat3', kw:['LIEBLICH','ESSIE','Annamate','CHICLOVE','Billie Bijoux','Van Chloe','ANNIS MUNN','ANNIS','AmorAime','BlingGem','NinaMaid','WISHMISS']}},
      {{id:'tLxCat4', kw:['MELELIFE','KYAYE','HIROM JOINS','Moonfox','Simlayton','STREYANT','LOKFAM','FEGER','CANNCI','CISSIEPERAL','ERIN MARIE','BENOITE','AOZELAN','OR OLD RUBIN','OLD RUBIN','PPRLIFE','Rewizoo','KROMPG','MONA MILANI','PESFIOLO','gcwen','WONRUN','CROCHETFUN','iSunat','CKUSCAPO','UHEPROKIT','LUXCUTY','EYUMOI','Naiswan','LEMKAY','BYBAIZ','YIYEPUTI','Qeces','TOBENO','Yzytdgzy','Rinponain','TUOIXPI','KHFGDS','ODIHUI','LOUISE VELLA','MISSZHI','koolfin','FENMI','GYUYCW','Zikonyou','SUNDINS','香港惠拓','SparkSphere']}}
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
</script>
</body>
</html>'''

    with open("lingxing.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[{now}] lingxing.html generated")


if __name__ == "__main__":
    main()
