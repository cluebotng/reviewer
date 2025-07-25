from django.forms import ModelForm

from cbng_reviewer.models import EditGroup


# Create the form class.
class EditGroupForm(ModelForm):
    class Meta:
        model = EditGroup
        fields = ["name", "weight"]
