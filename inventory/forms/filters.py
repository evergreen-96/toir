from django import forms


class BaseFilterForm(forms.Form):
    """Базовая форма фильтрации"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск...'
        })
    )

    def get_filtered_queryset(self, queryset):
        """Применяет фильтры к queryset"""
        if self.is_valid():
            search = self.cleaned_data.get('search')
            if search:
                queryset = self.apply_search(queryset, search)

        return queryset

    def apply_search(self, queryset, search_query):
        """Применяет поиск - должен быть переопределен"""
        return queryset