from django.http import JsonResponse
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
        fields = ["name", "job_title", "manager"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["manager"].queryset = HumanResource.objects.exclude(
                pk=self.instance.pk
            )

from django.db.models import Count

class HRListView(ListView):
    model = HumanResource
    template_name = "hr/hr_list.html"
    paginate_by = 20
    ordering = ["name"]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .annotate(subordinates_count=Count("subordinates"))
        )

        manager_id = self.request.GET.get("manager")
        job_title = self.request.GET.get("job_title")
        only_managers = self.request.GET.get("only_managers")

        if manager_id:
            qs = qs.filter(manager_id=manager_id)

        if job_title:
            qs = qs.filter(job_title__icontains=job_title)

        if only_managers:
            qs = qs.filter(subordinates_count__gt=0)

        return qs


    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["managers"] = HumanResource.objects.order_by("name")

        ctx["current_manager"] = self.request.GET.get("manager", "")
        ctx["current_job_title"] = self.request.GET.get("job_title", "")
        ctx["only_managers"] = self.request.GET.get("only_managers")

        return ctx



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


def hr_manager_autocomplete(request):
    q = request.GET.get("q", "")

    qs = HumanResource.objects.all()

    if q:
        qs = qs.filter(name__icontains=q)

    qs = qs.order_by("name")[:20]

    return JsonResponse({
        "results": [
            {
                "id": x.pk,
                "text": f"{x.name} — {x.job_title}" if x.job_title else x.name
            }
            for x in qs
        ]
    })
