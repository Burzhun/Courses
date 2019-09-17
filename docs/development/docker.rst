Использование Docker в процессе разработки
==========================================

Использование Docker для создания программного обеспечения позволяет запускать и тестировать код, не беспокоясь о внешних зависимостях, таких как серверы кэша и базы данных.



Необходимые компоненты
----------------------

Вам нужно будет установить `Docker <https://docs.docker.com/install/>`_ и `docker-compose <https://docs.docker.com/compose/install/>`_ перед выполнением следующих шагов.

.. note::

   В нашей конфигурации используется `docker-compose.override.yml <https://docs.docker.com/compose/extends/#understanding-multiple-compose-files>`_ который предоставляет запуск через python manage.py runserver для локальной разработки.


Использование
-------------

1. Сборка контейнеров с помощью ``docker-compose``

   .. code-block:: bash

    $ docker-compose build


2. Подготовьте базу данных

   .. code-block:: bash

    $ docker-compose run --rm web python manage.py migrate
    $ docker-compose run --rm web python manage.py collectstatic


3. Запустить контейнеры

   .. code-block:: bash

    $ docker-compose up

По умолчанию приложение запускается в режиме отладки и настроено на прослушивание через порт ``80``.


4. Запуск команд внутри контейнера

    Просто используйте следующий формат:

    .. code:: text

      docker-compose run --rm {service_name} {command}


    Например, чтобы открыть оболочку Django, вам нужно запустить это:

    .. code:: text

      docker-compose run --rm web python manage.py shell
