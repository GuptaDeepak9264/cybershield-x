from django import forms

from apps.accounts.models import User

from .models import Notification


class NotificationForm(forms.ModelForm):
    recipient = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.STUDENT),
        required=False,
        empty_label="Broadcast to all students",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Notification
        fields = ["recipient", "title", "message"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
