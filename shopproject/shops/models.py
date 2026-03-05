from django.contrib.auth.models import User
from django.db import models
from django.conf import settings
from django.utils.text import slugify

# Create your models here.
class Category(models.Model):
    name = models.CharField()
    slug = models.SlugField()

    def __str__(self):
        return self.name

class Product(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(
            Category,
            on_delete=models.SET_NULL,
            null=True,
            related_name='products'
        )
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    description = models.TextField()
    image = models.ImageField(upload_to='products/')
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    @property
    def total_price(self):
        return self.product.price * self.quantity

class Order(models.Model):
    PAYMENT_METHODS = [
        ('cod', 'Cash on Delivery'),
        ('bank', 'Bank Transfer'),
        ('momo', 'MoMo'),
    ]

    PAYMENT_STATUS = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
    ]

    STATUS_CHOICES = [
            ('pending', 'Chờ xử lý'),
            ('confirmed', 'Đã xác nhận'),
            ('shipping', 'Đang giao'),
            ('completed', 'Hoàn thành'),
            ('cancelled', 'Đã huỷ'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='unpaid')

    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending'
    )

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def get_total(self):
        return self.price * self.quantity

