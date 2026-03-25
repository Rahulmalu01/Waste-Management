from django import forms
from account.models import CustomUser
from bins.models import Bin
from .models import Route


class RouteAssignmentForm(forms.ModelForm):
    assigned_driver = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='DRIVER'),
        required=True,
        empty_label="Select Driver"
    )

    class Meta:
        model = Route
        fields = ['assigned_driver', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = [
            ('ASSIGNED', 'Assigned'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
            ('CANCELLED', 'Cancelled'),
        ]


class ReportFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    driver = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='DRIVER'),
        required=False,
        empty_label="All Drivers"
    )
    bin_obj = forms.ModelChoiceField(
        queryset=Bin.objects.all().order_by('bin_id'),
        required=False,
        empty_label="All Bins",
        label="Bin"
    )
    route_status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Statuses'),
            ('PLANNED', 'Planned'),
            ('ASSIGNED', 'Assigned'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
            ('CANCELLED', 'Cancelled'),
        ]
    )