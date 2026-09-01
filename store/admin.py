from django.contrib import admin
from .models import (
    Category,
    Address, Coupon, CouponUsage, Customer, InventoryTransaction, Notification,
    Order, OrderItem, OrderStatusHistory, Payment, Product, ProductImage,
    ProductTraceability, Review, Weaver, Wishlist,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active", "sort_order", "created_at")
    list_filter = ("active",)
    search_fields = ("name", "slug")
    list_editable = ("active", "sort_order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "stock", "featured", "active")
    list_filter = ("category", "featured", "active", "fabric")
    search_fields = ("name", "sku", "fabric", "colour", "pattern")
    list_editable = ("price", "stock", "featured", "active")
    prepopulated_fields = {}


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "sort_order", "alt")
    list_filter = ("product",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "role", "created_at")
    search_fields = ("name", "phone", "email")
    list_filter = ("role",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "label", "city", "state", "pincode", "is_default")
    search_fields = ("customer__name", "phone", "pincode")
    list_filter = ("state", "is_default")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "quantity", "price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "customer", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("shipping_name", "shipping_phone", "customer__name")
    list_editable = ("status",)
    inlines = [OrderItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "status", "amount", "transaction_id", "created_at")
    list_filter = ("method", "status")
    search_fields = ("order__id", "transaction_id")


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "changed_by", "created_at")
    list_filter = ("status", "created_at")


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ("product", "kind", "quantity", "reference", "created_by", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("product__name", "reference", "note")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "kind", "value", "minimum_order", "used_count", "active", "expires_at")
    list_filter = ("kind", "active")
    search_fields = ("code",)


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ("coupon", "customer", "order", "used_at")
    search_fields = ("coupon__code", "customer__name", "order__id")


@admin.register(Weaver)
class WeaverAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "specialization", "years", "active")
    list_filter = ("active", "location")
    search_fields = ("name", "location", "specialization")


@admin.register(ProductTraceability)
class ProductTraceabilityAdmin(admin.ModelAdmin):
    list_display = ("product", "step", "title", "completed")
    list_filter = ("completed",)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "created_at")
    search_fields = ("customer__name", "product__name")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "customer", "rating", "approved", "created_at")
    list_filter = ("rating", "approved")
    search_fields = ("product__name", "customer__name", "body")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("customer", "title", "read", "created_at")
    list_filter = ("read", "created_at")
    search_fields = ("customer__name", "title", "message")


admin.site.site_header = "POWERLOOM · WORKSHOP ADMIN"
admin.site.site_title = "Powerloom Admin"
admin.site.index_title = "Business Control Centre"
