from django import forms
from .models import Course, Resource


class CourseForm(forms.ModelForm):
    """Form to add a new course/resource."""

    class Meta:
        model = Course
        fields = ['title', 'description', 'link', 'category', 'provider']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'link': forms.URLInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'provider': forms.Select(attrs={'class': 'form-select'}),
        }


# Form to create or update a single resource.
class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['course', 'title', 'description', 'link', 'resource_type']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'link': forms.URLInput(attrs={'class': 'form-control'}),
            'resource_type': forms.Select(attrs={'class': 'form-select'}),
        }
