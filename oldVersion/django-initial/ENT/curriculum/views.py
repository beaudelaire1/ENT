
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Matiere, Competence
from .forms import MatiereForm, CompetenceForm

def matiere_list(request):
    qs = Matiere.objects.all().order_by('semester','name')
    return render(request, 'curriculum/matiere_list.html', {'matieres': qs})

def matiere_add(request):
    if request.method == 'POST':
        form = MatiereForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Matière créée.')
            return redirect('matiere_list')
    else:
        form = MatiereForm()
    return render(request, 'curriculum/matiere_form.html', {'form': form, 'title': 'Ajouter une matière'})

def matiere_edit(request, pk):
    obj = get_object_or_404(Matiere, pk=pk)
    if request.method == 'POST':
        form = MatiereForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Matière mise à jour.')
            return redirect('matiere_list')
    else:
        form = MatiereForm(instance=obj)
    return render(request, 'curriculum/matiere_form.html', {'form': form, 'title': f'Modifier {obj.name}', 'matiere': obj})

@require_POST
def update_hours(request, pk):
    obj = get_object_or_404(Matiere, pk=pk)
    action = request.POST.get('action')
    step = int(request.POST.get('step', '1'))
    if action == 'inc':
        obj.done_hours += step
    elif action == 'dec':
        obj.done_hours = max(0, obj.done_hours - step)
    obj.save()
    messages.success(request, f"Heures mises à jour: {obj.done_hours} / {obj.planned_hours}")
    return redirect('matiere_edit', pk=obj.pk)

def competence_add(request):
    initial = {}
    if 'matiere' in request.GET:
        initial['matiere'] = request.GET.get('matiere')
    if request.method == 'POST':
        form = CompetenceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Compétence ajoutée.')
            return redirect('matiere_list')
    else:
        form = CompetenceForm(initial=initial)
    return render(request, 'curriculum/competence_form.html', {'form': form, 'title':'Ajouter une compétence'})

def competence_edit(request, pk):
    obj = get_object_or_404(Competence, pk=pk)
    if request.method == 'POST':
        form = CompetenceForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Compétence mise à jour.')
            return redirect('matiere_list')
    else:
        form = CompetenceForm(instance=obj)
    return render(request, 'curriculum/competence_form.html', {'form': form, 'title': f'Modifier: {obj.title}'})
