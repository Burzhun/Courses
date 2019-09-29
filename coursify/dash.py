import os
import tempfile
import subprocess
import shutil
import glob

from django.core import checks
from django.core.files.storage import Storage


class DashFilesNames:
    """
    Существует для получения из названия оригинального файла
    все другие названия или маски названий. Помимо просто названия
    оригинального файла, может принимать и путь к нему: методы сами вытащат
    из неё название файла.

    ВНИМАНИЕ: методы этого класса не отвечают за пути к директориям,
    где хранятся файлы, методы возвращают только лишь названия объектов DASH.
    """

    @classmethod
    def mpd_manifest_name(cls, video_name: str) -> str:
        """Возвращает название файла манифеста"""

        filename = cls.get_video_name(video_name)
        return filename + ".mpd"

    @classmethod
    def dash_segments_mask(cls, video_name: str) -> str:
        """ Генерирует маску названий для segmentation файлов (чанки) по названию оригинального видео.

        Создаёт маску для названий seg файлов. При генерации
        на место подстроки \$RepresentationID\$ будет подставляться
        номер потока, а на место \$Number%05d\$ номер чанка в потоке,
        причём дополненная спереди нулями до пяти символов.

        :param video_name: название оригинального видео файла
        :return: маска для названий chunk файлов
        """
        filename = cls.get_video_name(video_name)
        return f'{filename}-chunk-stream\$RepresentationID\$-\$Number%05d\$.m4s'

    @classmethod
    def dash_init_files_mask(cls, video_name: str) -> str:
        """ Генерирует маску init файлов по названию оригинального видео.

        Создаёт маску для названий init файлов. При генерации
        на место подстроки \$RepresentationID\$ будет подставляться
        номер потока.

        :param video_name: название оригинального видео файла
        :return: маска для названий init файлов
        """
        filename = cls.get_video_name(video_name)
        return f"{filename}-init-stream\$RepresentationID\$.m4s"

    @classmethod
    def preview_image_name(cls, video_name: str) -> str:
        """Возвращает название файла preview из названия видео"
        :param video_name:
        :return: название файла preview
        """
        filename = cls.get_video_name(video_name)
        return filename + ".jpg"

    @classmethod
    def get_video_name(cls, video_name: str) -> str:
        filename, ext = os.path.splitext(video_name)
        return filename


