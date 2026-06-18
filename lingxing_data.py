"""处理领星ERP JSON数据 → 仪表盘 JS 变量"""
import json
from collections import defaultdict
from datetime import datetime, timedelta


def process(lingxing_json_path: str, days: int = 7):
    with open(lingxing_json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    orders = raw.get("orders", [])
    stocks = raw.get("stocks", [])

    # ── 订单：按店铺×日期 聚合 ──────────────────────────
    shop_daily = defaultdict(lambda: {"daily": defaultdict(int), "amount": defaultdict(float), "total": 0, "total_amount": 0.0})
    status_counts = defaultdict(int)
    dates_set = set()

    for o in orders:
        d = (o.get("purchase_date_local") or "")[:10]
        if not d:
            continue
        dates_set.add(d)
        name = o.get("seller_name", "?")
        qty = 1
        amt = float(o.get("order_total_amount", 0) or 0)
        shop_daily[name]["daily"][d] += qty
        shop_daily[name]["amount"][d] += amt
        shop_daily[name]["total"] += qty
        shop_daily[name]["total_amount"] += amt
        status_counts[o.get("order_status", "?")] += 1

    dates = sorted(dates_set)[-days:] if len(dates_set) > days else sorted(dates_set)
    fmt_dates = [datetime.strptime(d, "%Y-%m-%d").strftime("%m/%d") for d in dates]

    # 按 total 排序
    orders_data = {}
    for name, d in sorted(shop_daily.items(), key=lambda x: x[1]["total"], reverse=True):
        orders_data[name] = {
            "daily": {fmt_dates[i]: d["daily"].get(date, 0) for i, date in enumerate(dates)},
            "amount": {fmt_dates[i]: round(d["amount"].get(date, 0), 2) for i, date in enumerate(dates)},
            "total": d["total"],
            "total_amount": round(d["total_amount"], 2),
        }

    # ── FBA 库存摘要 ──────────────────────────────────
    stock_summary = {
        "total_skus": len(stocks),
        "available": sum(_int(s.get("afn_fulfillable_quantity")) for s in stocks),
        "pending": sum(_int(s.get("reserved_customerorders")) for s in stocks),
        "inbound": sum(_int(s.get("afn_inbound_shipped_quantity")) for s in stocks),
        "unsellable": sum(_int(s.get("afn_unsellable_quantity")) for s in stocks),
    }

    # 按仓库聚合
    warehouse_stock = defaultdict(lambda: {"available": 0, "pending": 0, "inbound": 0, "unsellable": 0, "skus": 0})
    for s in stocks:
        w = s.get("wname") or s.get("name", "?")
        warehouse_stock[w]["available"] += _int(s.get("afn_fulfillable_quantity"))
        warehouse_stock[w]["pending"] += _int(s.get("reserved_customerorders"))
        warehouse_stock[w]["inbound"] += _int(s.get("afn_inbound_shipped_quantity"))
        warehouse_stock[w]["unsellable"] += _int(s.get("afn_unsellable_quantity"))
        warehouse_stock[w]["skus"] += 1

    warehouse_data = {k: v for k, v in sorted(warehouse_stock.items(), key=lambda x: x[1]["available"], reverse=True)}

    # Top 20 SKU by available
    top_skus = []
    for s in sorted(stocks, key=lambda x: _int(x.get("afn_fulfillable_quantity", 0)), reverse=True)[:20]:
        top_skus.append({
            "sku": s.get("sku") or s.get("msku", ""),
            "name": (s.get("product_name") or "")[:30],
            "asin": s.get("asin", ""),
            "available": _int(s.get("afn_fulfillable_quantity")),
            "pending": _int(s.get("reserved_customerorders")),
            "inbound": _int(s.get("afn_inbound_shipped_quantity")),
            "unsellable": _int(s.get("afn_unsellable_quantity")),
        })

    # Exclude silver stores (moved to standalone silver-dashboard)
    silver_kw = ['LIEBLICH','ESSIE','Annamate','CHICLOVE','Billie Bijoux','Van Chloe','ANNIS MUNN','ANNIS','AmorAime','BlingGem','NinaMaid','WISHMISS']
    def _is_silver(name):
        n = name.lower().replace(" ", "")
        for k in silver_kw:
            # Match whole keyword first, then individual parts (handles warehouse name typos)
            if k.lower().replace(" ", "") in n:
                return True
            for part in k.lower().split():
                if part in n:
                    return True
        return False

    # Exclude silver from orders + warehouse
    non_silver_orders = {k: v for k, v in orders_data.items() if not _is_silver(k)}
    non_silver_warehouse = {k: v for k, v in warehouse_data.items() if not _is_silver(k)}

    # Recalculate totals without silver
    non_silver_total_orders = sum(v["total"] for v in non_silver_orders.values())
    non_silver_total_amount = sum(v["total_amount"] for v in non_silver_orders.values())

    return {
        "dates": fmt_dates,
        "dates_raw": dates,
        "orders": non_silver_orders,
        "status": dict(status_counts),
        "stock_summary": stock_summary,
        "warehouse_stock": non_silver_warehouse,
        "top_skus": top_skus,
        "total_orders": non_silver_total_orders,
        "total_amount": round(non_silver_total_amount, 2),
        "shops_count": len(non_silver_orders),
    }


def _int(v) -> int:
    try:
        return int(v) if v else 0
    except (ValueError, TypeError):
        return 0


if __name__ == "__main__":
    import sys, argparse, os
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="C:/Users/Admin/lingxing-api/lingxing_20260611_163012.json")
    parser.add_argument("-o", "--output", default=None, help="直接写入 JSON 文件")
    args = parser.parse_args()

    result = process(args.input)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
        print(f"Saved to {args.output}")

        # Also generate silver-only data file
        silver_kw = ['LIEBLICH','ESSIE','Annamate','CHICLOVE','Billie Bijoux','Van Chloe','ANNIS MUNN','ANNIS','AmorAime','BlingGem','NinaMaid','WISHMISS']
        def _is_silver(name):
            n = name.lower().replace(" ", "")
            return any(k.lower().replace(" ", "") in n for k in silver_kw)

        with open(args.input, "r", encoding="utf-8") as f:
            raw = json.load(f)
        orders = raw.get("orders", [])
        shop_daily = {}
        from collections import defaultdict
        shop_daily = defaultdict(lambda: {"daily": defaultdict(int), "amount": defaultdict(float), "total": 0, "total_amount": 0.0})
        dates_set = set()
        for o in orders:
            d = (o.get("purchase_date_local") or "")[:10]
            if not d: continue
            dates_set.add(d)
            name = o.get("seller_name", "?")
            if not _is_silver(name): continue
            amt = float(o.get("order_total_amount", 0) or 0)
            shop_daily[name]["daily"][d] += 1
            shop_daily[name]["amount"][d] += amt
            shop_daily[name]["total"] += 1
            shop_daily[name]["total_amount"] += amt
        dates = sorted(dates_set)[-7:]
        fmt_dates = [datetime.strptime(d, "%Y-%m-%d").strftime("%m/%d") for d in dates]
        silver_orders = {}
        for name, d in sorted(shop_daily.items(), key=lambda x: x[1]["total"], reverse=True):
            silver_orders[name] = {
                "daily": {fmt_dates[i]: d["daily"].get(date, 0) for i, date in enumerate(dates)},
                "amount": {fmt_dates[i]: round(d["amount"].get(date, 0), 2) for i, date in enumerate(dates)},
                "total": d["total"],
                "total_amount": round(d["total_amount"], 2),
            }
        # FBA stock for silver stores
        stocks = raw.get("stocks", [])
        sw = defaultdict(lambda: {"available": 0, "pending": 0, "inbound": 0, "unsellable": 0, "skus": 0})
        for s in stocks:
            w = s.get("wname") or s.get("name", "?")
            if not _is_silver(w): continue
            sw[w]["available"] += int(s.get("afn_fulfillable_quantity", 0) or 0)
            sw[w]["pending"] += int(s.get("reserved_customerorders", 0) or 0)
            sw[w]["inbound"] += int(s.get("afn_inbound_shipped_quantity", 0) or 0)
            sw[w]["unsellable"] += int(s.get("afn_unsellable_quantity", 0) or 0)
            sw[w]["skus"] += 1
        silver_warehouse = dict(sorted(sw.items(), key=lambda x: x[1]["available"], reverse=True))

        silver_data = {
            "pull_time": raw.get("pull_time", ""),
            "dates": fmt_dates,
            "orders": silver_orders,
            "warehouse_stock": silver_warehouse,
            "total_orders": sum(v["total"] for v in silver_orders.values()),
            "shops_count": len(silver_orders),
        }
        silver_path = os.path.join(os.path.dirname(args.output), "silver_data.json")
        with open(silver_path, "w", encoding="utf-8") as f:
            json.dump(silver_data, f, ensure_ascii=False)
        print(f"Silver data saved to {silver_path} ({silver_data['total_orders']} orders)")

    else:
        summary = {k: v for k, v in result.items() if k not in ("orders", "warehouse_stock")}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n{result['total_orders']} orders, {result['shops_count']} stores, {result['stock_summary']['available']} FBA available")
