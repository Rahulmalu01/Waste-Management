from django import forms
from .models import Bin

class BinForm(forms.ModelForm):
    """Form for creating and updating bins"""
    
    class Meta:
        model = Bin
        fields = [
            'bin_id', 'name', 'location_name',
            'latitude', 'longitude',
            'bin_height_cm', 'threshold_percentage',
            'is_active'
        ]
        widgets = {
            'bin_id': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white',
                'placeholder': 'e.g., BIN-001',
                'required': True
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white',
                'placeholder': 'e.g., Main Street Storage',
                'required': True
            }),
            'location_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white',
                'placeholder': 'e.g., Near City Hall'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white',
                'placeholder': 'e.g., 28.6139',
                'step': '0.0001',
                'required': True
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white',
                'placeholder': 'e.g., 77.2090',
                'step': '0.0001',
                'required': True
            }),
            'bin_height_cm': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white',
                'placeholder': 'e.g., 100',
                'step': '0.1',
                'required': True
            }),
            'threshold_percentage': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white',
                'placeholder': 'e.g., 80',
                'step': '0.1',
                'min': '0',
                'max': '100'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 rounded'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if latitude is not None:
            if not (-90 <= latitude <= 90):
                self.add_error('latitude', 'Latitude must be between -90 and 90')
        
        if longitude is not None:
            if not (-180 <= longitude <= 180):
                self.add_error('longitude', 'Longitude must be between -180 and 180')
        
        return cleaned_data