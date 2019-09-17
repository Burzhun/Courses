from django.urls import path

from .views import CourseList, CourseDetail, LessonDetail

app_name = 'courses'

urlpatterns = [
    path('', CourseList.as_view(), name='course-list'),
    path('<slug:slug>/', CourseDetail.as_view(), name='course-detail'),
    path('<slug:course_slug>/<slug:slug>/', LessonDetail.as_view(), name='lesson-detail')
]
