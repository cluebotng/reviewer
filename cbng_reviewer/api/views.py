import random
from typing import Optional

from django.http import StreamingHttpResponse, Http404, HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from cbng_reviewer.api.serializers import EditGroupSerializer
from cbng_reviewer.libs.django import reviewer_required
from cbng_reviewer.libs.edit_set import EditSetDumper
from cbng_reviewer.models import EditGroup, Edit, Classification, CLASSIFICATION_IDS


class EditGroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows edit groups to be viewed.
    """

    queryset = EditGroup.objects.all()
    serializer_class = EditGroupSerializer

    @action(detail=True, url_path="deleted-edits")
    def deleted_edits(self, *args, **kwargs):
        edit_group = self.get_object()
        deleted_edit_ids = edit_group.edit_set.filter(deleted=True).values_list("id", flat=True)
        return Response(deleted_edit_ids)

    @action(detail=True, url_path="completed-classifications")
    def completed_edits(self, *args, **kwargs):
        edit_group = self.get_object()
        return Response(
            {
                classified_edit.id: classified_edit.classification
                for classified_edit in edit_group.edit_set.filter(deleted=False, status=2).exclude(classification=None)
            }
        )

    @action(detail=True, url_path="dump-report-status")
    def report_status(self, *args, **kwargs):
        edit_group = self.get_object()
        if edit_group.name not in {
            "Legacy Report Interface Import",
            "Report Interface Import",
        }:
            raise Http404

        def _calculate_report_status(edit: Edit) -> Optional[int]:
            """
            0 => statusNameToId('Queued to be reviewed'),
            1 => statusNameToId('Partially reviewed'),
            2 => statusNameToId('Reviewed - Included in dataset as Vandalism'),
            3 => statusNameToId('Reviewed - Included in dataset as Constructive'),
            4 => statusNameToId('Reviewed - Not included in dataset'),
            5 => statusNameToId('Edit Data Has Been Removed'),
            """
            if edit.status == 0:
                return 0
            if edit.status == 1:
                return 1
            if edit.classification == 0:
                return 2
            if edit.classification == 1:
                return 3
            if edit.classification == 2:
                return 4

        edit_statuses = {}
        for edit in edit_group.edit_set.filter(deleted=False):
            report_status = _calculate_report_status(edit)
            if report_status is not None:
                edit_statuses[edit.id] = report_status

        # This is basically just to provide some feedback to the user/report interface
        # We can never use this for training as we are missing data
        for edit in edit_group.edit_set.filter(deleted=True).exclude(status=2):
            edit_statuses[edit.id] = 5

        return Response(edit_statuses)

    @action(detail=True, url_path="dump-editset")
    def dump(self, *args, **kwargs):
        edit_group = self.get_object()
        dumper = EditSetDumper()
        target_edits = edit_group.edit_set.filter(status=2).exclude(classification=None)

        def _xml_generator():
            yield "<WPEditSet>\n"
            for edit in target_edits:
                if wp_edit := dumper.generate_wp_edit(edit):
                    yield wp_edit
            yield "</WPEditSet>\n"

        return StreamingHttpResponse(_xml_generator(), content_type="text/xml")


@reviewer_required()
@api_view(["POST"])
def store_edit_classification(request):
    edit = get_object_or_404(Edit, id=request.data.get("edit_id"))
    user_classification = request.data.get("classification")
    if user_classification not in CLASSIFICATION_IDS:
        return HttpResponse(status=400, content="Invalid classification")

    if (edit.classification is not None and edit.classification != user_classification) and not request.data.get(
        "confirmation"
    ):
        return Response({"require_confirmation": True})

    Classification.objects.create(
        edit=edit,
        user=request.user,
        classification=user_classification,
        comment=request.data.get("comment"),
    )
    return Response({})


@reviewer_required()
@api_view()
def get_next_edit_id_for_review(request):
    # Check each edit group (highest weight first)
    edits_already_classified = set(Classification.objects.filter(user=request.user).values_list("edit_id", flat=True))
    for edit_group in EditGroup.objects.filter(weight__gt=0).order_by("-weight"):
        if (
            potential_edits := edit_group.edit_set.filter(deleted=False)
            .exclude(status=2)
            .exclude(id__in=edits_already_classified)
            .values_list("id", flat=True)
        ):
            selected_edit = random.choice(potential_edits)  # nosec: B311
            return Response({"edit_id": selected_edit})

    return Response({"edit_id": None, "message": "No Pending Edit Found"})


@api_view()
def dump_edit_as_wp_edit(request, edit_id):
    edit = get_object_or_404(Edit, id=edit_id, status=2)
    if wp_edit := EditSetDumper().generate_wp_edit(edit):
        return HttpResponse(wp_edit, content_type="text/xml")
    raise Http404
