# Аудит ссылок на материалы олимпиад

Дополнение после браузерной проверки: оба URL Яндекс Учебника, отмеченные ниже как `broken/empty_html`, открывают интерактивные уроки после выполнения JavaScript (33 и 39 карточек). Это ложные отрицательные результаты HTTP-проверки. Подтверждение сохранено отдельно в `additional_material_browser_review_20260923.json`; исходные результаты автоматического аудита ниже не изменены. Прохождение заданий не запускалось.

Проверено: **2026-09-23T18:03:11+00:00**. Каталог: `research/additional_competitions_20260923.json`.
SHA-256 каталога: `e8783d865bcb310cc74f3eed1d39619670ed71b417c12e000b033937c7a3b94b`.

Проверка выполняет реальные GET-запросы с переходом по редиректам. URL проверяются один раз вне зависимости от числа использований; запросы к одному домену идут последовательно. Читается только начало ответа, достаточное для определения файла, пустой страницы, сообщения об ошибке или JavaScript-оболочки.

## Итог

- Записей материалов: **13**.
- Уникальных URL: **13**.
- Олимпиад с материалами: **12** из 12.
- Работают: **11** URL / **11** записей материалов.
- Сломаны: **2** URL / **2** записей материалов.
- Неоднозначны: **0** URL / **0** записей материалов.
- За счёт дедупликации не отправлено повторных GET: **0**.
- Время аудита: **2.72 с**.

`inconclusive` не означает, что ссылка сломана: сервер мог потребовать JavaScript, CAPTCHA или заблокировать автоматический клиент. Такие URL нельзя считать подтверждёнными без проверки в браузере.

## Требуют внимания

| Статус | HTTP | Использований | URL | Причина |
|---|---:|---:|---|---|
| broken | 200 | 1 | https://education.yandex.ru/classroom/public-lesson/85189580/run/ | HTML-страница практически не содержит текста или ссылок. |
| broken | 200 | 1 | https://education.yandex.ru/classroom/public-lesson/85189581/run/ | HTML-страница практически не содержит текста или ссылок. |

## Содержимое требует смысловой проверки

Все подтверждённые HTML-страницы имеют признаки материалов или олимпиады.

## Ссылки, общие для нескольких олимпиад

Нет URL, общих для трёх и более олимпиад.

## Все уникальные URL

| Статус | HTTP | Тип | Использований | URL | Результат |
|---|---:|---|---:|---|---|
| ok | 200 | text/html | 1 | https://cs.hse.ru/olymp-team-comp/materials | html_nonempty |
| ok | 200 | text/html | 1 | https://disk.yandex.ru/d/ld8BxyB3IFS1pQ | html_nonempty |
| broken | 200 | text/html | 1 | https://education.yandex.ru/classroom/public-lesson/85189580/run/ | empty_html |
| broken | 200 | text/html | 1 | https://education.yandex.ru/classroom/public-lesson/85189581/run/ | empty_html |
| ok | 200 | application/pdf | 1 | https://olympiads.mccme.ru/matboi/usl2024_10_11.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://olympiads.mccme.ru/matboi/usl2025_89.pdf | download_nonempty |
| ok | 200 | text/html | 1 | https://olympiads.mccme.ru/regata/20252026/reg10.htm | html_nonempty |
| ok | 200 | text/html | 1 | https://olympiads.mccme.ru/regata/20252026/reg11.htm | html_nonempty |
| ok | 200 | text/html | 1 | https://olympiads.mccme.ru/regata/20252026/reg7.htm | html_nonempty |
| ok | 200 | text/html | 1 | https://olympiads.mccme.ru/regata/20252026/reg8.htm | html_nonempty |
| ok | 200 | text/html | 1 | https://olympiads.mccme.ru/regata/20252026/reg9.htm | html_nonempty |
| ok | 200 | text/html | 1 | https://turmath.ru/kolm/archive.php | html_nonempty |
| ok | 200 | text/html | 1 | https://www.vkoshp.letovo.ru/archive | html_nonempty |
