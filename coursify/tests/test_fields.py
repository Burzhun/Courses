import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import Storage
from django.test import TestCase, override_settings

from courses.models import Lesson, Course
from ..fields import DashFilesNames


@override_settings(DASH_RUN_CONVERTATION_AT_ASYNC=False)
class VideoFieldTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(
            slug="abc")
        video_path = os.path.join(
            settings.BASE_DIR,
            "coursify",
            "tests",
            "assets",
            "video_field_test.mp4")

        (abs_dir_path, filename) = os.path.split(video_path)

        with open(video_path, "rb") as infile:
            _file = SimpleUploadedFile(filename, infile.read())
            lesson = Lesson.objects.create(
                course=course,
                video=_file
            )

    def test_is_created_mpd_manifest(self):
        storage = Lesson().video.storage
        lesson = Lesson.objects.first()
        self.assertTrue(
            storage.exists(lesson.video.mpd_file_name),
            "Не сгенерирован mpd файл манифеста для DASH")

    def test_is_created_chunks(self):
        storage = Lesson().video.storage
        expected_streams_count = 5
        expected_count_of_chunks_for_stream = 2

        lesson = Lesson.objects.first()

        dash_seg_name = DashFilesNames.dash_segments_mask(lesson.video.name)
        dash_seg_name_mask = dash_seg_name. \
            replace(r"\$RepresentationID\$", "{0}"). \
            replace(r"\$Number%05d\$", "{1}")

        for stream_id in range(expected_streams_count):
            chunks_count = 0
            for chunk_id in range(1, expected_count_of_chunks_for_stream + 1):
                chunk_name = dash_seg_name_mask.format(
                    stream_id,
                    str(chunk_id).zfill(5))
                if storage.exists(chunk_name):
                    chunks_count += 1

            self.assertEqual(chunks_count, expected_count_of_chunks_for_stream,
                             f"Неверное количество чанков для DASH потока №{stream_id}, "
                             f"ожидалось {expected_count_of_chunks_for_stream}, существует {chunks_count}")

    def test_is_created_dash_init_files(self):
        storage = Lesson().video.storage
        expected_count_of_stream_init = 5

        lesson = Lesson.objects.first()

        stream_init_name = DashFilesNames.dash_init_files_mask(lesson.video.name)
        stream_init_name_mask = stream_init_name.replace(r"\$RepresentationID\$", "{0}")

        stream_init_files_count = 0
        for stream_id in range(expected_count_of_stream_init):
            init_name = stream_init_name_mask.format(stream_id)
            if storage.exists(init_name):
                stream_init_files_count += 1

        self.assertEqual(stream_init_files_count, expected_count_of_stream_init,
                         f"Неверное количество файлов описания для DASH потоков"
                         f"ожидалось {expected_count_of_stream_init}, существует {stream_init_files_count}")

    def test_is_created_preview_image(self):
        storage = Lesson().video.storage
        lesson = Lesson.objects.first()
        image_preview = lesson.video.preview_image_name

        self.assertTrue(
            storage.exists(image_preview),
            "Отсутсвует изображение-превью для видеоплеера")

    def test_mpd_url(self):
        lesson = Lesson.objects.first()
        self.assertNotEqual(
            len(lesson.video.mpd_url), 0,
            "Отсутствует url для mpd манифеста")

    def test_preview_url(self):
        lesson = Lesson.objects.first()
        self.assertNotEqual(
            len(lesson.video.preview_url), 0,
            "Отсутствует url для превью видеоплеера")

    def test_video_name(self):
        lesson = Lesson.objects.first()
        self.assertNotEqual(
            len(lesson.video.video_name), 0,
            "Отсутствует имя видео файла")


@override_settings(DASH_RUN_CONVERTATION_AT_ASYNC=False)
class VideoFieldDestroyTest(TestCase):
    """тест на правильное удаление VideoField"""

    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(
            slug="abc")
        video_path = os.path.join(
            settings.BASE_DIR,
            "coursify",
            "tests",
            "assets",
            "video_field_test.mp4")

        (abs_dir_path, filename) = os.path.split(video_path)

        with open(video_path, "rb") as infile:
            _file = SimpleUploadedFile(filename, infile.read())
            Lesson.objects.create(
                course=course,
                video=_file
            )

    def test_is_destroy(self):
        lesson = Lesson.objects.last()
        storage = Lesson().video.storage
        video_name = lesson.video.name
        lesson.video.delete()
        self._check_is_init_files_deleted(video_name, storage)
        self._check_is_seg_files_deleted(video_name, storage)
        self._check_is_preview_files_deleted(video_name, storage)
        self._check_is_mpd_manifest_deleted(video_name, storage)

    def _check_is_init_files_deleted(self, video_name: str, storage: Storage):
        count_of_stream_init = 5

        stream_init_name = DashFilesNames.dash_init_files_mask(video_name)
        stream_init_name_mask = stream_init_name.replace(r"\$RepresentationID\$", "{0}")

        stream_init_files_checked = 0
        for stream_id in range(count_of_stream_init):
            init_name = stream_init_name_mask.format(stream_id)
            if not storage.exists(init_name):
                stream_init_files_checked += 1

        self.assertEqual(stream_init_files_checked, count_of_stream_init,
                         f"Удаляются не все DASH потоки. "
                         f"Не удалилось {count_of_stream_init - stream_init_files_checked} потоков")

    def _check_is_seg_files_deleted(self, video_name, storage):
        streams_count = 5
        count_of_chunks_for_stream = 2

        dash_seg_name = DashFilesNames.dash_segments_mask(video_name)
        dash_seg_name_mask = dash_seg_name. \
            replace(r"\$RepresentationID\$", "{0}"). \
            replace(r"\$Number%05d\$", "{1}")
        for stream_id in range(streams_count):
            chunks_count = 0
            for chunk_id in range(1, count_of_chunks_for_stream + 1):
                chunk_name = dash_seg_name_mask.format(
                    stream_id,
                    str(chunk_id).zfill(5))
                if not storage.exists(chunk_name):
                    chunks_count += 1

            self.assertEqual(chunks_count, count_of_chunks_for_stream,
                             f"Удаляются не все сегменты для потока №{stream_id}, "
                             f"Не удалилось {count_of_chunks_for_stream - chunks_count} чанков")

    def _check_is_preview_files_deleted(self, video_name, storage):
        image_preview = DashFilesNames.preview_image_name(video_name)

        self.assertFalse(
            storage.exists(image_preview),
            "Не удаляется изображение-превью для видеоплеера")

    def _check_is_mpd_manifest_deleted(self, video_name, storage):
        self.assertFalse(
            storage.exists(video_name),
            "Не удаляется mpd файл манифеста для DASH")
