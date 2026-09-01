from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator,MaxValueValidator

class Category(models.Model):
 name=models.CharField(max_length=80,unique=True)
 slug=models.SlugField(max_length=80,unique=True)
 description=models.CharField(max_length=240,blank=True)
 active=models.BooleanField(default=True)
 sort_order=models.PositiveIntegerField(default=0)
 created_at=models.DateTimeField(auto_now_add=True)
 def __str__(self): return self.name


class Weaver(models.Model):
 name=models.CharField(max_length=160); location=models.CharField(max_length=120); specialization=models.CharField(max_length=200,blank=True)
 years=models.PositiveIntegerField(default=1); story=models.TextField(blank=True); active=models.BooleanField(default=True)
 def __str__(self): return self.name

class Product(models.Model):
 CATEGORY=[('cotton','Cotton Saree'),('silk','Silk Saree'),('handloom','Handloom'),('printed','Printed'),('festive','Festive')]
 name=models.CharField(max_length=160); sku=models.CharField(max_length=50,unique=True); category=models.CharField(max_length=80,default='cotton',db_index=True)
 description=models.TextField(blank=True); fabric=models.CharField(max_length=80,default='Cotton'); size=models.CharField(max_length=80,default='6.3 m × 1.15 m')
 price=models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(Decimal('0'))]); compare_at_price=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
 stock=models.PositiveIntegerField(default=0); low_stock_threshold=models.PositiveIntegerField(default=5); unit=models.CharField(max_length=30,default='piece')
 image=models.ImageField(upload_to='products/',blank=True,null=True); featured=models.BooleanField(default=False); active=models.BooleanField(default=True)
 colour=models.CharField(max_length=60,default='Natural',blank=True); pattern=models.CharField(max_length=80,default='Traditional',blank=True); origin=models.CharField(max_length=120,default='Karnataka',blank=True)
 weaver=models.ForeignKey(Weaver,on_delete=models.SET_NULL,null=True,blank=True,related_name='products')
 created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
 class Meta: indexes=[models.Index(fields=['category','active']),models.Index(fields=['featured','active']),models.Index(fields=['stock'])]
 def __str__(self): return f'{self.name} ({self.sku})'
 def get_category_display(self):
  built_in=dict(self.CATEGORY)
  return built_in.get(self.category, self.category.replace('-', ' ').title())
 @property
 def discount_percent(self):
  if self.compare_at_price and self.compare_at_price>self.price: return int((1-self.price/self.compare_at_price)*100)
  return 0
 @property
 def available(self): return self.active and self.stock>0

class ProductImage(models.Model):
 product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='gallery'); image=models.ImageField(upload_to='products/gallery/'); alt=models.CharField(max_length=180,blank=True); sort_order=models.PositiveIntegerField(default=0)
 class Meta: ordering=['sort_order','id']

class Customer(models.Model):
 ROLE=[('customer','Customer'),('inventory','Inventory Manager'),('orders','Order Manager'),('admin','Administrator')]
 user=models.OneToOneField(User,on_delete=models.SET_NULL,null=True,blank=True,related_name='customer_profile'); name=models.CharField(max_length=120); phone=models.CharField(max_length=30); email=models.EmailField(blank=True)
 address=models.TextField(blank=True); role=models.CharField(max_length=20,choices=ROLE,default='customer'); created_at=models.DateTimeField(auto_now_add=True)
 def __str__(self): return self.name

class Address(models.Model):
 customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name='addresses'); label=models.CharField(max_length=40,default='Home'); name=models.CharField(max_length=120); phone=models.CharField(max_length=30); address=models.TextField(); city=models.CharField(max_length=80,default='Bengaluru'); state=models.CharField(max_length=80,default='Karnataka'); pincode=models.CharField(max_length=12); is_default=models.BooleanField(default=False)
 def __str__(self): return f'{self.label} · {self.customer.name}'

class Wishlist(models.Model):
 customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name='wishlist'); product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='wishlisted_by'); created_at=models.DateTimeField(auto_now_add=True)
 class Meta: constraints=[models.UniqueConstraint(fields=['customer','product'],name='unique_wishlist_item')]

class Coupon(models.Model):
 KIND=[('percent','Percentage'),('fixed','Fixed amount')]
 code=models.CharField(max_length=40,unique=True); kind=models.CharField(max_length=10,choices=KIND,default='percent'); value=models.DecimalField(max_digits=10,decimal_places=2); minimum_order=models.DecimalField(max_digits=10,decimal_places=2,default=0); maximum_discount=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True); usage_limit=models.PositiveIntegerField(null=True,blank=True); used_count=models.PositiveIntegerField(default=0); active=models.BooleanField(default=True); starts_at=models.DateTimeField(null=True,blank=True); expires_at=models.DateTimeField(null=True,blank=True)
 def __str__(self): return self.code

