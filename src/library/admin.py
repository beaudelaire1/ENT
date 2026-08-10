from django.contrib import admin

from .models import Folder, LibraryItem, Tag

admin.site.register(Folder)
admin.site.register(Tag)
admin.site.register(LibraryItem)
