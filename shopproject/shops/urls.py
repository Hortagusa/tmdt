from django.urls import path
from . import views

app_name = 'shops'

urlpatterns = [
    path('', views.index, name='index'),
    # products
    path('products/', views.product_list, name='product_list'),
    path('products/all/', views.all_shops, name='all_shops'),
    path('products/<int:id>/', views.product_detail, name='product_detail'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:id>/edit/', views.product_update, name='product_update'),
    path('products/<int:id>/delete/', views.product_delete, name='product_delete'),
    path("comment/delete/<int:id>/", views.comment_delete, name="comment_delete"),
    path("comment/edit/<int:id>/", views.comment_edit, name="comment_edit"),
    # category
    path('category/add/', views.category_create, name='category_create'),
    # cart
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    #checkout
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('invoice/<int:order_id>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('payment/qr/<int:order_id>/', views.payment_qr, name='payment_qr'),
    path('payment/webhook/bank/', views.bank_payment_webhook, name='bank_payment_webhook'),
    #status
    path('orders/', views.order_list, name='order_list'),
    # order detail của user
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    # order detail của admin
    path('admin/orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin/orders/<int:order_id>/update/', views.update_order_status, name='update_order_status'),
    path('order/<int:order_id>/delete/', views.delete_order, name='delete_order'),
    #thống kê
    path('dashboard/', views.dashboard, name='dashboard'),
    #lịch sử order
    path('orders/history/', views.order_history, name='order_history'),
    #hủy đơn hàng
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
]

