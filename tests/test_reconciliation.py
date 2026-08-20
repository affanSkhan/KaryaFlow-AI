import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('kmain', Path(__file__).parents[1] / 'app' / 'main.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def document(doc_type, vendor='ABC Manufacturing', qty=100, price=45, po='PO-1042'):
    return {
        'document_type': doc_type,
        'document_label': mod.TYPE_LABELS[doc_type],
        'filename': f'{doc_type}.txt',
        'vendor': vendor,
        'po_number': po,
        'invoice_number': 'INV-8831',
        'date': '2026-08-21',
        'items': [{'description': 'Steel Bolt M10', 'quantity': qty, 'unit_price': price}],
        'quantity': qty,
        'unit_price': price,
        'total': qty * price,
        'raw_text': f'Vendor: {vendor}\nQuantity: {qty}\nUnit Price: {price}\nPO Number: {po}',
    }


def test_match():
    result = mod.reconcile({
        'purchase_order': document('purchase_order'),
        'invoice': document('invoice'),
        'delivery_challan': document('delivery_challan'),
    })
    assert result['status'] == 'MATCH'
    assert result['score'] == 100


def test_quantity_exception():
    result = mod.reconcile({
        'purchase_order': document('purchase_order', qty=100),
        'invoice': document('invoice', qty=120),
        'delivery_challan': document('delivery_challan', qty=100),
    })
    assert result['status'] == 'EXCEPTION'
    quantity = next(x for x in result['checks'] if x['key'] == 'quantity')
    assert quantity['variance']['invoice'] == 20


def test_incomplete_case():
    result = mod.reconcile({'purchase_order': document('purchase_order')})
    assert result['status'] == 'INCOMPLETE'