class Order(models.Model):
 STATUS=[('placed','Order Placed'),('confirmed','Confirmed'),('weaving','Preparing / Weaving'),('packed','Packed'),('shipped','Shipped'),('delivered','Delivered'),('cancelled','Cancelled')]
 customer=models.ForeignKey(Customer,on_delete=models.PROTECT,related_name='orders'); status=models.CharField(max_length=20,choices=STATUS,default='placed')
 subtotal=models.DecimalField(max_digits=12,decimal_places=2,default=0); discount=models.DecimalField(max_digits=12,decimal_places=2,default=0); shipping=models.DecimalField(max_digits=12,decimal_places=2,default=0); tax=models.DecimalField(max_digits=12,decimal_places=2,default=0); total=models.DecimalField(max_digits=12,decimal_places=2,default=0)
 coupon=models.ForeignKey(Coupon,on_delete=models.SET_NULL,null=True,blank=True,related_name='orders'); shipping_name=models.CharField(max_length=120); shipping_phone=models.CharField(max_length=30); shipping_address=models.TextField(); notes=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
 def __str__(self): return f'PL-{self.id:05d}'
 @property
 def paid(self): return hasattr(self,'payment') and self.payment.status=='paid'

class OrderItem(models.Model):
 order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items'); product=models.ForeignKey(Product,on_delete=models.PROTECT); product_name=models.CharField(max_length=160); quantity=models.PositiveIntegerField(); price=models.DecimalField(max_digits=10,decimal_places=2)
 @property
 def subtotal(self): return self.quantity*self.price

class OrderStatusHistory(models.Model):
 order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='status_history'); status=models.CharField(max_length=20,choices=Order.STATUS); note=models.CharField(max_length=250,blank=True); changed_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
 class Meta: ordering=['created_at']

class InventoryTransaction(models.Model):
 TYPE=[('opening','Opening stock'),('receive','Stock received'),('sale','Sale'),('cancel','Cancellation/return'),('adjust','Manual adjustment')]
 product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='inventory_transactions'); kind=models.CharField(max_length=12,choices=TYPE); quantity=models.IntegerField(); reference=models.CharField(max_length=100,blank=True); note=models.CharField(max_length=250,blank=True); created_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
 class Meta: ordering=['-created_at']

class Payment(models.Model):
 STATUS=[('pending','Pending'),('paid','Paid'),('failed','Failed'),('refunded','Refunded')]
 METHOD=[('demo','Demo Payment'),('cod','Cash on Delivery')]
 order=models.OneToOneField(Order,on_delete=models.CASCADE,related_name='payment'); method=models.CharField(max_length=10,choices=METHOD,default='demo'); status=models.CharField(max_length=10,choices=STATUS,default='pending'); transaction_id=models.CharField(max_length=100,unique=True,null=True,blank=True); amount=models.DecimalField(max_digits=12,decimal_places=2,default=0); created_at=models.DateTimeField(auto_now_add=True); paid_at=models.DateTimeField(null=True,blank=True)

class Review(models.Model):
 product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='reviews'); customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name='reviews'); order_item=models.ForeignKey(OrderItem,on_delete=models.SET_NULL,null=True,blank=True); rating=models.PositiveSmallIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)]); title=models.CharField(max_length=120,blank=True); body=models.TextField(); approved=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)
 class Meta: constraints=[models.UniqueConstraint(fields=['product','customer'],name='one_review_per_customer_product')]

class ProductTraceability(models.Model):
 product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='trace_steps'); step=models.PositiveIntegerField(); title=models.CharField(max_length=100); description=models.CharField(max_length=300); completed=models.BooleanField(default=True)
 class Meta: ordering=['step']

class Notification(models.Model):
 customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name='notifications'); title=models.CharField(max_length=160); message=models.CharField(max_length=400); url=models.CharField(max_length=240,blank=True); read=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True)
 class Meta: ordering=['-created_at']

class CouponUsage(models.Model):
 coupon=models.ForeignKey(Coupon,on_delete=models.CASCADE,related_name='usages'); customer=models.ForeignKey(Customer,on_delete=models.CASCADE); order=models.OneToOneField(Order,on_delete=models.CASCADE); used_at=models.DateTimeField(auto_now_add=True)
