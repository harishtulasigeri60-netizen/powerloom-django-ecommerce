from django import forms
from django.contrib.auth.models import User
from .models import Product,Address,Review,Coupon,Category,Customer
class ProductForm(forms.ModelForm):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  choices=[(c.slug,c.name) for c in Category.objects.filter(active=True).order_by('sort_order','name')]
  current=self.instance.category if self.instance and self.instance.pk else None
  if current and current not in dict(choices): choices.append((current,self.instance.get_category_display()))
  self.fields['category'].choices=choices
 class Meta:
  model=Product; fields=['name','sku','category','fabric','colour','pattern','origin','weaver','size','description','price','compare_at_price','stock','low_stock_threshold','unit','image','featured','active']; widgets={'description':forms.Textarea(attrs={'rows':4})}
class CustomerCheckoutForm(forms.Form):
 name=forms.CharField(max_length=120); phone=forms.CharField(max_length=30); address=forms.CharField(widget=forms.Textarea(attrs={'rows':4})); city=forms.CharField(max_length=80,initial='Bengaluru'); state=forms.CharField(max_length=80,initial='Karnataka'); pincode=forms.CharField(max_length=12); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={'rows':3})); coupon=forms.CharField(required=False,max_length=40); payment=forms.ChoiceField(choices=[('demo','Demo Payment'),('cod','Cash on Delivery')],initial='demo')
class CustomerRegisterForm(forms.Form):
 username=forms.CharField(max_length=80); password=forms.CharField(min_length=8,widget=forms.PasswordInput); name=forms.CharField(max_length=120); phone=forms.CharField(max_length=30); email=forms.EmailField(required=False); address=forms.CharField(required=False,widget=forms.Textarea(attrs={'rows':3}))
 def clean_username(self):
  u=self.cleaned_data['username']
  if User.objects.filter(username=u).exists(): raise forms.ValidationError('Username already exists.')
  return u
class AddressForm(forms.ModelForm):
 class Meta: model=Address; fields=['label','name','phone','address','city','state','pincode','is_default']; widgets={'address':forms.Textarea(attrs={'rows':3})}
class ReviewForm(forms.ModelForm):
 class Meta: model=Review; fields=['rating','title','body']; widgets={'body':forms.Textarea(attrs={'rows':4})}
class CouponForm(forms.ModelForm):
 class Meta: model=Coupon; fields=['code','kind','value','minimum_order','maximum_discount','usage_limit','starts_at','expires_at','active']; widgets={'starts_at':forms.DateTimeInput(attrs={'type':'datetime-local'}),'expires_at':forms.DateTimeInput(attrs={'type':'datetime-local'})}

class CategoryForm(forms.ModelForm):
 class Meta:
  model=Category; fields=['name','slug','description','sort_order','active']
  widgets={'description':forms.Textarea(attrs={'rows':3})}

class CustomerAdminForm(forms.ModelForm):
 class Meta:
  model=Customer; fields=['name','phone','email','address']
  widgets={'address':forms.Textarea(attrs={'rows':3})}
