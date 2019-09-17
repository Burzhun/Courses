from django.test import TestCase
from django.urls import reverse

from .models import Course, Lesson


class CourseListViewTest(TestCase):
    fixtures = ['courses']

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('/courses/')
        self.assertEqual(resp.status_code, 200)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('courses:course-list'))
        self.assertEqual(resp.status_code, 200)

    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse('courses:course-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'courses/course_list.html')


class CourseDetailViewTest(TestCase):
    fixtures = ['courses']

    def setUp(self):
        self.object = Course.objects.first()

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('/courses/{}/'.format(self.object.slug))
        self.assertEqual(resp.status_code, 200)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('courses:course-detail', args=[self.object.slug]))
        self.assertEqual(resp.status_code, 200)

    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse('courses:course-detail', args=[self.object.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'courses/course_detail.html')


class LessonDetailViewTest(TestCase):
    fixtures = ['courses']

    def setUp(self):
        self.object = Lesson.objects.first()

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('/courses/{}/{}/'.format(self.object.course.slug, self.object.slug))
        self.assertEqual(resp.status_code, 200)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('courses:lesson-detail', args=[self.object.course.slug, self.object.slug]))
        self.assertEqual(resp.status_code, 200)

    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse('courses:lesson-detail', args=[self.object.course.slug, self.object.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'courses/lesson_detail.html')
