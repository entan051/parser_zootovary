# Парсер zootovary.ru
## Тестовое задание


   Данный парсер является тестовым заданием.
   Ниже будут приведенны комментарии к реализации и обоснования к ВОЗМОЖНЫМ изменениям для повышения производительности.

## Комментарии к реализации

  К указанному в документе стеку были добавлены только модули идущие вместе с актуальной версией языка.

  Комментариев по коду оставленно не будет, потому что как мне кажется того описания, что я оставил около объявления каждого из классов с головой достаточно.
  
  Были выполнены все требования описанные в ТЗ, если что-то было упущенно это было сделанно лишь из-за невнимательности или неверной трактовки ТЗ. Приношу извинения - готов переделать.
  
  Код не идеален, хоть я и стремился к этому. Также код был написан в соответствии с SOLID и PEP-8.
  
  Насколько хорошо была выполнена работа - судить Вам.
  
  К предпоследнему коммиту прикрепленны логи и выходные .csv файлы, которые получились после работы парсера.
  Время за которое спарсился весь сайт - 10789.8 сек. или 2 часа 59 минут 49 секунд.
  Время на выполнение ТЗ ~ 8 часов

## Возможные улучшения

  Асинхронный парсер... Первое бы что я сделал ушел бы от синхронной реализации, которую как я понял вы хотели увидеть в ТЗ и сделал бы асинхронный вариант.
  
  selectolax на замену BeautifulSoup4... bs4 хороший обработчик, он стабильный и у него огромное разнообразие методов, но selectolax несравнимо быстрее в тех же самых задачах. Это подтверждают и огромное кол-во бенчмарков в интернете и мой личный опыт. Я всегда делаю скидку на ошибку и готов к обсуждению, но моя точка зрения на данный момент такая.
  
  Запись данных не в csv... Понятное дело, чтобы не усложнять и так не увесистое ТЗ вы решили отказаться от просьбы воспользоваться СУБД (н-р PostgreSQL) или каким нибудь распределенной БД, вроде Kafka. Однако хранение и главное запись производилась бы быстрее НЕ в .csv
  
  Остальное зависит от нюансов архитектуры и машины. Выше перечисленно основное.
  
  Вместо подписи  ✨Magic ✨