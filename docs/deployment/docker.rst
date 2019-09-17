Использование Docker для процесса эксплуатации
==============================================

Отличия от использования :doc:`../development/docker` только в том, что для процесса эксплуатации нужно использовать дополнительный файл ``docker-compose.production.yml``

.. code-block:: bash

    $ docker-compose -f docker-compose.yml -f docker-compose.production.yml up
