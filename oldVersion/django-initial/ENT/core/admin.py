from django.contrib import admin
from .models import Category, ResourceProvider

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ResourceProvider)
class ResourceProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'website')
    search_fields = ('name',)
