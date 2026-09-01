from decimal import Decimal
from io import BytesIO
import json
import uuid
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Sum, F, Avg
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .decorators import admin_only, customer_only
from .forms import AddressForm, CategoryForm, CouponForm, CustomerAdminForm, CustomerCheckoutForm, CustomerRegisterForm, ProductForm, ReviewForm
from .models import (
    Address, Category, Coupon, CouponUsage, Customer, InventoryTransaction, Notification,
    Order, OrderItem, OrderStatusHistory, Payment, Product, ProductTraceability,
    Review, Weaver, Wishlist,
)

TAX_RATE = Decimal("0.00")
SHIPPING_FLAT = Decimal("0.00")


def _money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _customer(request):
    if not request.user.is_authenticated or request.user.is_staff:
        return None
    profile = getattr(request.user, "customer_profile", None)
    if profile is None:
        profile = Customer.objects.create(
            user=request.user,
            name=request.user.get_full_name() or request.user.username,
            phone="",
            email=request.user.email,
        )
    return profile


def _cart(request):
    return request.session.get("cart", {}) or {}


def cart_data(request):
    """Return cart lines and the exact DB-price × quantity total."""
    cart = _cart(request)
    items, total, cleaned = [], Decimal("0.00"), {}

    for raw_pid, raw_qty in cart.items():
        try:
            pid = int(raw_pid)
            qty = int(raw_qty)
        except (TypeError, ValueError):
            continue

        product = Product.objects.filter(pk=pid, active=True).first()
        if not product or qty < 1 or product.stock < 1:
            continue

        qty = min(qty, product.stock)
        subtotal = _money(product.price * qty)
        cleaned[str(pid)] = qty
        items.append({
            "product": product,
            "quantity": qty,
            "price": product.price,
            "subtotal": subtotal,
        })
        total += subtotal

    total = _money(total)
    if cleaned != cart:
        request.session["cart"] = cleaned
        request.session.modified = True
    return items, total


def _coupon_valid(coupon, subtotal, now=None, customer=None):
    if not coupon or not coupon.active:
        return False, Decimal("0.00"), "Coupon not found."
    now = now or timezone.now()
    if coupon.starts_at and now < coupon.starts_at:
        return False, Decimal("0.00"), "Coupon is not active yet."
    if coupon.expires_at and now > coupon.expires_at:
        return False, Decimal("0.00"), "Coupon has expired."
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        return False, Decimal("0.00"), "Coupon usage limit reached."
    if subtotal < coupon.minimum_order:
        return False, Decimal("0.00"), f"Minimum order is ₹{coupon.minimum_order:,.2f}."
    if customer and CouponUsage.objects.filter(coupon=coupon, customer=customer).exists():
        return False, Decimal("0.00"), "You have already used this coupon."

    if coupon.kind == "percent":
        discount = subtotal * coupon.value / Decimal("100")
    else:
        discount = coupon.value
    if coupon.maximum_discount:
        discount = min(discount, coupon.maximum_discount)
    discount = min(discount, subtotal)
    return True, _money(discount), ""


def _checkout_totals(subtotal, coupon=None, customer=None):
    valid, discount, _ = _coupon_valid(coupon, subtotal, customer=customer) if coupon else (True, Decimal("0.00"), "")
    if not valid:
        discount = Decimal("0.00")
    shipping = SHIPPING_FLAT
    tax = _money((subtotal - discount) * TAX_RATE / Decimal("100"))
    total = _money(subtotal - discount + shipping + tax)
    return _money(subtotal), discount, shipping, tax, total


