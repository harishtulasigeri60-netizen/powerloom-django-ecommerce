# Architecture

Browser → Django URLs → views/services → Django ORM → SQLite or PostgreSQL

Commerce invariants:
- Product price is copied into OrderItem.price at checkout.
- OrderItem.subtotal = price × quantity.
- Order.subtotal = sum(OrderItem.subtotal).
- Discount is calculated from the server-side subtotal.
- Inventory is locked with `select_for_update()` while an order is created.
- Stock movement is recorded in InventoryTransaction.
- Order status changes are recorded in OrderStatusHistory.
- Payment is recorded separately from the order.

The current build keeps the existing single-app Django structure intentionally so it remains easy to understand in a student/recruiter review while still separating major business concepts into models and management areas.
