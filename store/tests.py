from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Product, Customer, Order, OrderItem


class CommerceTests(TestCase):
    def setUp(self):
        u = User.objects.create_user('customer', password='customer12345')
        self.c = Customer.objects.create(user=u, name='Test', phone='9999999999', email='a@b.com')
        self.p = Product.objects.create(name='Test Saree', sku='TEST-001', price=Decimal('1500.00'), stock=20)
        self.client = Client()
        self.client.login(username='customer', password='customer12345')

    def test_order_item_subtotal_multiplies_quantity(self):
        o = Order.objects.create(customer=self.c, shipping_name='Test', shipping_phone='9', shipping_address='A', total=0)
        i = OrderItem.objects.create(order=o, product=self.p, product_name=self.p.name, quantity=10, price=self.p.price)
        self.assertEqual(i.subtotal, Decimal('15000.00'))

    def test_cart_total_multiplies_quantity(self):
        s = self.client.session
        s['cart'] = {str(self.p.id): 10}
        s.save()
        r = self.client.get('/cart/')
        self.assertContains(r, '15000.00')

    def test_customer_cannot_open_admin_workspace(self):
        r = self.client.get('/admin-dashboard/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/catalog/', r.url)

    def test_customer_cannot_open_product_management(self):
        r = self.client.get('/admin/products/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/catalog/', r.url)

    def test_admin_cannot_use_customer_cart(self):
        User.objects.create_user('admin', password='admin12345', is_staff=True)
        self.client.logout()
        self.client.login(username='admin', password='admin12345')
        r = self.client.get('/cart/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin-dashboard/', r.url)
