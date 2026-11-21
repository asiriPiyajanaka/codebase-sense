def cancel(repository, order_id):
    repository.mark_cancelled(order_id)
    return {"cancelled": True}