def home(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_dashboard")
    featured = Product.objects.filter(active=True, featured=True).select_related("weaver")[:6]
    products = Product.objects.filter(active=True).select_related("weaver")[:8]
    return render(request, "home.html", {
        "featured": featured,
        "products": products,
        "weavers": Weaver.objects.filter(active=True)[:3],
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard" if request.user.is_staff else "catalog")
    role = request.GET.get("role") or request.POST.get("role")
    if role not in {"customer", "admin"}:
        return render(request, "auth/login.html", {"role_select": True, "next": request.GET.get("next", "")})
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user:
            if role == "admin" and not user.is_staff:
                messages.error(request, "This account is a customer account. Choose Customer sign in.")
            elif role == "customer" and user.is_staff:
                messages.error(request, "This is an admin account. Choose Admin sign in.")
            else:
                login(request, user)
                next_url = request.GET.get("next", "") or request.POST.get("next", "")
                if url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()):
                    return redirect(next_url)
                return redirect("admin_dashboard" if user.is_staff else "catalog")
        else:
            messages.error(request, "Incorrect username or password.")
    return render(request, "auth/login.html", {"role": role, "role_select": False, "next": request.GET.get("next", "")})


def logout_view(request):
    logout(request)
    return redirect("home")


def register(request):
    if request.user.is_authenticated:
        return redirect("catalog")
    form = CustomerRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            user = User.objects.create_user(
                username=d["username"], password=d["password"], email=d["email"]
            )
            customer = Customer.objects.create(
                user=user, name=d["name"], phone=d["phone"], email=d["email"], address=d["address"]
            )
            if d["address"]:
                Address.objects.create(
                    customer=customer, label="Home", name=customer.name, phone=customer.phone,
                    address=customer.address, city="Bengaluru", state="Karnataka", pincode="000000", is_default=True,
                )
        login(request, user)
        messages.success(request, "Welcome to Powerloom.")
        return redirect("catalog")
    return render(request, "auth/register.html", {"form": form})


@customer_only
def profile(request):
    customer = _customer(request)
    form = AddressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data.get("is_default"):
            Address.objects.filter(customer=customer).update(is_default=False)
        address = form.save(commit=False)
        address.customer = customer
        address.save()
        messages.success(request, "Address saved.")
        return redirect("profile")
    return render(request, "customer/profile.html", {
        "customer": customer,
        "addresses": customer.addresses.all(),
        "form": form,
        "notifications": customer.notifications.all()[:8],
    })


@customer_only
def notifications(request):
    customer = _customer(request)
    customer.notifications.filter(read=False).update(read=True)
    return render(request, "customer/notifications.html", {"notifications": customer.notifications.all()})


@customer_only
def catalog(request):
    qs = Product.objects.filter(active=True).select_related("weaver").annotate(avg_rating=Avg("reviews__rating"))
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    fabric = request.GET.get("fabric", "")
    colour = request.GET.get("colour", "")
    sort = request.GET.get("sort", "newest")
    minp = request.GET.get("min", "")
    maxp = request.GET.get("max", "")
    available = request.GET.get("available")

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(fabric__icontains=q) | Q(description__icontains=q))
    if category:
        qs = qs.filter(category=category)
    if fabric:
        qs = qs.filter(fabric__iexact=fabric)
    if colour:
        qs = qs.filter(colour__iexact=colour)
    try:
        if minp:
            qs = qs.filter(price__gte=Decimal(minp))
        if maxp:
            qs = qs.filter(price__lte=Decimal(maxp))
    except (TypeError, ValueError, ArithmeticError):
        pass
    if available:
        qs = qs.filter(stock__gt=0)

    ordering = {
        "price_asc": "price", "price_desc": "-price", "name": "name",
        "popular": "-avg_rating", "newest": "-created_at",
    }.get(sort, "-created_at")
    qs = qs.order_by(ordering, "name").distinct()

    fabrics = Product.objects.filter(active=True).values_list("fabric", flat=True).distinct().order_by("fabric")
    colours = Product.objects.filter(active=True).values_list("colour", flat=True).distinct().order_by("colour")
    return render(request, "customer/catalog.html", {
        "products": qs, "q": q, "category": category, "categories": [(c.slug, c.name) for c in Category.objects.filter(active=True).order_by("sort_order", "name")],
        "fabrics": fabrics, "colours": colours, "sort": sort,
        "minp": minp, "maxp": maxp, "available": available,
    })


@customer_only
def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("weaver").prefetch_related("gallery", "reviews__customer", "trace_steps"),
        pk=pk, active=True,
    )
    reviews = product.reviews.filter(approved=True).order_by("-created_at")
    average = reviews.aggregate(value=Avg("rating"))["value"] or 0
    return render(request, "customer/product_detail.html", {
        "product": product,
        "related": Product.objects.filter(active=True, category=product.category).exclude(pk=product.pk)[:4],
        "reviews": reviews,
        "review_form": ReviewForm(),
        "avg_rating": average,
    })


@customer_only
@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    try:
        quantity = max(1, int(request.POST.get("quantity", 1)))
    except (TypeError, ValueError):
        quantity = 1

    if product.stock < 1:
        messages.error(request, "This saree is currently out of stock.")
        return redirect(request.POST.get("next") or "cart")

    cart = _cart(request)
    current = int(cart.get(str(pk), 0) or 0)
    new_quantity = min(current + quantity, product.stock)
    cart[str(pk)] = new_quantity
    request.session["cart"] = cart
    request.session.modified = True
    if new_quantity < current + quantity:
        messages.info(request, f"Only {product.stock} piece(s) are available.")
    else:
        messages.success(request, f"{product.name} added · {new_quantity} piece(s) in cart.")
    return redirect(request.POST.get("next") or "cart")


@customer_only
@require_POST
def update_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1
    cart = _cart(request)
    if quantity <= 0 or product.stock < 1:
        cart.pop(str(pk), None)
        messages.info(request, "Item removed from cart.")
    else:
        cart[str(pk)] = min(quantity, product.stock)
        messages.success(request, "Cart quantity updated.")
    request.session["cart"] = cart
    request.session.modified = True
    return redirect("cart")


@customer_only
@require_POST
def remove_from_cart(request, pk):
    cart = _cart(request)
    cart.pop(str(pk), None)
    request.session["cart"] = cart
    request.session.modified = True
    messages.info(request, "Item removed from cart.")
    return redirect("cart")


@customer_only
def cart(request):
    items, total = cart_data(request)
    return render(request, "customer/cart.html", {"items": items, "total": total})


@customer_only
@require_POST
def toggle_wishlist(request, pk):
    customer = _customer(request)
    product = get_object_or_404(Product, pk=pk, active=True)
    existing = Wishlist.objects.filter(customer=customer, product=product).first()
    if existing:
        existing.delete()
        added = False
    else:
        Wishlist.objects.create(customer=customer, product=product)
        added = True
    return JsonResponse({"added": added, "message": "Added to wishlist." if added else "Removed from wishlist."})


@customer_only
def wishlist(request):
    customer = _customer(request)
    return render(request, "customer/wishlist.html", {
        "items": Wishlist.objects.filter(customer=customer).select_related("product")
    })


@customer_only
@require_POST
def apply_coupon(request):
    customer = _customer(request)
    _, subtotal = cart_data(request)
    code = request.POST.get("code", "").strip().upper()
    coupon = Coupon.objects.filter(code=code, active=True).first()
    valid, discount, error = _coupon_valid(coupon, subtotal, customer=customer)
    if not valid:
        request.session.pop("coupon_code", None)
        return JsonResponse({"ok": False, "message": error}, status=400)
    request.session["coupon_code"] = coupon.code
    request.session.modified = True
    total = _money(subtotal - discount + SHIPPING_FLAT)
    return JsonResponse({
        "ok": True, "code": coupon.code, "discount": str(discount),
        "subtotal": str(subtotal), "total": str(total),
    })


