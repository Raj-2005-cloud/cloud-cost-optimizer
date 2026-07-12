from django import forms
from .models import AWSAccount

class AWSAccountForm(forms.ModelForm):
    class Meta:
        model = AWSAccount
        fields = ["access_key", "secret_key", "region", "alert_email"]
        labels = {
            "alert_email": "Alert Email (Gmail)",
        }
        widgets = {
            "secret_key": forms.PasswordInput(),
            "alert_email": forms.EmailInput(attrs={"placeholder": "your-email@gmail.com"}),
        }