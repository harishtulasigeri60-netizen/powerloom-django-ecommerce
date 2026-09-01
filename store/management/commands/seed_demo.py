from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from store.models import Category, Coupon, Customer, Product, ProductTraceability, Weaver


class Command(BaseCommand):
    help = "Seed polished Powerloom presentation data and demo accounts."

    def handle(self, *args, **options):
        category_data = [
            ("Cotton Saree", "cotton", "Lightweight everyday and heritage cotton weaves."),
            ("Silk Saree", "silk", "Festive silk and silk-blend collections."),
            ("Handloom", "handloom", "Hand-finished weaves with visible craft character."),
            ("Printed", "printed", "Pattern-led everyday Powerloom sarees."),
            ("Festive", "festive", "Celebration-ready sarees with richer borders and detailing."),
        ]
        for order, (name, slug, description) in enumerate(category_data, 1):
            Category.objects.update_or_create(
                slug=slug, defaults={"name": name, "description": description, "sort_order": order, "active": True}
            )
        weaver_data = [
            ("Sri Lakshmi Powerloom", "Ilkal, Karnataka", "Cotton sarees & traditional borders", 18),
            ("Mahalakshmi Weaves", "Hubballi, Karnataka", "Festive silk-inspired weaves", 24),
            ("Kaveri Loom House", "Dharwad, Karnataka", "Printed everyday cottons", 12),
        ]
        weavers = []
        for name, location, specialization, years in weaver_data:
            weaver, _ = Weaver.objects.get_or_create(
                name=name,
                defaults={
                    "location": location,
                    "specialization": specialization,
                    "years": years,
                    "story": "A workshop built around careful weaving, finishing and local craft knowledge.",
                },
            )
            weavers.append(weaver)

        products = [
            ("Ilkal Heritage Green", "PL-GRN-001", "cotton", "Cotton", "Forest Green", "Checked", 1499, 220, weavers[0]),
            ("Mysuru Gold Thread", "PL-SLK-002", "silk", "Silk Blend", "Ivory Gold", "Temple Border", 3299, 85, weavers[1]),
            ("Karnataka Indigo Rhythm", "PL-HND-003", "handloom", "Handloom Cotton", "Indigo", "Woven Stripe", 1899, 64, weavers[0]),
            ("Rosewood Printed Drape", "PL-PRT-004", "printed", "Cotton", "Rose", "Floral Print", 1199, 140, weavers[2]),
            ("Festival Marigold", "PL-FST-005", "festive", "Silk Blend", "Marigold", "Zari Border", 2899, 42, weavers[1]),
            ("Terracotta Loom Classic", "PL-COT-006", "cotton", "Cotton", "Terracotta", "Checks", 1399, 9, weavers[2]),
        ]

        trace = [
            (1, "Yarn preparation", "Threads are selected and prepared for consistent tension."),
            (2, "Dyeing", "Colour is developed and checked before weaving."),
            (3, "Powerloom weaving", "The fabric is woven with controlled rhythm and alignment."),
            (4, "Quality check", "Borders, pallu and finishing are inspected."),
            (5, "Packaging", "The finished saree is folded and prepared for delivery."),
        ]

        for index, (name, sku, category, fabric, colour, pattern, price, stock, weaver) in enumerate(products, 1):
            product, _ = Product.objects.update_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": category,
                    "fabric": fabric,
                    "colour": colour,
                    "pattern": pattern,
                    "origin": "Karnataka",
                    "price": Decimal(str(price)),
                    "compare_at_price": Decimal(str(price * 12 // 10)),
                    "stock": stock,
                    "low_stock_threshold": 10,
                    "featured": index <= 3,
                    "active": True,
                    "weaver": weaver,
                    "image": f"products/demo-{index}.png",
                    "description": (
                        f"A thoughtfully finished {fabric.lower()} saree inspired by Karnataka craft traditions. "
                        "Designed for comfortable elegance and made to carry its woven story forward."
                    ),
                },
            )
            if not product.trace_steps.exists():
                ProductTraceability.objects.bulk_create([
                    ProductTraceability(product=product, step=step, title=title, description=description)
                    for step, title, description in trace
                ])

        Coupon.objects.get_or_create(
            code="POWER10",
            defaults={
                "kind": "percent", "value": Decimal("10"), "minimum_order": Decimal("2000"),
                "maximum_discount": Decimal("500"), "active": True,
            },
        )

        admin_user, created = User.objects.get_or_create(username="admin", defaults={"email": "admin@example.com"})
        if created:
            admin_user.set_password("admin12345")
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
        elif not admin_user.is_staff:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.set_password("admin12345")
            admin_user.save()

        customer_user, created = User.objects.get_or_create(username="customer", defaults={"email": "customer@example.com"})
        if created:
            customer_user.set_password("customer12345")
            customer_user.save()
        Customer.objects.get_or_create(
            user=customer_user,
            defaults={"name": "Demo Customer", "phone": "9999999999", "email": customer_user.email},
        )

        self.stdout.write(self.style.SUCCESS("Powerloom demo data ready."))
        self.stdout.write("Admin: admin / admin12345")
        self.stdout.write("Customer: customer / customer12345")
