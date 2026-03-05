from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'category',
            'price',
            'stock',
            'description',
            'image'
        ]

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']

class CheckoutForm(forms.Form):
    address = forms.CharField(widget=forms.Textarea(attrs={'class':'form-control'}))

    payment_method = forms.ChoiceField(
        choices=[
            ('cod', 'Thanh toán khi nhận hàng (COD)'),
            ('bank', 'Chuyển khoản ngân hàng'),
            ('momo', 'MoMo'),
        ],
        widget=forms.RadioSelect
    )