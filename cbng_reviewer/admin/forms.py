from django import forms

from cbng_reviewer.models import EditGroup


# Create the form class.
class EditGroupForm(forms.ModelForm):
    class Meta:
        model = EditGroup
        fields = ["name", "weight", "related_to", "group_type"]


class AddUserForm(forms.Form):
    username = forms.CharField(max_length=255)
