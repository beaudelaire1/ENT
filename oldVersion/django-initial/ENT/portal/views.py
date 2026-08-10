from django.shortcuts import render, get_object_or_404, redirect
from django import forms

from core.models import Category
from curriculum.forms import CourseForm, ResourceForm
from curriculum.models import Course


def home(request):
    categories = Category.objects.all().order_by('name')
    context = {
        'categories': categories,
        'categories_navigation': categories,
    }
    return render(request, 'portal/home.html', context)


def category_detail(request, pk: int):
    category = get_object_or_404(Category, pk=pk)
    courses = category.courses.all()
    categories = Category.objects.all().order_by('name')
    context = {
        'category': category,
        'courses': courses,
        'categories_navigation': categories,
    }
    return render(request, 'portal/category_detail.html', context)


def add_resource(request, course_id: int):
    """
    Allows a user to add a resource to a specific course. The course is
    preselected and hidden in the form so users cannot attach a resource to the
    wrong course inadvertently. After creation, the user is redirected back to
    the detail page of the course's category.
    """
    course = get_object_or_404(Course, pk=course_id)
    categories = Category.objects.all().order_by('name')
    if request.method == 'POST':
        form = ResourceForm(request.POST)
        if form.is_valid():
            resource = form.save()
            # redirect to the category page to display the new resource
            return redirect('portal:category_detail', pk=course.category.pk)
    else:
        # Pre-fill the course field and hide it from the user
        form = ResourceForm(initial={'course': course})
        form.fields['course'].widget = forms.HiddenInput()
    context = {
        'form': form,
        'course': course,
        'categories_navigation': categories,
    }
    return render(request, 'portal/add_resource.html', context)


def add_course(request):
    categories = Category.objects.all().order_by('name')
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            return redirect(course.category.get_absolute_url())
    else:
        form = CourseForm()
    context = {
        'form': form,
        'categories_navigation': categories,
    }
    return render(request, 'portal/add_course.html', context)
