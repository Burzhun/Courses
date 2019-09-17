Использование медиаплеера в процессе разработки
===============================================

Созданние плеера с помощью VideoField и https://github.com/clappr/clappr


Необходимые компоненты
----------------------
В системе должен быть установлен ffmpeg c кодеком libx264.

На момент написание этой статьи в docker файле уже присутствовало всё что
нужно, поэтому, если вы работаете через контейнеры, ничего готовить не надо.

Использование
-------------

1. Добавьте в модель поле ``VideoField``

   .. code-block:: python

        from coursify.fields import VideoField
        ...
        class MyModel(models.Model):
            video = VideoField('видео', blank=True)


2. Подключите в шаблоне следующие зависимости:

   .. code-block:: html

      <script src="{% static 'vendor/mediaplayer/clappr/clappr.js' %}"></script>
      <script src="{% static 'vendor/mediaplayer/shaka-player/shaka-player.compiled.js' %}"></script>
      <script src="{% static 'vendor/mediaplayer/clappr/dash-shaka-playback.js' %}"></script>
      <script src="{% static 'vendor/mediaplayer/clappr/clappr-level-selector-plugin.min.js' %}"></script>

4. Инициализируйте прлеер:

   .. code-block:: html

       <script>
        document.addEventListener("DOMContentLoaded", function (e) {
          const manifestUri = "{{ object.video.mpd_url }}";
          window.player = new Clappr.Player({
            width: '100%',
            height: 'auto',
            source: manifestUri,
            poster: "{{ object.video.preview_url }}",
            plugins: [DashShakaPlayback, LevelSelector, Clappr.MediaControl, PlaybackRatePlugin],
            playbackRateConfig: {
              defaultValue: '1.0',
              options: [
                  {value: '0.5', label: '0.5x'},
                  {value: '1.0', label: '1x'},
                  {value: '1.5', label: '1.5x'},
                  {value: '2.0', label: '2x'},
              ]
            },
            shakaConfiguration: {
              enableAdaption: true,
              streaming: {
                rebufferingGoal: 15,
              }
            },
            levelSelectorConfig: {
              title: 'Разрешение',
              currentLevel: 2,
              labelCallback: function (playbackLevel, customLabel) {
                return playbackLevel.label;
              }
            },
            parentId: '#video-{{ object.id }}'
          });
        });
      </script>
