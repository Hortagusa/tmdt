import os
import hmac
import re
from urllib.parse import urlencode
from django.conf import settings
from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import render
from django.contrib import messages
from django.utils.html import strip_tags

from .models import Product, Category, Cart, CartItem, Order, OrderItem
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .forms import ProductForm, CategoryForm, CheckoutForm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from django.http import HttpResponse
from io import BytesIO
from reportlab.platypus import Image
from django.utils.dateparse import parse_date
from django.utils import timezone
import json

def index(request):
    category_id = request.GET.get('category')

    products = Product.objects.filter(seller=request.user)
    categories = Category.objects.all()

    if category_id:
        products = products.filter(category_id=category_id)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': int(category_id) if category_id else None
    }

    return render(request, 'shops/index.html', context)

def all_shops(request):
    products = Product.objects.order_by('-created')[:6]
    return render(request, 'shops/product_list.html', {
        'products': products
    })


def product_list(request):
    category_id = request.GET.get('category')

    products = Product.objects.all().select_related('category', 'seller', 'seller__profile')
    categories = Category.objects.all()

    if category_id:
        products = products.filter(category_id=category_id)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': int(category_id) if category_id else None
    }
    return render(request, 'shops/product_list.html', context)

def get_or_create_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart

@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('shops:product_create')
    else:
        form = CategoryForm()

    return render(request, 'shops/category_form.html', {
        'form': form,
        'title': 'Add category'
    })

def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            return redirect('shops:product_list')
    else:
        form = ProductForm()

    return render(request, 'shops/product_form.html', {
        'form': form,
        'title': 'Add product'
    })

def product_detail(request, id):
    product = get_object_or_404(Product, id=id)

    return render(request, 'shops/shop_detail.html', {
        'product': product
    })

def product_delete(request, id):
    product = get_object_or_404(Product, id=id)

    if product.seller != request.user:
        return HttpResponseForbidden("Bạn không có quyền xoá sản phẩm này")

    if request.method == 'POST':
        product.delete()
        return redirect('shops:product_list')

    return render(request, 'shops/product_confirm_delete.html', {
        'product': product
    })

def product_update(request, id):
    product = get_object_or_404(Product, id=id)

    if product.seller != request.user:
        return HttpResponseForbidden("Bạn không có quyền sửa sản phẩm này")

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('shops:product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'shops/product_form.html', {
        'form': form,
        'title': 'Edit product'
    })

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request.user)

    if product.stock <= 0:
        messages.error(request, f"Sản phẩm '{product.name}' đã hết hàng.")
        return redirect(request.META.get('HTTP_REFERER', 'shops:product_list'))

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    # vượt stock
    if item.quantity >= product.stock:
        messages.error(request, f"Sản phẩm '{product.name}' chỉ còn {product.stock} sản phẩm trong kho!")
        return redirect(request.META.get('HTTP_REFERER', 'shops:product_list'))

    #  hợp lệ
    if not created:
        item.quantity += 1
    else:
        item.quantity = 1

    item.save()
    return redirect(request.META.get('HTTP_REFERER', 'shops:product_list'))

@login_required
def cart_detail(request):
    cart = get_or_create_cart(request.user)
    items = CartItem.objects.filter(cart=cart)
    total = sum(item.total_price for item in items)
    total_quantity = sum(item.quantity for item in items)
    return render(request, 'shops/cart.html', {
        'cart': cart,
        'items': items,
        'total': total,
        'total_quantity': total_quantity,
    })

@login_required
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    try:
        qty = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        qty = 1

    if qty < 1:
        qty = 1

    if qty > item.product.stock:
        qty = item.product.stock
        messages.warning(
            request,
            f"Sản phẩm '{item.product.name}' chỉ còn {item.product.stock} trong kho."
        )

    if qty < 1:
        item.delete()
        messages.error(request, f"Sản phẩm '{item.product.name}' đã hết hàng.")
        return redirect('shops:cart_detail')

    item.quantity = qty
    item.save()
    return redirect('shops:cart_detail')

@login_required
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect('shops:cart_detail')

