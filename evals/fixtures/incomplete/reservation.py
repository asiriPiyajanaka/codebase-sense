def reserve(adapter, request_id, sku, quantity):
    if not request_id or not sku or type(quantity) is not int or quantity <= 0:
        raise ValueError("invalid reservation")
    return adapter.reserve(request_id, sku, quantity)
