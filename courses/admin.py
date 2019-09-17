from django.contrib import admin

from .models import Course, Lesson


@admin.register(Course)
class CoursesAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'created_at')
    search_fields = ('name', 'course')
    prepopulated_fields = {'slug': ('name',)}
