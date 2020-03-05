import hashlib
import os
import uuid

from django.core.management import call_command
from django.test import TransactionTestCase
from le_utils.constants import content_kinds
from le_utils.constants import file_formats
from le_utils.constants import format_presets
from mock import patch

from .sqlalchemytesting import django_connection_engine
from kolibri.core.content.models import ContentNode
from kolibri.core.content.models import File
from kolibri.core.content.models import LocalFile
from kolibri.core.content.utils.paths import get_content_storage_file_path


def get_engine(connection_string):
    return django_connection_engine()


test_channel_id = "6199dde695db4ee4ab392222d5af1e5c"


@patch("kolibri.core.content.utils.sqlalchemybridge.get_engine", new=get_engine)
class UnavailableContentDeletion(TransactionTestCase):
    def setUp(self):
        super(UnavailableContentDeletion, self).setUp()

        # create an unavailable contentnode
        self.unavailable_contentnode = ContentNode(
            title="wow",
            available=False,
            id=uuid.uuid4().hex,
            content_id=uuid.uuid4().hex,
            channel_id=uuid.uuid4().hex,
        )
        self.unavailable_contentnode.save()

        self.hash = hashlib.md5("wow".encode()).hexdigest()
        self.extension = file_formats.PDF

        # with an associated stored local file
        self.stored_local_file = LocalFile(
            id=self.hash, extension=self.extension, available=True, file_size=1000000
        )
        self.stored_local_file.save()

        self.file = File(
            local_file=self.stored_local_file,
            contentnode=self.unavailable_contentnode,
            preset=format_presets.DOCUMENT,
            id=uuid.uuid4().hex,
        )
        self.file.save()

        # actually store a dummy local file
        self.filename = "{}.{}".format(self.hash, self.extension)

        self.path = get_content_storage_file_path(self.filename)
        path_dir = os.path.dirname(self.path)
        if not os.path.exists(path_dir):
            os.makedirs(path_dir)
        tempfile = open(self.path, "w")
        tempfile.write("wow")
        tempfile.close()

    def delete_content(self):
        num_deleted = 0
        freed_bytes = 0
        for deleted, file in LocalFile.objects.delete_unused_files():
            if deleted:
                num_deleted += 1
                freed_bytes += file.file_size
        return num_deleted, freed_bytes

    def test_delete_unavailable_stored_files(self):
        self.assertEqual(LocalFile.objects.get_unused_files().count(), 1)
        deleted, freed_bytes = self.delete_content()
        self.assertEqual(deleted, 1)
        self.assertEqual(freed_bytes, self.stored_local_file.file_size)

        self.assertEqual(os.path.exists(self.path), False)
        self.assertEqual(LocalFile.objects.get_unused_files().count(), 0)

    def test_dont_delete_used_stored_files(self):
        available_contentnode = ContentNode.objects.create(
            title="wow",
            available=True,
            id=uuid.uuid4().hex,
            content_id=uuid.uuid4().hex,
            channel_id=uuid.uuid4().hex,
        )
        File.objects.create(
            local_file=self.stored_local_file,
            contentnode=available_contentnode,
            preset=format_presets.DOCUMENT,
            id=uuid.uuid4().hex,
        )
        self.assertEqual(LocalFile.objects.get_unused_files().count(), 0)
        deleted, freed_bytes = self.delete_content()
        self.assertEqual(deleted, 0)

    def tearDown(self):
        call_command("flush", interactive=False)
        super(UnavailableContentDeletion, self).tearDown()


@patch("kolibri.core.content.utils.sqlalchemybridge.get_engine", new=get_engine)
class DeleteContentTestCase(TransactionTestCase):
    """
    Testcase for delete content management command
    """

    fixtures = ["content_test.json"]
    the_channel_id = "6199dde695db4ee4ab392222d5af1e5c"

    def test_include_all_nodes_all_deleted(self):
        ContentNode.objects.all().update(available=True)
        include_ids = list(
            ContentNode.objects.exclude(kind=content_kinds.TOPIC).values_list(
                "id", flat=True
            )
        )
        call_command("deletecontent", test_channel_id, node_ids=include_ids)
        self.assertEqual(ContentNode.objects.all().count(), 0)

    def test_include_all_nodes_other_channel_node_still_available(self):
        include_ids = list(
            ContentNode.objects.exclude(kind=content_kinds.TOPIC).values_list(
                "id", flat=True
            )
        )
        test = ContentNode.objects.filter(kind=content_kinds.VIDEO).first()
        original_id = test.id
        test.id = uuid.uuid4().hex
        test.channel_id = uuid.uuid4().hex
        test.available = True
        test.parent = None
        test.save()
        original = ContentNode.objects.get(id=original_id)
        for file in original.files.all():
            file.id = uuid.uuid4().hex
            file.contentnode = test
            file.supplementary = False
            file.save()
        call_command("deletecontent", test_channel_id, node_ids=include_ids)
        test.refresh_from_db()
        self.assertTrue(test.available)

    def test_include_all_nodes_force_delete_other_channel_node_not_available(self):
        include_ids = list(
            ContentNode.objects.exclude(kind=content_kinds.TOPIC).values_list(
                "id", flat=True
            )
        )
        test = ContentNode.objects.filter(kind=content_kinds.VIDEO).first()
        original_id = test.id
        test.id = uuid.uuid4().hex
        test.channel_id = uuid.uuid4().hex
        test.available = True
        test.parent = None
        test.save()
        original = ContentNode.objects.get(id=original_id)
        for file in original.files.all():
            file.id = uuid.uuid4().hex
            file.contentnode = test
            file.supplementary = False
            file.save()
        call_command(
            "deletecontent", test_channel_id, node_ids=include_ids, force_delete=True
        )
        test.refresh_from_db()
        self.assertFalse(test.available)

    def test_exclude_all_nodes_force_delete_other_channel_node_not_available_no_delete(self):
        exclude_ids = list(
            ContentNode.objects.exclude(kind=content_kinds.TOPIC).values_list(
                "id", flat=True
            )
        )
        test = ContentNode.objects.filter(kind=content_kinds.VIDEO).first()
        original_id = test.id
        test.id = uuid.uuid4().hex
        test.channel_id = uuid.uuid4().hex
        test.available = False
        test.parent = None
        test.save()
        original = ContentNode.objects.get(id=original_id)
        for file in original.files.all():
            file.id = uuid.uuid4().hex
            file.contentnode = test
            file.supplementary = False
            file.save()
        call_command(
            "deletecontent",
            test_channel_id,
            exclude_node_ids=exclude_ids,
            force_delete=True,
        )
        try:
            original = ContentNode.objects.get(id=original_id)
            self.assertTrue(original.available)
        except ContentNode.DoesNotExist:
            self.fail("Content node has been deleted")

    @patch("kolibri.core.content.management.commands.deletecontent.clear_channel_stats")
    def test_deleting_channel_clears_stats_cache(self, channel_stats_clear_mock):
        ContentNode.objects.all().update(available=True)
        include_ids = list(
            ContentNode.objects.exclude(kind=content_kinds.TOPIC).values_list(
                "id", flat=True
            )
        )
        self.assertFalse(channel_stats_clear_mock.called)
        call_command("deletecontent", test_channel_id, node_ids=include_ids)
        self.assertTrue(channel_stats_clear_mock.called)

    def tearDown(self):
        call_command("flush", interactive=False)
        super(DeleteContentTestCase, self).tearDown()
