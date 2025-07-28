from rest_framework import serializers

from cbng_reviewer.models import EditGroup, Edit


class EditGroupSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField(read_only=True, source="get_type")

    def get_type(self, obj):
        return obj.get_group_type_display()

    class Meta:
        model = EditGroup
        fields = ["id", "name", "related_to", "type"]


class DeletedEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edit
        fields = ["id", "name"]