@customer_only
def checkout(request):
    customer = _customer(request)
    items, cart_total = cart_data(request)
    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect("catalog")

    default = customer.addresses.filter(is_default=True).first()
    initial = {
        "name": default.name if default else customer.name,
        "phone": default.phone if default else customer.phone,
        "address": default.address if default else customer.address,
        "city": default.city if default else "Bengaluru",
        "state": default.state if default else "Karnataka",
        "pincode": default.pincode if default else "",
        "coupon": request.session.get("coupon_code", ""),
        "payment": "demo",
    }
    form = CustomerCheckoutForm(request.POST or None, initial=initial)

    coupon_code = request.session.get("coupon_code", "")
    coupon = Coupon.objects.filter(code=coupon_code, active=True).first() if coupon_code else None
    valid, discount, _ = _coupon_valid(coupon, cart_total, customer=customer) if coupon else (True, Decimal("0.00"), "")
    if not valid:
        coupon = None
        request.session.pop("coupon_code", None)
        discount = Decimal("0.00")
    subtotal, discount, shipping, tax, total = _checkout_totals(cart_total, coupon, customer)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        requested_coupon = data.get("coupon", "").strip().upper()

        try:
            with transaction.atomic():
                # Re-read and lock every product before calculating the final order amount.
                locked_lines = []
                subtotal = Decimal("0.00")
                for line in items:
                    product = Product.objects.select_for_update().get(pk=line["product"].pk)
                    quantity = min(int(line["quantity"]), product.stock)
                    if quantity < 1:
                        raise ValueError(f"{product.name} is no longer available.")
                    line_total = _money(product.price * quantity)
                    locked_lines.append((product, quantity, product.price, line_total))
                    subtotal += line_total
                subtotal = _money(subtotal)

                coupon = None
                discount = Decimal("0.00")
                if requested_coupon:
                    coupon = Coupon.objects.select_for_update().filter(code=requested_coupon, active=True).first()
                    valid, discount, error = _coupon_valid(coupon, subtotal, customer=customer)
                    if not valid:
                        raise ValueError(error)
                shipping = SHIPPING_FLAT
                tax = _money((subtotal - discount) * TAX_RATE / Decimal("100"))
                total = _money(subtotal - discount + shipping + tax)

                customer.name = data["name"]
                customer.phone = data["phone"]
                customer.address = data["address"]
                customer.save(update_fields=["name", "phone", "address"])
                Address.objects.filter(customer=customer).update(is_default=False)
                Address.objects.create(
                    customer=customer, label="Checkout", name=data["name"], phone=data["phone"],
                    address=data["address"], city=data["city"], state=data["state"],
                    pincode=data["pincode"], is_default=True,
                )

                order = Order.objects.create(
                    customer=customer, status="placed", subtotal=subtotal, discount=discount,
                    shipping=shipping, tax=tax, total=total, coupon=coupon,
                    shipping_name=data["name"], shipping_phone=data["phone"],
                    shipping_address=f"{data['address']}\n{data['city']}, {data['state']} - {data['pincode']}",
                    notes=data["notes"],
                )

                for product, quantity, unit_price, line_total in locked_lines:
                    OrderItem.objects.create(
                        order=order, product=product, product_name=product.name,
                        quantity=quantity, price=unit_price,
                    )
                    product.stock -= quantity
                    product.save(update_fields=["stock", "updated_at"])
                    InventoryTransaction.objects.create(
                        product=product, kind="sale", quantity=-quantity,
                        reference=str(order), created_by=request.user,
                    )

                OrderStatusHistory.objects.create(order=order, status="placed", changed_by=request.user, note="Order created")
                payment_method = data["payment"]
                Payment.objects.create(
                    order=order, method=payment_method,
                    status="paid" if payment_method == "demo" else "pending",
                    transaction_id=f"DEMO-{uuid.uuid4().hex[:14].upper()}" if payment_method == "demo" else None,
                    amount=total, paid_at=timezone.now() if payment_method == "demo" else None,
                )
                if coupon:
                    Coupon.objects.filter(pk=coupon.pk).update(used_count=F("used_count") + 1)
                    CouponUsage.objects.create(coupon=coupon, customer=customer, order=order)
                Notification.objects.create(
                    customer=customer, title="Order received",
                    message=f"{order} has been placed successfully.",
                    url=reverse("order_detail", kwargs={"pk": order.pk}),
                )

            request.session["cart"] = {}
            request.session.pop("coupon_code", None)
            request.session.modified = True
            return redirect("order_detail", pk=order.pk)
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("cart")

    return render(request, "customer/checkout.html", {
        "form": form, "items": items, "subtotal": subtotal, "discount": discount,
        "shipping": shipping, "tax": tax, "total": total, "coupon": coupon,
    })


