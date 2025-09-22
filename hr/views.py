from django.views.generic import ListView, DetailView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django import forms
from .models import HumanResource

class HumanResourceForm(forms.ModelForm):
    class Meta:
        model = HumanResource
        fields = ["name", "job_title"]

class HRListView(ListView):
    model = HumanResource
    template_name = "hr/hr_list.html"
    paginate_by = 20
    ordering = ["name"]

class HRDetailView(DetailView):
    model = HumanResource
    template_name = "hr/hr_detail.html"

def hr_create(request):
    if request.method == "POST":
        form = HumanResourceForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Сотрудник создан.")
            return redirect("hr:hr_detail", pk=obj.pk)
    else:
        form = HumanResourceForm()
    return render(request, "hr/hr_form.html", {"form": form, "create": True})

def hr_update(request, pk):
    obj = get_object_or_404(HumanResource, pk=pk)
    if request.method == "POST":
        form = HumanResourceForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Изменения сохранены.")
            return redirect("hr:hr_detail", pk=obj.pk)
    else:
        form = HumanResourceForm(instance=obj)
    return render(request, "hr/hr_form.html", {"form": form, "create": False, "obj": obj})

class HumanResourceDeleteView(DeleteView):
    model = HumanResource
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("hr:hr_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("hr:hr_detail", args=[self.object.pk])
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            response = super().post(request, *args, **kwargs)
            messages.success(request, "Сотрудник удалён.")
            return response
        except ProtectedError:
            messages.error(request, "Нельзя удалить: есть связанные объекты.")
            return redirect("hr:hr_detail", pk=self.object.pk)
