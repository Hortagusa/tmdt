from django.contrib import admin

from .models import Product, Category, Order, OrderItem

# Register your models here.
admin.site.register(Product)
admin.site.register(Category)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_price', 'payment_method', 'payment_status', 'status', 'created']
    inlines = [OrderItemInline]

