"""处理领星ERP JSON数据 → 仪表盘 JS 变量"""
import json
from collections import defaultdict
from datetime import datetime


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

    return {
        "dates": fmt_dates,
        "dates_raw": dates,
        "orders": orders_data,
        "status": dict(status_counts),
        "stock_summary": stock_summary,
        "warehouse_stock": warehouse_data,
        "top_skus": top_skus,
        "total_orders": len(orders),
        "total_amount": round(sum(float(o.get("order_total_amount", 0) or 0) for o in orders), 2),
        "shops_count": len(orders_data),
    }


def _int(v) -> int:
    try:
        return int(v) if v else 0
    except (ValueError, TypeError):
        return 0


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/Admin/lingxing-api/lingxing_20260611_163012.json"
    result = process(path)
    print(json.dumps({k: v for k, v in result.items() if k not in ("orders", "warehouse_stock")}, ensure_ascii=False, indent=2))
    print(f"\nTop stores: {list(result['orders'].keys())[:10]}")
    print(f"Top warehouses: {list(result['warehouse_stock'].keys())[:5]}")
