from rest_framework import serializers

from cbng_reviewer.models import EditGroup, Edit


class EditGroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EditGroup
        fields = ["id", "name"]


class DeletedEditSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Edit
        fields = ["id", "name"]
