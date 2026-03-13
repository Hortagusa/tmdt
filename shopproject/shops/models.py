from django.contrib.auth.models import User
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, null=True)

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


class Comment(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    content = models.TextField()

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Cart - {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    @property
    def total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


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

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='unpaid'
    )

    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    price = models.DecimalField(max_digits=12, decimal_places=2)

    quantity = models.PositiveIntegerField()

    def get_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"
    
class Wishlist(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="wishlist_items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlisted_users"
    )

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created']

    def __str__(self):
        return f"{self.user.username} ❤️ {self.product.name}"
    
class Notification(models.Model):

    NOTIFICATION_TYPES = [
        ('order', 'Order Update'),
        ('restock', 'Product Restock'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )

    is_read = models.BooleanField(default=False)

    link = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.user.username} - {self.message[:30]}"
    
class Wallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="wallet"
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"{self.user.username} wallet"
    
class WalletTransaction(models.Model):

    TRANSACTION_TYPE = [
        ('refund', 'Refund'),
        ('payment', 'Payment'),
        ('deposit', 'Deposit')
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE
    )

    description = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)
    
class ReturnRequest(models.Model):

    STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('refunded', 'Refunded'),
        ('resolved', 'Resolved'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='returns'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='pending'
    )

    created = models.DateTimeField(auto_now_add=True)

    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )