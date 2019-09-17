import io
import tempfile
import subprocess
import os
import datetime
import posixpath
from django.conf import settings
from django.db.models.fields.files import FieldFile
from django.core.files.storage import Storage
from django.core.files.storage import default_storage

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open('/dev/null', 'w')

from django import forms
from django.core import checks
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .dash import DashFilesNames, DashVideoManager
from .tasks import generate_dash_manifest


class VideoFormField(forms.FileField):
    default_error_messages = {
        'invalid_video': _(
            'Upload a valid video. The file you uploaded was either not an '
            'video or a corrupted video.'
        )
    }

    def to_python(self, data):
        f = super(VideoFormField, self).to_python(data)

        if f is None:
            return None

        if hasattr(data, 'temporary_file_path'):
            input_file = data.temporary_file_path()
        else:
            if hasattr(data, 'read'):
                content = data.read()
            else:
                content = data['content']

            fd, input_file = tempfile.mkstemp()

            with io.open(fd, 'w') as f:  # this works on Python 2?
                f.write(str(content))

        # tries to open the video file with ffmpeg to check his integrity
        exit_code = subprocess.call([
            'ffmpeg',
            '-v', 'quiet',  # don't print messages
            '-i', input_file,  # input file
            '-f', 'null',  # format is null because we don't really want to convert anything
            '-'  # output to nowhere
        ], stdout=DEVNULL, stderr=DEVNULL)

        # TODO: if file is an image ffmpeg dont exit with error code
        # we should use ffprobe and analyze the output too

        if not exit_code == 0:
            raise forms.ValidationError(
                self.error_messages['invalid_video'],
                code='invalid_video'
            )

        if hasattr(f, 'seek') and callable(f.seek):
            f.seek(0)

        return f


class FieldVideo(FieldFile):
    """объект доступный как поле объекта VideoField.
    Все эти поля доступны для работы в темплейтах"""

    @property
    def video_name(self) -> str:
        """ Название видео. Гарантируется, что оно уникально для всех видео
        и его можно использовать как id для шаблонов"""
        return DashFilesNames.get_video_name(self.name)

    @property
    def mpd_url(self) -> str:
        """url путь к файлу mpd. mpd файл содержит информацию
        обо всех остальных частях dash файлов"""
        return self.storage.url(DashFilesNames.mpd_manifest_name(self.name))

    @property
    def preview_url(self) -> str:
        """url путь к превью-изображению видео"""
        return self.storage.url(DashFilesNames.preview_image_name(self.name))

    @property
    def preview_image_name(self) -> str:
        """название превью-изображения"""
        return DashFilesNames.preview_image_name(self.name)

    @property
    def mpd_file_name(self) -> str:
        """название mpd манифеста."""
        return DashFilesNames.mpd_manifest_name(self.name)

    def delete(self, save=True):
        file_name = self.name
        storage = self.storage
        super().delete(save)
        dash = DashVideoManager(file_name, storage)
        dash.destroy()
    delete.alters_data = True


class VideoField(models.FileField):
    description = _('Video')
    async_dash_gen_result = None
    attr_class = FieldVideo

    def __init__(self, *args, **kwargs):
        self.width_field = kwargs.pop('width_field', None)
        self.height_field = kwargs.pop('height_field', None)
        self.duration_field = kwargs.pop('duration_field', None)
        self.size_field = kwargs.pop('size_field', None)
        self.thumbnail_field = kwargs.pop('thumbnail_field', None)

        super(VideoField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super(VideoField, self).check(**kwargs)
        errors.extend(self._check_ffmpeg_installed())
        return errors

    def _check_ffmpeg_installed(self):
        exit_code = subprocess.call(['which', 'ffmpeg'], stdout=DEVNULL)

        if not exit_code == 0:
            return [
                checks.Error(
                    'Cannot use VideoField because ffmpeg is not installed.',
                    hint='Get ffmpeg at https://ffmpeg.org/download.html',
                    obj=self,
                    id='videofield.E001',
                )
            ]
        return []

    def deconstruct(self):
        name, path, args, kwargs = super(VideoField, self).deconstruct()

        if self.width_field:
            kwargs['width_field'] = self.width_field
        if self.height_field:
            kwargs['height_field'] = self.height_field
        if self.duration_field:
            kwargs['duration_field'] = self.duration_field
        if self.size_field:
            kwargs['size_field'] = self.size_field
        if self.thumbnail_field:
            kwargs['thumbnail_field'] = self.thumbnail_field

        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {'form_class': VideoFormField}
        defaults.update(kwargs)
        return super(VideoField, self).formfield(**defaults)

    def pre_save(self, model_instance, add):
        file = super().pre_save(model_instance, add)
        if file:
            self.gen_dash(file.name)
        return file

    def gen_dash(self, file_name: str):
        if settings.DASH_RUN_CONVERTATION_AT_ASYNC:
            generate_dash_manifest.apply_async(args=[file_name])
        else:
            dash = DashVideoManager(file_name, default_storage)
            dash.generate()

    def get_storage_object(self) -> Storage:
        return self.storage

    def generate_filename(self, instance, filename):
        if callable(self.upload_to):
            filename = self.upload_to(instance, filename)
        else:
            dirname = datetime.datetime.now().strftime(self.upload_to)
            filename = posixpath.join(dirname, filename)

        return self.gen_uniq_filename(filename)

    def gen_uniq_filename(self, video_name: str) -> str:
        """генерирует уникальное имя файла

        Для которого будет уникальной версия имени с расширением mpd"""

        _, ext = os.path.splitext(video_name)
        mpd_file_name = DashFilesNames.mpd_manifest_name(video_name)
        gen_mpd_name = self.storage.generate_filename(mpd_file_name)
        gen_name, _ = os.path.splitext(gen_mpd_name)
        return gen_name + ext
