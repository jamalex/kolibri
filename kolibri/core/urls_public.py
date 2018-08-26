"""
Kolibri public url patterns
===========================

This module defines the "public API" endpoints that we expect to be called externally by other
instances of Kolibri, or by 3rd party applications or clients. For this reason, these endpoints
need to be maintained with backwards compatibility to ensure ongoing support for older clients.

If breaking changes need to be introduced to an endpoint, a new endpoint should be created
instead, at a different URL (e.g. with version number v2 instead of v1), leaving the original
endpoint in place and maintained to the best extent possible so older clients can still use it.

"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework import routers

from .api import InfoViewSet
from .auth.api import PublicFacilityViewSet

router = routers.SimpleRouter()

router.register(r'v1/facility', PublicFacilityViewSet, base_name='publicfacility')
router.register(r'info', InfoViewSet, base_name='info')

urlpatterns = router.urls