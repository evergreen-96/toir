from django.http import JsonResponse
from django.db.models.deletion import ProtectedError
from django.contrib import messages
from django.shortcuts import redirect


class AjaxProtectedDeleteMixin:
    success_message = "Объект удалён"
    protected_message = "Нельзя удалить: есть связанные объекты"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        try:
            self.object.delete()

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True})

            messages.success(request, self.success_message)
            return redirect(self.get_success_url())

        except ProtectedError as e:
            related = [str(obj) for obj in e.protected_objects]

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "ok": False,
                    "error": self.protected_message,
                    "related": related,
                }, status=400)

            messages.error(request, self.protected_message)
            return redirect(self.get_success_url())
