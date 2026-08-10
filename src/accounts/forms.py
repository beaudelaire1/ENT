from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Invitation, UserProfile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["display_name", "theme", "accent_color", "timezone"]
        widgets = {"accent_color": forms.TextInput(attrs={"type": "color"})}


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ["email"]


class InvitationAcceptForm(forms.Form):
    username = forms.CharField(max_length=150, label="Nom d’utilisateur")
    display_name = forms.CharField(max_length=120, required=False, label="Nom affiché")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Mot de passe")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmation")

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ce nom d’utilisateur est déjà utilisé.")
        return username

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Les mots de passe ne correspondent pas.")
        elif cleaned.get("password1"):
            validate_password(cleaned["password1"])
        return cleaned
