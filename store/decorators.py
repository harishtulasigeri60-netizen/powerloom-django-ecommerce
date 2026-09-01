from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_only(view):
 @wraps(view)
 def w(request,*a,**k):
  if not request.user.is_authenticated:
   return redirect('/login/?role=admin&next='+request.path)
  if not request.user.is_staff:
   messages.error(request,'Admin access only. Your customer account cannot manage the workshop.')
   return redirect('/catalog/')
  return view(request,*a,**k)
 return w


def customer_only(view):
 @wraps(view)
 def w(request,*a,**k):
  if not request.user.is_authenticated:
   return redirect('/login/?role=customer&next='+request.path)
  if request.user.is_staff:
   messages.info(request,'Customer shopping is unavailable for admin accounts. Use the Workshop controls instead.')
   return redirect('/admin-dashboard/')
  return view(request,*a,**k)
 return w
