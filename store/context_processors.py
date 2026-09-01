def cart_context(request):
 cart=request.session.get('cart',{}) or {}
 try: count=sum(max(0,int(v)) for v in cart.values())
 except (TypeError,ValueError): count=0
 customer=getattr(request.user,'customer_profile',None) if request.user.is_authenticated else None
 unread=customer.notifications.filter(read=False).count() if customer else 0
 return {'cart_count':count,'unread_notifications':unread}