@login_required
def order_history(request):
    month_raw = request.GET.get('month')
    year_raw = request.GET.get('year')
    start_date_raw = request.GET.get('start_date')
    end_date_raw = request.GET.get('end_date')
    has_filter = any([month_raw, year_raw, start_date_raw, end_date_raw])

    month = None
    year = None
    try:
        month = int(month_raw) if month_raw else None
    except (TypeError, ValueError):
        month = None
    try:
        year = int(year_raw) if year_raw else None
    except (TypeError, ValueError):
        year = None

    start_date = parse_date(start_date_raw) if start_date_raw else None
    end_date = parse_date(end_date_raw) if end_date_raw else None

    orders = Order.objects.filter(user=request.user)

    # Khi dùng khoảng ngày thì ưu tiên khoảng ngày, bỏ month/year.
    if start_date or end_date:
        month = None
        year = None

    if has_filter:
        if year:
            orders = orders.filter(created__year=year)
        if month:
            orders = orders.filter(created__month=month)
        if start_date and end_date:
            orders = orders.filter(created__date__range=(start_date, end_date))
        elif start_date:
            orders = orders.filter(created__date__gte=start_date)
        elif end_date:
            orders = orders.filter(created__date__lte=end_date)
    else:
        # Mặc định chỉ hiển thị đơn trong 7 ngày gần nhất.
        seven_days_ago = timezone.now().date() - timedelta(days=7)
        orders = orders.filter(created__date__gte=seven_days_ago)

    orders = orders.order_by('-created')

    current_year = timezone.now().year
    context = {
        'orders': orders,
        'months': list(range(1, 13)),
        'years': list(range(current_year - 5, current_year + 1)),
        'month': month,
        'year': year,
        'start_date': start_date,
        'end_date': end_date,
        'has_filter': has_filter,
    }
    return render(request, 'shops/order_history.html', context)

@login_required
def checkout(request):
    cart = get_or_create_cart(request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related("product")
    total = sum(item.total_price for item in cart_items)

    if not cart_items.exists():
        messages.error(request, "Giỏ hàng trống!")
        return redirect('shops:cart_detail')

    if request.method == "GET":
        form = CheckoutForm()
        return render(request, "shops/checkout.html", {
            "items": cart_items,
            "form": form,
            "total": total,
        })

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        return render(request, "shops/checkout.html", {
            "items": cart_items,
            "form": form,
            "total": total,
        })

    payment_method = form.cleaned_data["payment_method"]
    address = form.cleaned_data["address"]

    with transaction.atomic():
        locked_items = list(
            CartItem.objects
            .select_for_update()
            .select_related("product")
            .filter(cart=cart)
        )

        if not locked_items:
            messages.error(request, "Giỏ hàng trống!")
            return redirect('shops:cart_detail')

        product_ids = [item.product_id for item in locked_items]
        products = {
            p.id: p
            for p in Product.objects.select_for_update().filter(id__in=product_ids)
        }

        for item in locked_items:
            product = products.get(item.product_id)
            if not product or item.quantity > product.stock:
                available = product.stock if product else 0
                messages.error(
                    request,
                    f"Sản phẩm '{item.product.name}' chỉ còn {available} trong kho. Vui lòng cập nhật giỏ hàng."
                )
                return redirect('shops:cart_detail')

        order = Order.objects.create(
            user=request.user,
            address=address,
            payment_method=payment_method,
            payment_status='unpaid',
            total_price=0
        )

        total = 0
        for item in locked_items:
            product = products[item.product_id]
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                price=product.price
            )
            total += product.price * item.quantity
            product.stock -= item.quantity

        Product.objects.bulk_update(list(products.values()), ['stock'])
        order.total_price = total
        order.save(update_fields=['total_price'])
        CartItem.objects.filter(id__in=[item.id for item in locked_items]).delete()

    _send_order_email(order, request)

    if payment_method in ["bank", "momo"]:
        return redirect('shops:payment_qr', order_id=order.id)

    return redirect('shops:order_success', order_id=order.id)

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'shops/order_success.html', {
        'order': order
    })

def invoice_pdf(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40,leftMargin=40, topMargin=40,bottomMargin=40)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name='TitleStyle',
        fontSize=20,
        leading=24,
        alignment=TA_LEFT,
        spaceAfter=12
    )

    normal = styles['Normal']
    bold = ParagraphStyle(name='Bold', parent=styles['Normal'], fontSize=11, leading=14)
    bold.fontName = 'Helvetica-Bold'

    elements = []

    # ===== HEADER =====
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Paragraph(f"Order ID: #{order.id}", normal))
    elements.append(Paragraph(f"Date: {order.created.strftime('%d/%m/%Y')}", normal))
    elements.append(Spacer(1, 16))

    # ===== CUSTOMER INFO BOX =====
    customer_data = [
        ["Customer Info", ""],
        ["Name:", order.full_name or order.user.get_full_name()],
        ["Email:", order.email or order.user.email],
        ["Phone:", order.phone or (order.user.profile.phone if hasattr(order.user, 'profile') else "")],
        ["Address:", order.address],
    ]

    customer_table = Table(customer_data, colWidths=[120, 360])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('SPAN', (0,0), (-1,0)),
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('INNERGRID', (0,1), (-1,-1), 0.5, colors.grey),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))

    elements.append(customer_table)
    elements.append(Spacer(1, 20))

    # ===== PRODUCT TABLE =====
    table_data = [
        ["Image", "Product", "Price", "Qty", "Total"]
    ]

    for item in order.items.all():
        img_path = item.product.image.path if item.product.image else None

        if img_path and os.path.exists(img_path):
            img = Image(img_path, width=50, height=50)
        else:
            img = Paragraph("No image", normal)

        table_data.append([
            img,
            item.product.name,
            f"{item.price}",
            str(item.quantity),
            f"{item.get_total()}"
        ])

    product_table = Table(table_data, colWidths=[60, 200, 80, 60, 80])

    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.black),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),

        ('ALIGN',(1,1),(-1,-1),'CENTER'),
        ('ALIGN',(0,0),(0,-1),'LEFT'),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),

        ('BACKGROUND',(0,1),(-1,-1),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
    ]))

    elements.append(product_table)
    elements.append(Spacer(1, 20))

    # ===== TOTAL =====
    total_table = Table([
        ["Total:", f"{order.total_price}"]
    ], colWidths=[380, 80])

    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.lightgrey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN',(1,0),(-1,-1),'CENTER'),
        ('BOX',(0,0),(-1,-1),1,colors.black),
        ('TOPPADDING',(0,0),(-1,-1),12),
        ('BOTTOMPADDING',(0,0),(-1,-1),12),
    ]))

    elements.append(total_table)

    elements.append(Spacer(1, 30))

    # ===== FOOTER =====
    elements.append(Paragraph("Thank you for your purchase ❤️", styles['Heading3']))
    elements.append(Paragraph("Contact us: support@shop.com", normal))

    doc.build(elements)
    buffer.seek(0)

    return HttpResponse(buffer, content_type='application/pdf')

