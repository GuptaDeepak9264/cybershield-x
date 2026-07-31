import os

from django import forms
from django.core.exceptions import ValidationError

from .models import ScanLog, ThreatIntelEntry

# Kept intentionally small and explicit rather than trying to be exhaustive -
# this is a UX guardrail, not a security control. Real content inspection
# happens server-side in the FastAPI scanning service (Milestone 3).
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".doc", ".docx", ".zip", ".exe", ".txt", ".jpg", ".png"}
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class FileUploadForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        ext = os.path.splitext(uploaded.name)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise ValidationError(f"Unsupported file type '{ext}'.")
        if uploaded.size > MAX_UPLOAD_SIZE_BYTES:
            raise ValidationError("File exceeds the 25 MB limit.")
        return uploaded


class URLScanForm(forms.Form):
    url = forms.URLField(
        widget=forms.URLInput(attrs={"class": "form-control", "placeholder": "https://example.com"})
    )


class ThreatIntelForm(forms.ModelForm):
    class Meta:
        model = ThreatIntelEntry
        fields = ["indicator", "indicator_type", "severity", "description"]
        widgets = {
            "indicator": forms.TextInput(attrs={"class": "form-control"}),
            "indicator_type": forms.Select(attrs={"class": "form-select"}),
            "severity": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