def _owns(request, order):
    return bool(
        request.user.is_authenticated
        and (request.user.is_staff or (getattr(request.user, "customer_profile", None) and order.customer.user_id == request.user.id))
    )


@customer_only
def my_orders(request):
    customer = _customer(request)
    return render(request, "customer/my_orders.html", {
        "orders": customer.orders.prefetch_related("items", "payment").order_by("-created_at")
    })


@customer_only
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items", "status_history", "payment"), pk=pk)
    if not _owns(request, order):
        return redirect("login")
    return render(request, "customer/order_detail.html", {"order": order})


@customer_only
@require_POST
def cancel_order(request, pk):
    customer = _customer(request)
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk, customer=customer)
        if order.status not in {"placed", "confirmed"}:
            messages.error(request, "This order can no longer be cancelled.")
            return redirect("order_detail", pk=pk)
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=order, status="cancelled", changed_by=request.user, note="Cancelled by customer")
        for item in order.items.select_related("product"):
            product = Product.objects.select_for_update().get(pk=item.product_id)
            product.stock += item.quantity
            product.save(update_fields=["stock", "updated_at"])
            InventoryTransaction.objects.create(
                product=product, kind="cancel", quantity=item.quantity,
                reference=str(order), created_by=request.user,
            )
        if hasattr(order, "payment") and order.payment.status == "paid":
            order.payment.status = "refunded"
            order.payment.save(update_fields=["status"])
        Notification.objects.create(
            customer=customer, title="Order cancelled",
            message=f"{order} was cancelled and stock was restored.", url=reverse("order_detail", kwargs={"pk": order.pk}),
        )
    messages.success(request, "Order cancelled and inventory restored.")
    return redirect("order_detail", pk=pk)


@customer_only
@require_POST
def review_create(request, pk):
    customer = _customer(request)
    product = get_object_or_404(Product, pk=pk, active=True)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please enter a valid review.")
    elif not OrderItem.objects.filter(order__customer=customer, product=product, order__status="delivered").exists():
        messages.error(request, "Reviews are available after delivery.")
    elif Review.objects.filter(product=product, customer=customer).exists():
        messages.error(request, "You have already reviewed this saree.")
    else:
        obj = form.save(commit=False)
        obj.product = product
        obj.customer = customer
        obj.order_item = OrderItem.objects.filter(order__customer=customer, product=product, order__status="delivered").first()
        obj.save()
        messages.success(request, "Thank you for your review.")
    return redirect("product_detail", pk=pk)


@admin_only
def admin_dashboard(request):
    orders = Order.objects.select_related("customer", "payment").order_by("-created_at")
    today = timezone.localdate()
    month_start = today.replace(day=1)
    revenue = Order.objects.exclude(status="cancelled").aggregate(value=Sum("total"))["value"] or Decimal("0")
    month_revenue = Order.objects.filter(created_at__date__gte=month_start).exclude(status="cancelled").aggregate(value=Sum("total"))["value"] or Decimal("0")
    daily = list(
        Order.objects.filter(created_at__date__gte=today).exclude(status="cancelled")
        .values("created_at__date").annotate(total=Sum("total")).order_by("created_at__date")
    )
    best = list(
        OrderItem.objects.filter(order__status__in=["placed", "confirmed", "weaving", "packed", "shipped", "delivered"])
        .values("product_name").annotate(units=Sum("quantity")).order_by("-units")[:6]
    )
    return render(request, "admin/dashboard.html", {
        "product_count": Product.objects.count(),
        "stock": Product.objects.aggregate(value=Sum("stock"))["value"] or 0,
        "customers": Customer.objects.count(),
        "pending": Order.objects.exclude(status__in=["delivered", "cancelled"]).count(),
        "revenue": revenue, "month_revenue": month_revenue,
        "recent": orders[:10],
        "low": Product.objects.filter(active=True, stock__lte=F("low_stock_threshold")).order_by("stock")[:8],
        "daily_json": json.dumps([{"date": str(x["created_at__date"]), "total": float(x["total"])} for x in daily]),
        "best_json": json.dumps(best),
    })


