from django.db import models
from django.urls import reverse

from core.models import Category, ResourceProvider


class Course(models.Model):
    """Represents a course or learning resource within a category."""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='courses')
    provider = models.ForeignKey(ResourceProvider, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    link = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return self.link


class Module(models.Model):
    """Optional breakdown of a course into modules/lessons."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self) -> str:
        return f"{self.order}. {self.title}"


# New model to represent individual resources within a course
class Resource(models.Model):
    """Represents a specific learning resource attached to a course.

    Each course can have multiple resources (videos, articles, PDFs, etc.) so
    learners can access a variety of materials. Separating resources from the
    Course model allows the system to grow without duplicating course entries
    when new materials are added.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    link = models.URLField()
    RESOURCE_TYPE_CHOICES = [
        ('video', 'Vidéo'),
        ('article', 'Article'),
        ('pdf', 'PDF'),
        ('audio', 'Audio'),
        ('other', 'Autre'),
    ]
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPE_CHOICES, default='other')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self) -> str:
        return f"{self.title} ({self.get_resource_type_display()})"
