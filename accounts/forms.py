from django import forms
from .models import AWSAccount

class AWSAccountForm(forms.ModelForm):
    class Meta:
        model = AWSAccount
        fields = ["access_key", "secret_key", "region"]
        widgets = {
            "secret_key": forms.PasswordInput(),
        }