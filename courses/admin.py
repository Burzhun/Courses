from django.contrib import admin
from django.urls import path
from .models import Course, Lesson
from django.http import HttpResponse
from os.path import join,isdir
from os import mkdir
from coursify import settings
from django.core.files.base import ContentFile
import shutil

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
    change_form_template = 'admin/lesson/change_form.html'

    def get_urls(self):
        urls = super(LessonAdmin,self).get_urls()
        custom_urls = [
            path('upload_video/<int:lesson_id>/',self.admin_site.admin_view(self.upload_video))
        ]
        return custom_urls + urls

    #Загрузка видео
    def upload_video(self,request,lesson_id):
        lesson = Lesson.objects.get(pk=lesson_id)
        contest_range = request.headers['Content-Range'].replace('bytes','').split('/')
        start,end = contest_range[0].split('-')
        path = join(settings.MEDIA_ROOT, 'videos', 'lesson_id'+str(lesson_id), 'video.mp4')
        if not isdir(join(settings.MEDIA_ROOT, 'videos')):
            mkdir(join(settings.MEDIA_ROOT, 'videos'))
        if not isdir(join(settings.MEDIA_ROOT, 'videos', 'lesson_id'+str(lesson_id))):           
            mkdir(join(settings.MEDIA_ROOT, 'videos', 'lesson_id'+str(lesson_id)))
        
        if(int(start)==0):
            # Создаем новый файл для первого запроса
            f = open(path, "wb+")            
        else:
            # Дополняем файл для последующих запросов
            f = open(path, "ab+")
        request_file = request.FILES['video']
        for chunk in request_file.chunks():
            f.write(chunk)              
        f.close()
        length = int(contest_range[1])
        if(int(end)+1==length):
            #Если закончили сохранение запись файла, то записываем его в модель
            with ContentFile(open(path, "rb+").read()) as     file_content:
                file_path = join('videos', 'lesson_id'+str(lesson_id), 'video.mp4')
                lesson.video.save(file_path, file_content)
                # Save the article
                lesson.save()
                shutil.rmtree(join(settings.MEDIA_ROOT, 'videos', 'lesson_id'+str(lesson_id)), ignore_errors=True)
            return HttpResponse('end')
        return HttpResponse(int(int(end)*100/length))
