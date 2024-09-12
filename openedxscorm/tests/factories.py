import factory
from common.djangoapps.student.tests.factories import UserFactory
from opaque_keys.edx.keys import CourseKey, UsageKey

from openedxscorm.models import ScormState

COURSE_KEY = CourseKey.from_string("course-v1:Org+Course+Run")
USAGE_KEY = UsageKey.from_string("block-v1:Org+Course+Run+type@scorm+block@abcd123")


class ScormStateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScormState

    user = factory.SubFactory(UserFactory)
    course_key = COURSE_KEY
    usage_key = USAGE_KEY
    success_status = ScormState.SuccessChoices.UNKNOWN
    completion_status = ScormState.CompleteChoices.UNKNOWN
