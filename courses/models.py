import os

from django.db import models
from django.urls import reverse

from coursify.fields import VideoField


def lesson_video_upload_to(instance, filename):
    return os.path.join('courses', 'lessons', instance.slug, filename)


class Course(models.Model):
    name = models.CharField('название', max_length=100)
    slug = models.SlugField('ссылка', unique=True)
    description = models.TextField('описание', blank=True)

    created_at = models.DateTimeField('дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('courses:course-detail', args=[self.slug])


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', verbose_name='курс')
    name = models.CharField('название', max_length=100)
    slug = models.SlugField('ссылка')
    video = VideoField('видео', upload_to=lesson_video_upload_to, blank=True)
    content = models.TextField('контент', blank=True)

    created_at = models.DateTimeField('дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        unique_together = ('course', 'slug')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('courses:lesson-detail', args=[self.course.slug, self.slug])
