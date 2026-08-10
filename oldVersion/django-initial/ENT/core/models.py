from django.db import models


class Category(models.Model):
    """Represents a subject area or thematic category (e.g. Anglais, Informatique)."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        """Returns the URL for the category detail page.

        This method references the `portal` namespace to keep navigation
        consistent across the site. If the URL pattern changes in the future,
        update the reverse call accordingly.
        """
        from django.urls import reverse
        return reverse('portal:category_detail', args=[self.pk])


class ResourceProvider(models.Model):
    """Represents a platform or provider of learning resources."""
    name = models.CharField(max_length=100)
    website = models.URLField()

    def __str__(self) -> str:
        return self.name
