from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django import forms
from .models import HumanResource
from django.db.models import Count


class HumanResourceForm(forms.ModelForm):
    class Meta:
        model = HumanResource
        fields = ["name", "job_title", "manager"]
        widgets = {
            "job_title": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["manager"].queryset = HumanResource.objects.exclude(
                pk=self.instance.pk
            )

        # 🔑 ОБЯЗАТЕЛЬНО: option + selected
        if self.instance.pk and self.instance.job_title:
            self.fields["job_title"].choices = [
                (self.instance.job_title, self.instance.job_title)
            ]
            self.initial["job_title"] = self.instance.job_title


class HRListView(ListView):
    model = HumanResource
    template_name = "hr/hr_list.html"
    paginate_by = 20
    ordering = ["name"]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("manager")
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

        manager_id = self.request.GET.get("manager")
        job_title = self.request.GET.get("job_title")
        only_managers = self.request.GET.get("only_managers")

        ctx["only_managers"] = only_managers
        ctx["current_job_title"] = job_title

        ctx["current_manager_obj"] = None
        if manager_id:
            ctx["current_manager_obj"] = (
                HumanResource.objects
                .filter(pk=manager_id)
                .only("id", "name", "job_title")
                .first()
            )

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


class HumanResourceDeleteView(View):
    def post(self, request, pk):
        obj = get_object_or_404(HumanResource, pk=pk)

        try:
            obj.delete()
            return JsonResponse({"ok": True})

        except ProtectedError as e:
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": [str(o) for o in e.protected_objects],
            }, status=400)


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


def hr_job_title_autocomplete(request):
    q = request.GET.get("q", "")

    qs = (
        HumanResource.objects
        .exclude(job_title="")
        .values_list("job_title", flat=True)
        .distinct()
        .order_by("job_title")
    )

    if q:
        qs = qs.filter(job_title__icontains=q)

    qs = qs[:20]

    return JsonResponse({
        "results": [
            {"id": title, "text": title}
            for title in qs
        ]
    })
