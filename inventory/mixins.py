from django.contrib import messages
from django.shortcuts import redirect


class SuccessMessageMixin:
    """Миксин для сообщений об успехе"""
    success_message = ""

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response


class HistoryTrackingMixin:
    """Миксин для отслеживания истории изменений"""

    def form_valid(self, form):
        from core.audit import build_change_reason

        obj = form.save(commit=False)
        obj._history_user = self.request.user
        obj._change_reason = build_change_reason(self.get_action_name())
        obj.save()
        form.save_m2m()

        return super().form_valid(form)

    def get_action_name(self):
        """Название действия - должно быть переопределено"""
        raise NotImplementedError