@admin_only
def admin_products(request):
    q = request.GET.get("q", "").strip()
    products = Product.objects.select_related("weaver").all().order_by("-featured", "name")
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(fabric__icontains=q))
    return render(request, "admin/products.html", {"products": products, "q": q})


@admin_only
def admin_product_add(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        if product.stock:
            InventoryTransaction.objects.create(product=product, kind="opening", quantity=product.stock, created_by=request.user)
        messages.success(request, "Saree added to the catalogue.")
        return redirect("admin_products")
    return render(request, "admin/product_form.html", {"form": form, "title": "Add saree", "button": "Add to catalogue"})


@admin_only
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    old_stock = product.stock
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        delta = product.stock - old_stock
        if delta:
            InventoryTransaction.objects.create(product=product, kind="adjust", quantity=delta, reference="Manual edit", created_by=request.user)
        messages.success(request, "Catalogue item updated.")
        return redirect("admin_products")
    return render(request, "admin/product_form.html", {"form": form, "title": "Edit saree", "button": "Save changes"})


@admin_only
@require_POST
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.active = False
    product.save(update_fields=["active", "updated_at"])
    messages.success(request, "Product hidden from the customer catalogue.")
    return redirect("admin_products")


@admin_only
def admin_orders(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    orders = Order.objects.select_related("customer", "payment").prefetch_related("items").order_by("-created_at")
    if q:
        orders = orders.filter(Q(shipping_name__icontains=q) | Q(customer__name__icontains=q) | Q(id__icontains=q))
    if status:
        orders = orders.filter(status=status)
    return render(request, "admin/orders.html", {
        "orders": orders, "statuses": Order.STATUS, "q": q, "selected_status": status,
    })


@admin_only
@require_POST
def admin_order_status(request, pk):
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
        new_status = request.POST.get("status")
        valid_statuses = dict(Order.STATUS)
        if new_status not in valid_statuses:
            messages.error(request, "Invalid order status.")
            return redirect("admin_orders")
        if order.status in {"cancelled", "delivered"} and new_status != order.status:
            messages.error(request, "A cancelled or delivered order cannot be moved backwards.")
            return redirect("admin_orders")
        if new_status == order.status:
            messages.info(request, f"{order} is already {order.get_status_display()}.")
            return redirect("admin_orders")

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=order, status=new_status, changed_by=request.user, note=request.POST.get("note", ""))

        if new_status == "cancelled":
            for item in order.items.select_related("product"):
                product = Product.objects.select_for_update().get(pk=item.product_id)
                product.stock += item.quantity
                product.save(update_fields=["stock", "updated_at"])
                InventoryTransaction.objects.create(product=product, kind="cancel", quantity=item.quantity, reference=str(order), created_by=request.user)
            if hasattr(order, "payment") and order.payment.status == "paid":
                order.payment.status = "refunded"
                order.payment.save(update_fields=["status"])

        Notification.objects.create(
            customer=order.customer, title=f"Order {new_status}",
            message=f"Your {order} status is now {order.get_status_display()}.",
            url=reverse("order_detail", kwargs={"pk": order.pk}),
        )
    messages.success(request, f"{order} updated.")
    return redirect("admin_orders")


@admin_only
def admin_inventory(request):
    products = Product.objects.all().order_by("stock", "name")
    transactions = InventoryTransaction.objects.select_related("product").order_by("-created_at")[:40]
    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = 0
        product = get_object_or_404(Product, pk=request.POST.get("product"))
        new_stock = max(0, product.stock + quantity)
        actual_delta = new_stock - product.stock
        product.stock = new_stock
        product.save(update_fields=["stock", "updated_at"])
        if actual_delta:
            InventoryTransaction.objects.create(
                product=product, kind="receive" if actual_delta > 0 else "adjust",
                quantity=actual_delta, note=request.POST.get("note", ""), created_by=request.user,
            )
        messages.success(request, "Inventory updated.")
        return redirect("admin_inventory")
    return render(request, "admin/inventory.html", {"products": products, "transactions": transactions})


@admin_only
def admin_coupons(request):
    form = CouponForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Coupon saved.")
        return redirect("admin_coupons")
    return render(request, "admin/coupons.html", {"coupons": Coupon.objects.all().order_by("-id"), "form": form})


@admin_only
def admin_categories(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Saree category created.")
        return redirect("admin_categories")
    categories = Category.objects.all().order_by("sort_order", "name")
    return render(request, "admin/categories.html", {"form": form, "categories": categories})


@admin_only
@require_POST
def admin_category_toggle(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.active = not category.active
    category.save(update_fields=["active"])
    messages.success(request, f"{category.name} is now {'available' if category.active else 'hidden'} in the product editor.")
    return redirect("admin_categories")


@admin_only
def admin_customers(request):
    q = request.GET.get("q", "").strip()
    customers = Customer.objects.select_related("user").all()
    if q:
        customers = customers.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(user__username__icontains=q))
    customers = list(customers.order_by("-created_at"))
    for customer in customers:
        customer.order_count = customer.orders.count()
        customer.total_spend = customer.orders.exclude(status="cancelled").aggregate(value=Sum("total"))["value"] or Decimal("0.00")
    return render(request, "admin/customers.html", {"customers": customers, "q": q})


@admin_only
def admin_customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerAdminForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        if customer.user:
            customer.user.email = customer.email
            customer.user.save(update_fields=["email"])
        messages.success(request, "Customer profile updated.")
        return redirect("admin_customers")
    return render(request, "admin/customer_form.html", {"form": form, "customer": customer})

@admin_only
def admin_weavers(request):
    if request.method == "POST":
        Weaver.objects.create(
            name=request.POST.get("name", "").strip(), location=request.POST.get("location", "").strip(),
            specialization=request.POST.get("specialization", "").strip(), years=max(1, int(request.POST.get("years", 1) or 1)),
            story=request.POST.get("story", "").strip(),
        )
        messages.success(request, "Weaver unit added.")
        return redirect("admin_weavers")
    return render(request, "admin/weavers.html", {"weavers": Weaver.objects.filter(active=True), "products": Product.objects.select_related("weaver")})


def receipt_pdf(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    if not _owns(request, order):
        return redirect("login")

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "PowerloomReceiptTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, textColor=colors.HexColor("#263126"), spaceAfter=5,
    )
    normal = ParagraphStyle("ReceiptNormal", parent=styles["Normal"], fontSize=9, leading=13)
    story = [
        Paragraph("POWERLOOM", title),
        Paragraph("Cotton Weavers · Order Receipt", normal), Spacer(1, 8),
        Paragraph(f"<b>Receipt:</b> {escape(str(order))}", normal),
        Paragraph(f"<b>Date:</b> {order.created_at.strftime('%d %b %Y, %I:%M %p')}", normal),
        Paragraph(f"<b>Customer:</b> {escape(order.shipping_name)}", normal),
        Paragraph(f"<b>Phone:</b> {escape(order.shipping_phone)}", normal),
        Paragraph(f"<b>Delivery:</b> {escape(order.shipping_address).replace(chr(10), '<br/>')}", normal),
        Spacer(1, 12),
    ]
    rows = [["Saree", "Qty", "Rate", "Amount"]]
    for item in order.items.all():
        rows.append([item.product_name, str(item.quantity), f"Rs. {item.price:,.2f}", f"Rs. {item.subtotal:,.2f}"])
    rows += [
        ["", "", "Subtotal", f"Rs. {order.subtotal:,.2f}"],
        ["", "", "Discount", f"- Rs. {order.discount:,.2f}"],
        ["", "", "Delivery", f"Rs. {order.shipping:,.2f}"],
        ["", "", "TOTAL", f"Rs. {order.total:,.2f}"],
    ]
    table = Table(rows, colWidths=[80 * mm, 20 * mm, 32 * mm, 38 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263126")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9d8d0")),
        ("PADDING", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (-2, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story += [table, Spacer(1, 18), Paragraph("Thank you for supporting local weaving and craftsmanship.", normal)]
    document.build(story)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Powerloom_{order}.pdf"'
    return response
