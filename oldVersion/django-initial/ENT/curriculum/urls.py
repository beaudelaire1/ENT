
from django.urls import path
from . import views

urlpatterns = [
    path('', views.matiere_list, name='matiere_list'),
    path('add/', views.matiere_add, name='matiere_add'),
    path('<int:pk>/edit/', views.matiere_edit, name='matiere_edit'),
    path('<int:pk>/hours/', views.update_hours, name='update_hours'),
    path('competence/add/', views.competence_add, name='competence_add'),
    path('competence/<int:pk>/edit/', views.competence_edit, name='competence_edit'),
]