@login_required
def payment_qr(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    transfer_content = f"ORDER{order.id}"
    amount = int(order.total_price)
    qr_image_url = None

    if order.payment_method == 'bank':
        params = urlencode({
            "amount": amount,
            "addInfo": transfer_content,
            "accountName": "DO HOANG MINH CHAU",
        })
        qr_image_url = f"https://img.vietqr.io/image/MB-0866709954-compact2.png?{params}"
    elif order.payment_method == 'momo':
        # Dùng cùng thông tin tài khoản nhận để khách chuyển thủ công.
        params = urlencode({
            "amount": amount,
            "addInfo": transfer_content,
            "accountName": "DO HOANG MINH CHAU",
        })
        qr_image_url = f"https://img.vietqr.io/image/MB-0866709954-compact2.png?{params}"
    else:
        messages.info(request, "Đơn hàng này không dùng QR chuyển khoản.")
        return redirect('shops:order_detail', order_id=order.id)

    return render(request, 'shops/payment_qr.html', {
        'order': order,
        'qr_image_url': qr_image_url,
        'transfer_content': transfer_content,
    })

def _extract_order_id_from_webhook(payload):
    for key in ["order_id", "orderId", "order"]:
        value = payload.get(key)
        if value:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass

    text_sources = [
        payload.get("content"),
        payload.get("description"),
        payload.get("transfer_content"),
        payload.get("addInfo"),
        payload.get("message"),
    ]
    for text in text_sources:
        if not text:
            continue
        match = re.search(r"ORDER(\d+)", str(text).upper())
        if match:
            return int(match.group(1))

    return None


def _extract_amount_from_webhook(payload):
    for key in ["amount", "transferAmount", "value"]:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def _is_successful_payment(payload):
    success_values = {"success", "paid", "completed", "00", "0", "true"}
    status_candidates = [
        payload.get("status"),
        payload.get("transactionStatus"),
        payload.get("resultCode"),
        payload.get("code"),
    ]
    for value in status_candidates:
        if value is None:
            continue
        normalized = str(value).strip().lower()
        if normalized in success_values:
            return True
    return bool(payload.get("success") is True)


@csrf_exempt
@require_POST
def bank_payment_webhook(request):
    expected_secret = getattr(settings, "BANK_WEBHOOK_SECRET", "")
    received_secret = request.headers.get("X-Webhook-Secret", "")

    if not expected_secret:
        return JsonResponse(
            {"ok": False, "error": "Webhook secret is not configured"},
            status=500,
        )

    if not hmac.compare_digest(str(received_secret), str(expected_secret)):
        return JsonResponse({"ok": False, "error": "Invalid webhook secret"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON payload"}, status=400)

    if "data" in payload and isinstance(payload["data"], dict):
        payload = payload["data"]

    if not _is_successful_payment(payload):
        return JsonResponse({"ok": True, "updated": False, "reason": "not_success_status"})

    order_id = _extract_order_id_from_webhook(payload)
    if not order_id:
        return JsonResponse({"ok": False, "error": "Cannot determine order id"}, status=400)

    paid_amount = _extract_amount_from_webhook(payload)

    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)

            if order.status == "cancelled":
                return JsonResponse({"ok": True, "updated": False, "reason": "order_cancelled"})

            if order.payment_method not in ["bank", "momo"]:
                return JsonResponse({"ok": True, "updated": False, "reason": "not_transfer_order"})

            expected_amount = int(order.total_price)
            if paid_amount is not None and paid_amount != expected_amount:
                return JsonResponse(
                    {
                        "ok": False,
                        "error": "Amount mismatch",
                        "expected_amount": expected_amount,
                        "paid_amount": paid_amount,
                    },
                    status=400,
                )

            if order.payment_status != "paid":
                order.payment_status = "paid"
                order.save(update_fields=["payment_status"])
                return JsonResponse({"ok": True, "updated": True, "order_id": order.id})

            return JsonResponse({"ok": True, "updated": False, "reason": "already_paid", "order_id": order.id})
    except Order.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Order not found"}, status=404)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )
    items = order.items.all() # related_name='items' trong OrderItem

    return render(request, 'shops/order_detail.html', {
        'order': order,
        'items': items
    })

@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
    )
    items = order.items.all() # related_name='items' trong OrderItem

    return render(request, 'shops/admin_order_detail.html', {
        'order': order,
        'items': items
    })

@staff_member_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        order.status = new_status
        order.save()

        messages.success(request, 'Cập nhật trạng thái thành công!')
        return redirect('shops:admin_order_detail', order_id=order.id)

@staff_member_required
def order_list(request):
    month_raw = request.GET.get('month')
    year_raw = request.GET.get('year')
    start_date_raw = request.GET.get('start_date')
    end_date_raw = request.GET.get('end_date')
    has_filter = any([month_raw, year_raw, start_date_raw, end_date_raw])

    month = None
    year = None
    try:
        month = int(month_raw) if month_raw else None
    except (TypeError, ValueError):
        month = None
    try:
        year = int(year_raw) if year_raw else None
    except (TypeError, ValueError):
        year = None

    start_date = parse_date(start_date_raw) if start_date_raw else None
    end_date = parse_date(end_date_raw) if end_date_raw else None

    # Nếu chọn khoảng ngày thì ưu tiên theo khoảng ngày.
    if start_date or end_date:
        month = None
        year = None

    orders = Order.objects.select_related('user').all()
    if year:
        orders = orders.filter(created__year=year)
    if month:
        orders = orders.filter(created__month=month)
    if start_date and end_date:
        orders = orders.filter(created__date__range=(start_date, end_date))
    elif start_date:
        orders = orders.filter(created__date__gte=start_date)
    elif end_date:
        orders = orders.filter(created__date__lte=end_date)

    orders = orders.order_by('-created')

    current_year = timezone.now().year
    return render(request, 'shops/order_list.html', {
        'orders': orders,
        'months': list(range(1, 13)),
        'years': list(range(current_year - 5, current_year + 1)),
        'month': month,
        'year': year,
        'start_date': start_date,
        'end_date': end_date,
        'has_filter': has_filter,
    })

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user #chỉ lấy đơn của user
    )

    if request.method == 'GET':
        return render(request, 'shops/order_confirm_cancel.html', {
            'order': order
        })

    if request.method == 'POST':
        with transaction.atomic():
            order = get_object_or_404(
                Order.objects.select_for_update(),
                id=order_id,
                user=request.user
            )

            #chỉ được hủy khi đã xác nhận hoặc chờ xử lí
            if order.status in ['pending', 'confirmed']:
                order_items = list(order.items.select_related('product'))
                product_ids = [item.product_id for item in order_items]
                products = {
                    p.id: p
                    for p in Product.objects.select_for_update().filter(id__in=product_ids)
                }

                for item in order_items:
                    if item.product_id in products:
                        products[item.product_id].stock += item.quantity

                if products:
                    Product.objects.bulk_update(list(products.values()), ['stock'])

                order.status = 'cancelled'
                order.save(update_fields=['status'])
                messages.success(request, "Đơn hàng đã được hủy.")
            else:
                messages.error(request, "Không thể hủy đơn này.")

    return redirect('shops:order_history')