class DashVideoManager:
    """ Класс для работы с файлами стримингово формата DASH.

    Для инициализации класса требуется название оригинального видео
    и класс storage, в котором хранится оригинал и должны хранится
    произовдные файлы.

    DASH формат в сумме состоит из 3 типов файлов:

    1) mpd манифест, в котором описаны все доступные потоки и где хранятся
    файлы инициализации потоков.

    2) файлы инициализаии потоков (в коде отмечены как init файлы) -
    файлы в которых описаны где хранятся чанки потоков и для каких промежутков времени
    они созданы. Каждый поток это доступные разрешения для видео
    (360, 480, 720 и т.п.) и обычно один аудио поток.

    3) файлы чанков (в коде отмечены как chunk файлы) - файлы, в которых непосредственно
    кодируется определённый промежуток потока. На момент написания этого комментария,
    это было около 2-3 секнуд в каждом чанке.
    """

    TEMP_DIR_PREFIX = "dash_video_"

    def __init__(self: object, file_name: str, storage: Storage):
        self.file_name = file_name
        self.storage = storage
        self.temp_video_file = None
        self.temp_dir = None

    def __del__(self):
        if self.temp_video_file is not None \
                and os.path.exists(self.temp_video_file.name):
            os.remove(self.temp_video_file.name)

    def generate(self):
        """Генерирует все компоненты для dash и удалет оригинальное видео"""
        self._create_temp_video_file()
        self._generate_dash()
        self._generate_preview()
        self._save_generated_files()

    def destroy(self):
        """Удаляет все компоненты dash этого видео"""
        self._remove_mpd_manifest()
        self._remove_preview_image()
        init_files_count = self._remove_init_files()
        self._remove_seg_files(init_files_count)

    def _remove_mpd_manifest(self):
        mpd_file_name = DashFilesNames.mpd_manifest_name(self.file_name)
        self.storage.delete(mpd_file_name)

    def _remove_preview_image(self):
        preview_image = DashFilesNames.preview_image_name(self.file_name)
        self.storage.delete(preview_image)

    def _remove_init_files(self):
        """удаляет все файлы описания потоков"""
        stream_init_name = DashFilesNames.dash_init_files_mask(self.file_name)
        stream_init_name_mask = stream_init_name.replace(r"\$RepresentationID\$", "{0}")

        stream_id = 0

        while True:
            init_name = stream_init_name_mask.format(stream_id)
            if not self.storage.exists(init_name):
                break
            self.storage.delete(init_name)
            stream_id += 1
        return stream_id

    def _remove_seg_files(self, init_files_count):
        """удаляет все чанки для потоков с номерами от 0 до init_files_count"""

        dash_seg_name = DashFilesNames.dash_segments_mask(self.file_name)
        dash_seg_name_mask = dash_seg_name. \
            replace(r"\$RepresentationID\$", "{0}"). \
            replace(r"\$Number%05d\$", "{1}")

        # TODO: сделать на threads
        for stream_id in range(init_files_count):
            chunk_id = 1
            while True:
                chunk_name = dash_seg_name_mask.format(
                    stream_id,
                    str(chunk_id).zfill(5))
                if not self.storage.exists(chunk_name):
                    break
                self.storage.delete(chunk_name)
                chunk_id += 1

    def _create_temp_video_file(self):
        """создаёт временную директорию и переносит туда оригинал видео из storage,
        т.к. storage может хранить файлы не в файловой системе текущего хоста"""

        self.temp_dir = tempfile.TemporaryDirectory(
            prefix=self.TEMP_DIR_PREFIX)
        self.temp_video_file = tempfile.NamedTemporaryFile(
            dir=self.temp_dir.name,
            delete=False)
        video_file = self.storage.open(self.file_name, "rb")
        shutil.copyfileobj(video_file, self.temp_video_file.file)
        self.temp_video_file.file.close()

    def _generate_dash(self):
        """запускает генерацию всех компонентов dash формата и
        сохраняет все файлы во временную директорию"""

        result = subprocess.run(self._get_command_for_generate_dash(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                shell=True)

        if not result.returncode == 0:
            return [checks.Error('Cannot generate ffmpeg dash mpd manifest')]

    def _generate_preview(self):
        """генерирует preview изображение из видео
        на момент написания комментарии, берётся кадр из 1 секнуды видео"""

        video_file_name = self.temp_video_file.name
        preview = self._preview_file_path()
        result = subprocess.run(f"ffmpeg -i '{video_file_name}' -ss 00:00:01.000 -vframes 1 '{preview}'",
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                shell=True)
        if not result.returncode == 0:
            return [checks.Error('Cannot generate ffmpeg preview for video')]

    def _save_generated_files(self):
        """сохраняет mpd манифест, изображение-превью,
        а так же файлы инициализации потоков и сегменты потоков
        из временной директории в storage"""

        with open(self._mpd_file_path(), "rb") as mpd_tmp_file:
            mpd_manifest_name = DashFilesNames.mpd_manifest_name(self.file_name)
            mpd_storage_file = self.storage.open(
                mpd_manifest_name,
                "wb+")
            shutil.copyfileobj(mpd_tmp_file, mpd_storage_file)
            mpd_storage_file.close()

        with open(self._preview_file_path(), "rb") as preview_tmp_file:
            preview_image_name = DashFilesNames.preview_image_name(self.file_name)
            preview_storage_file = self.storage.open(
                preview_image_name,
                "wb+")
            shutil.copyfileobj(preview_tmp_file, preview_storage_file)
            preview_storage_file.close()

        self._save_init_files()

        self._save_seg_files()

    def _get_command_for_generate_dash(self):
        video_height = self._get_height_of_video()

        if video_height > 1070:
            return self._dash_command_gen_1080_and_less()
        elif video_height > 710:
            return self._dash_command_gen_720_and_less()
        else:
            return self._dash_command_gen_480_and_less()

    def _get_height_of_video(self):
        video_file_name = self.temp_video_file.name
        cmd_video_height = 'ffmpeg -i ' + video_file_name + \
                           r' 2>&1 | grep Video: | grep -Po "\d{3,5}x\d{3,5}" | cut -d"x" -f1'
              
        height = subprocess.check_output([cmd_video_height], shell=True)
        height_str = height.decode("utf-8", "strict")

        if len(height_str) == 0:
            raise ValueError("Value of the height video is empty")
        try:
            return int(height_str)
        except ValueError:
            raise ValueError(f"Unexpected type of video height value. Expected digits, got {height_str}")

    def _dash_command_gen_1080_and_less(self):
        """Создаёт команду для генерации dash контента на основе оригинального видео.
        Данная функция создаёт потоки в 1080, 720, 480, 360px.

        Описание генерируемой команды:
        -i {адрес входного файла}

        -map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:a:0 - дублируем
            входной поток на 4 видео потока (v) и 1 аудио (a)

        -b:v:3 5000k -filter:v:3 "scale=-2:1080" -profile:v:3 high -
            берем 3 видео поток, устанавливаем битрейт в 5000 кб/c
            сжимаем до высоты в 1080 пикселей и уставливаем профиль кодирования
            в hight. Все остальные потоки на подобии этому

        -chunk_duration_ms 2000 средняя длина чанка в мс
        -time_shift_buffer_depth 4000 время забуфферизированного видео
            до начала воспроизведения плеером видео
        """
        return f'ffmpeg -i {self.temp_video_file.name} \
-map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:a:0 \
-c:a aac -b:a 128k \
-c:v libx264 -x264opts "keyint=24:min-keyint=24:no-scenecut" -r 24 \
-bf 1 -b_strategy 0 -sc_threshold 0 -pix_fmt yuv420p \
-b:v:3 5000k -filter:v:3 "scale=-2:1080" -profile:v:3 high \
-b:v:2 1800k -filter:v:2 "scale=-2:720" -profile:v:2 main \
-b:v:1 700k -filter:v:1 "scale=-2:480" -profile:v:1 main \
-b:v:0 450k -filter:v:0 "scale=-2:360" -profile:v:0 baseline \
-chunk_start_index 1 \
-chunk_duration_ms 2000 \
-time_shift_buffer_depth 4000 \
-minimum_update_period 4000 \
-use_timeline 1 \
-use_template 1 \
-f dash \
-init_seg_name {self._init_file_name_mask()} \
-media_seg_name {self._seg_file_name_mask()} \
{self._mpd_file_path()}'

    def _dash_command_gen_720_and_less(self):
        """Создаёт команду для генерации dash контента на основе оригинального видео.
        Данная функция создаёт потоки в 720, 480, 360px.

        Описание генерируемой команды:
        -i {адрес входного файла}

        -map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:a:0 - дублируем
            входной поток на 4 видео потока (v) и 1 аудио

        -b:v:3 5000k -filter:v:3 "scale=-2:1080" -profile:v:3 high -
            берем 3 видео поток, устанавливаем битрейт в 5000 кб/c
            сжимаем до высоты в 1080 пикселей и уставливаем профиль кодирования
            в hight. Все остальные потоки на подобии этому

        -chunk_duration_ms 2000 средняя длина чанка в мс
        -time_shift_buffer_depth 4000 время забуфферизированного видео
            до начала воспроизведения плеером видео
        """
        return f'ffmpeg -i {self.temp_video_file.name} \
-map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:a:0 \
-c:a aac -b:a 128k \
-c:v libx264 -x264opts "keyint=24:min-keyint=24:no-scenecut" -r 24 \
-bf 1 -b_strategy 0 -sc_threshold 0 -pix_fmt yuv420p \
-b:v:2 1800k -filter:v:2 "scale=-2:720" -profile:v:2 main \
-b:v:1 700k -filter:v:1 "scale=-2:480" -profile:v:1 main \
-b:v:0 450k -filter:v:0 "scale=-2:360" -profile:v:0 baseline \
-chunk_start_index 1 \
-chunk_duration_ms 2000 \
-time_shift_buffer_depth 4000 \
-minimum_update_period 4000 \
-use_timeline 1 \
-use_template 1 \
-f dash \
-adaptation_sets "id=0,streams=0,1,2 id=1,streams=3" \
-init_seg_name {self._init_file_name_mask()} \
-media_seg_name {self._seg_file_name_mask()} \
{self._mpd_file_path()} '

    def _dash_command_gen_480_and_less(self):
        """Создаёт команду для генерации dash контента на основе оригинального видео.
        Данная функция создаёт потоки в 480, 360px.

        Описание генерируемой команды:
        -i {адрес входного файла}

        -map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:a:0 - дублируем
            входной поток на 4 видео потока (v) и 1 аудио

        -b:v:3 5000k -filter:v:3 "scale=-2:1080" -profile:v:3 high -
            берем 3 видео поток, устанавливаем битрейт в 5000 кб/c
            сжимаем до высоты в 1080 пикселей и уставливаем профиль кодирования
            в hight. Все остальные потоки на подобии этому

        -chunk_duration_ms 2000 средняя длина чанка в мс
        -time_shift_buffer_depth 4000 время забуфферизированного видео
            до начала воспроизведения плеером видео
        """
        return f'ffmpeg -i {self.temp_video_file.name} \
-map 0:v:0 -map 0:v:0 -map 0:a:0 \
-c:a aac -b:a 128k \
-c:v libx264 -x264opts "keyint=24:min-keyint=24:no-scenecut" -r 24 \
-bf 1 -b_strategy 0 -sc_threshold 0 -pix_fmt yuv420p \
-b:v:1 700k -filter:v:1 "scale=-2:480" -profile:v:1 main \
-b:v:0 450k -filter:v:0 "scale=-2:360" -profile:v:0 baseline \
-chunk_start_index 1 \
-chunk_duration_ms 2000 \
-time_shift_buffer_depth 4000 \
-minimum_update_period 4000 \
-use_timeline 1 \
-use_template 1 \
-f dash \
-adaptation_sets "id=0,streams=0,1 id=1,streams=3" \
-init_seg_name {self._init_file_name_mask()} \
-media_seg_name {self._seg_file_name_mask()} \
{self._mpd_file_path()} '

    def _save_init_files(self):
        """сохраняет сгенерированные init файлы из временной директории в storage"""
        dash_init_name = self._init_file_name_mask()
        dash_init_name_mask = dash_init_name. \
            replace(r"\$RepresentationID\$", "*"). \
            replace("\$Number%05d\$", "*")

        inits_filepath_list = glob.glob(
            os.path.join(self.temp_dir.name, dash_init_name_mask))

        for init_path in inits_filepath_list:
            init_name = os.path.basename(init_path)
            with open(init_path, "rb") as init_tmp_file:
                init_storage_file = self.storage.open(
                    os.path.join(os.path.dirname(self.file_name), init_name),
                    "wb+"
                )
                shutil.copyfileobj(init_tmp_file, init_storage_file)
                init_storage_file.close()

    def _save_seg_files(self):
        """
        сохраняет сгенерированные seg файлы из временной директории в storage
        """
        dash_seg_name = self._seg_file_name_mask()
        dash_seg_name_mask = dash_seg_name. \
            replace(r"\$RepresentationID\$", "*"). \
            replace("\$Number%05d\$", "*")

        segs_filepath_list = glob.glob(
            os.path.join(self.temp_dir.name, dash_seg_name_mask))

        for seg_path in segs_filepath_list:
            seg_name = os.path.basename(seg_path)
            with open(seg_path, "rb") as seg_tmp_file:
                seg_storage_file = self.storage.open(
                    os.path.join(os.path.dirname(self.file_name), seg_name),
                    "wb+")
                shutil.copyfileobj(seg_tmp_file, seg_storage_file)
                seg_storage_file.close()

    def _mpd_file_path(self):
        """возвращает путь временного mpd файла в файловой системе"""
        mpd_file_name = DashFilesNames.mpd_manifest_name(self.file_name)

        return os.path.join(self.temp_dir.name, os.path.basename(mpd_file_name))

    def _preview_file_path(self):
        """возвращает путь временного preview файла в файловой системе"""
        preview_file_name = DashFilesNames.preview_image_name(self.file_name)
        return os.path.join(self.temp_dir.name, os.path.basename(preview_file_name))

    def _seg_file_name_mask(self):
        path = DashFilesNames.dash_segments_mask(self.file_name)
        return os.path.basename(path)

    def _init_file_name_mask(self):
        path = DashFilesNames.dash_init_files_mask(self.file_name)
        return os.path.basename(path)
