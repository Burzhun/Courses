from django.views.generic import ListView, DetailView

from .models import Course, Lesson


class CourseList(ListView):
    model = Course


class CourseDetail(DetailView):
    model = Course


class LessonDetail(DetailView):
    model = Lesson

    def get_queryset(self):
        queryset = super().get_queryset()
        course_slug = self.kwargs.get('course_slug')
        if course_slug:
            queryset = queryset.filter(course__slug=course_slug)
        return queryset