@login_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền xóa!")
        return redirect('shops:order_list')

    # 👉 GET: hiển thị trang confirm
    if request.method == 'GET':
        return render(request, 'shops/order_confirm_delete.html', {
            'order': order
        })

    # 👉 POST: mới xóa thật
    if request.method == 'POST':
        order.delete()
        messages.success(request, "Đã xóa đơn hàng!")
        return redirect('shops:order_list')

@staff_member_required
def dashboard(request):

    all_orders = Order.objects.all()

    # loại trừ đơn huỷ
    valid_orders = Order.objects.exclude(status='cancelled')

    # =========================
    # LẤY FILTER INPUT
    # =========================
    month = request.GET.get('month')
    year = request.GET.get('year')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    has_filter = any([month, year, start_date, end_date])

    # Ép kiểu
    month = int(month) if month else None
    year = int(year) if year else None
    start_date = parse_date(start_date) if start_date else None
    end_date = parse_date(end_date) if end_date else None
    #nếu có ngày thì xóa tháng năm
    if start_date or end_date:
        month = None
        year = None

    def apply_time_filters(queryset, date_field):
        if year:
            queryset = queryset.filter(**{f"{date_field}__year": year})
        if month:
            queryset = queryset.filter(**{f"{date_field}__month": month})

        if start_date and end_date:
            queryset = queryset.filter(**{f"{date_field}__date__range": (start_date, end_date)})
        elif start_date:
            queryset = queryset.filter(**{f"{date_field}__date__gte": start_date})
        elif end_date:
            queryset = queryset.filter(**{f"{date_field}__date__lte": end_date})
        return queryset

    # =========================
    # APPLY FILTER MONTH/YEAR
    # =========================
    valid_orders = apply_time_filters(valid_orders, "created")
    filtered_all_orders = apply_time_filters(all_orders, "created")

    # =========================
    # KPI SUMMARY
    # =========================
    total_revenue = valid_orders.aggregate(
        total=Sum('total_price')
    )['total'] or 0

    total_orders = valid_orders.count()

    today = timezone.now().date()

    revenue_today = Order.objects.exclude(status='cancelled').filter(
        created__date=today
    ).aggregate(total=Sum('total_price'))['total'] or 0

    revenue_this_month = Order.objects.exclude(status='cancelled').filter(
        created__year=today.year,
        created__month=today.month
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # =========================
    # DOANH THU THEO NGÀY (theo filter hiện tại)
    # =========================
    revenue_by_day = (
        valid_orders
        .annotate(day=TruncDay('created'))
        .values('day')
        .annotate(total=Sum('total_price'))
        .order_by('day')
    )

    # =========================
    # DOANH THU THEO THÁNG
    # =========================
    revenue_by_month = None
    if year:
        revenue_by_month = (
            Order.objects.exclude(status='cancelled')
            .filter(created__year=year)
            .annotate(month=TruncMonth('created'))
            .values('month')
            .annotate(total=Sum('total_price'))
            .order_by('month')
        )

    # =========================
    # DOANH THU THEO NĂM (khi không chọn năm)
    # =========================
    revenue_by_year = None
    if not year:
        revenue_by_year = (
            Order.objects.exclude(status='cancelled')
            .annotate(year=TruncYear('created'))
            .values('year')
            .annotate(total=Sum('total_price'))
            .order_by('year')
        )

    # =========================
    # TOP PRODUCTS (theo filter hiện tại)
    # =========================
    top_products = OrderItem.objects.exclude(order__status='cancelled')
    top_products = apply_time_filters(top_products, "order__created")

    top_products = (
        top_products
        .values('product__id', 'product__name')
        .annotate(
            total_qty=Sum('quantity'),
            revenue=Sum(F('quantity') * F('price'))
        )
        .order_by('-total_qty')[:10]
    )
    
    #THỐNG KÊ TRẠNG THÁI ĐƠN HÀNG
    status_counts_qs = (
        filtered_all_orders
        .values('status')
        .annotate(total=Count('id'))
    )
    status_count_map = {row['status']: row['total'] for row in status_counts_qs}
    order_status_stats = [
        ('pending', 'Chờ xử lý', status_count_map.get('pending', 0)),
        ('confirmed', 'Đã xác nhận', status_count_map.get('confirmed', 0)),
        ('shipping', 'Đang giao', status_count_map.get('shipping', 0)),
        ('completed', 'Hoàn thành', status_count_map.get('completed', 0)),
        ('cancelled', 'Đã hủy', status_count_map.get('cancelled', 0)),
    ]
    


    # =========================
    # SELECT DATA
    # =========================
    current_year = timezone.now().year
    months = list(range(1, 13))
    years = list(range(current_year - 5, current_year + 1))

    # ====== DỮ LIỆU BIỂU ĐỒ ======
    chart_labels = []
    chart_data = []

    # Date range
    if start_date or end_date:
        for r in revenue_by_day:
            chart_labels.append(r['day'].strftime('%d/%m'))
            chart_data.append(float(r['total']))

    # Month + Year → theo ngày trong tháng
    elif month and year:
        for r in revenue_by_day:
            chart_labels.append(r['day'].strftime('%d/%m'))
            chart_data.append(float(r['total']))

    # Chỉ chọn Year → theo tháng
    elif year:
        for r in revenue_by_month:
            chart_labels.append(r['month'].strftime('%m/%Y'))
            chart_data.append(float(r['total']))

    # Mặc định → theo năm
    else:
        for r in revenue_by_year:
            chart_labels.append(r['year'].strftime('%Y'))
            chart_data.append(float(r['total']))

    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'revenue_today': revenue_today,
        'revenue_this_month': revenue_this_month,
        'revenue_by_day': revenue_by_day,
        'revenue_by_month': revenue_by_month,
        'revenue_by_year': revenue_by_year,
        'top_products': top_products,
        'months': months,
        'years': years,
        'month': month,
        'year': year,
        'start_date': start_date,
        'end_date': end_date,
        'has_filter': has_filter,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'order_status_stats': order_status_stats,
        'filtered_order_count': filtered_all_orders.count(),
    }

    return render(request, 'shops/dashboard.html', context)

@login_required
def _send_order_email(order, request):
    if not order.user.email:
        return

    base_url = getattr(settings, "PUBLIC_BASE_URL", "").rstrip("/")
    history_path = reverse('shops:order_history')
    if base_url:
        order_history_url = f"{base_url}{history_path}"
    else:
        order_history_url = request.build_absolute_uri(history_path)

    context = {
        'order': order,
        'order_items': order.items.select_related('product').all(),
        'order_history_url': order_history_url,
        'payment_label': order.get_payment_method_display(),
        'status_label': order.get_status_display(),
    }

    subject = f"CSHOP - Xác nhận đơn hàng #{order.id}"
    html_content = render_to_string('shops/emails/order_confirmation.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.user.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=True)
