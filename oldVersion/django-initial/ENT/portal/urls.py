from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.home, name='home'),
    path('category/<int:pk>/', views.category_detail, name='category_detail'),
    path('add_course/', views.add_course, name='add_course'),
    # route to add a new resource to a specific course
    path('course/<int:course_id>/add_resource/', views.add_resource, name='add_resource'),
]
