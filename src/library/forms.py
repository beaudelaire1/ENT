from __future__ import annotations

import json

import bleach
from django import forms
from django.conf import settings

from .models import Folder, LibraryItem, Tag

ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "s",
    "blockquote",
    "pre",
    "code",
    "h1",
    "h2",
    "h3",
    "ol",
    "ul",
    "li",
    "a",
]
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "target", "rel"]}


class LibraryItemForm(forms.ModelForm):
    note_delta_json = forms.CharField(widget=forms.HiddenInput, required=False)
    note_html_input = forms.CharField(widget=forms.HiddenInput, required=False)
    note_text_input = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = LibraryItem
        fields = ["kind", "title", "description", "folder", "tags", "url", "file", "provider_name", "source_category"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "tags": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["folder"].queryset = Folder.objects.filter(owner=user)
        self.fields["tags"].queryset = Tag.objects.filter(owner=user)
        if self.instance.pk:
            self.fields["note_delta_json"].initial = json.dumps(self.instance.note_delta)
            self.fields["note_html_input"].initial = self.instance.note_html
            self.fields["note_text_input"].initial = self.instance.note_text

    def clean_file(self):
        upload = self.cleaned_data.get("file")
        if upload and getattr(upload, "size", 0) > settings.LIBRARY_MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"Le fichier dépasse {settings.LIBRARY_MAX_UPLOAD_MB} Mo.")
        return upload

    def clean_note_delta_json(self):
        value = self.cleaned_data.get("note_delta_json") or "{}"
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("Le contenu structuré de la note est invalide.") from exc
        if not isinstance(data, dict):
            raise forms.ValidationError("Le contenu structuré de la note est invalide.")
        return data

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("kind") == LibraryItem.Kind.NOTE:
            self.instance.note_delta = cleaned.get("note_delta_json") or {}
            self.instance.note_text = (cleaned.get("note_text_input") or "").strip()
            self.instance.note_html = self.sanitize_note_html(cleaned.get("note_html_input") or "")
        return cleaned

    @staticmethod
    def sanitize_note_html(value):
        return bleach.clean(
            value,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=["http", "https", "mailto"],
            strip=True,
        )

    def save(self, commit=True):
        item = super().save(commit=False)
        item.owner = self.user
        if item.kind == LibraryItem.Kind.NOTE:
            item.note_delta = self.cleaned_data.get("note_delta_json") or {}
            item.note_text = (self.cleaned_data.get("note_text_input") or "").strip()
            item.note_html = self.sanitize_note_html(self.cleaned_data.get("note_html_input") or "")
        if item.file:
            item.file_size = getattr(item.file, "size", item.file_size)
            item.mime_type = (
                getattr(item.file.file, "content_type", item.mime_type)
                if hasattr(item.file, "file")
                else item.mime_type
            )
        if commit:
            item.full_clean()
            item.save()
            self.save_m2m()
        return item


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ["name", "parent"]

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Folder.objects.filter(owner=user)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.owner = self.user
        if commit:
            instance.full_clean()
            instance.save()
        return instance


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "color"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}
