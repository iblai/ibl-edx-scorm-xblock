import factory

from openedxscorm.models import ScormState


class ScormStateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScormState
