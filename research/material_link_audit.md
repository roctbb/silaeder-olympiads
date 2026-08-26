# Аудит ссылок на материалы олимпиад

Проверено: **2026-08-26T19:41:26+00:00**. Каталог: `data/seed/catalog.json`.
SHA-256 каталога: `28fa1d02b5cdd3a96ed7a98753740e21267d1ba32e5e9bac6c80f49f0068f6b5`.

Проверка выполняет реальные GET-запросы с переходом по редиректам. URL проверяются один раз вне зависимости от числа использований; запросы к одному домену идут последовательно. Читается только начало ответа, достаточное для определения файла, пустой страницы, сообщения об ошибке или JavaScript-оболочки.

## Итог

- Записей материалов: **480**.
- Уникальных URL: **291**.
- Олимпиад с материалами: **363** из 363.
- Работают: **291** URL / **480** записей материалов.
- Сломаны: **0** URL / **0** записей материалов.
- Неоднозначны: **0** URL / **0** записей материалов.
- За счёт дедупликации не отправлено повторных GET: **189**.
- Время аудита: **87.19 с**.

`inconclusive` не означает, что ссылка сломана: сервер мог потребовать JavaScript, CAPTCHA или заблокировать автоматический клиент. Такие URL нельзя считать подтверждёнными без проверки в браузере.

## Требуют внимания

Сломанных или неоднозначных ссылок не обнаружено.

## Содержимое требует смысловой проверки

Все подтверждённые HTML-страницы имеют признаки материалов или олимпиады.

## Ссылки, общие для нескольких олимпиад

Высокое число использований не является сетевой ошибкой, но помогает найти слишком общие архивы, которые стоит заменить профильными страницами.

| Олимпиад | Записей | URL |
|---:|---:|---|
| 6 | 6 | https://bibn.unn.ru/preparation.html |
| 4 | 4 | https://dovuz.sfu.ru/abiturientu-sfu/olimpiady/belchonok/arkhiv/ |
| 6 | 6 | https://dovuz.urfu.ru/olymps/izumrud/tasks |
| 6 | 6 | https://info.abiturient.tsu.ru/ru/content/answers-ORMO |
| 8 | 8 | https://malun.kpfu.ru/mpoarh |
| 3 | 3 | https://mospolytech.ru/postupayushchim/olimpiady/olimpiada-iskusstvo-grafiki/ |
| 21 | 21 | https://ntcontest.ru/books/ |
| 7 | 7 | https://olymp.bmstu.ru/ru/variants |
| 7 | 7 | https://olymp.mipt.ru/olympiad/samples |
| 27 | 27 | https://olymp.msu.ru/rus/page/main/29/page/zadaniya-olimpiady-proshlyh-let |
| 4 | 4 | https://olymp.tsput.ru/materials/ |
| 21 | 21 | https://olympiada.spbu.ru/arkhiv.html |
| 21 | 21 | https://olympiada.spbu.ru/podgotovka.html |
| 3 | 3 | https://pro.firpo.ru/meropriyatiya/itogi/itogi2026/ |
| 4 | 4 | https://prodcontest.com/materials/ |
| 8 | 8 | https://pvg.mk.ru/archive/2024-2025/ |
| 8 | 8 | https://pvg.mk.ru/archive/archive/ |
| 4 | 4 | https://vserosolimp.edsoo.ru/informatic |
| 4 | 4 | https://vso.edsoo.ru/public.php/dav/files/ywgpTXZJfX4RWE2/?accept=zip |
| 5 | 5 | https://www.fa.ru/for-applicants/olympiads/mission/examples/ |
| 5 | 5 | https://www.fa.ru/for-applicants/olympiads/mission/materials/ |
| 3 | 3 | https://www.pguas.ru/tatlin |
| 7 | 7 | https://www.ranepa.ru/olymp/arkhiv-zadaniy/ |
| 5 | 5 | https://www.rsuh.ru/education/cdo/olimpiada-rggu-dlya-shkolnikov.php |
| 8 | 8 | https://xn--k1acfgjg.xn--l1afu.xn--p1ai/archives/%D0%B7%D0%B0%D0%B4%D0%B0%D0%BD%D0%B8%D1%8F/ |

## Все уникальные URL

| Статус | HTTP | Тип | Использований | URL | Результат |
|---|---:|---|---:|---|---|
| ok | 200 | application/pdf | 1 | http://academy.fsb.ru/upload/iblock/a77/pb6cpyv2bnrln4f8dfaqgsuu0l9r723u.pdf | download_nonempty |
| ok | 200 | text/html | 1 | http://school.astro.spbu.ru/?q=node/678 | html_nonempty |
| ok | 200 | text/html | 1 | http://www.pdmi.ras.ru/~olymp/ | html_nonempty |
| ok | 200 | text/html | 1 | https://abilympics-russia.ru/competencies/Komp2026/?type=5 | html_nonempty |
| ok | 200 | text/html | 1 | https://ai.edu.gov.ru/materials | html_nonempty |
| ok | 200 | text/html | 1 | https://artmasters.ru/junior | html_nonempty |
| ok | 200 | text/html | 6 | https://bibn.unn.ru/preparation.html | html_nonempty |
| ok | 200 | text/html | 1 | https://chvt.ru/ | html_nonempty |
| ok | 200 | text/html | 1 | https://cloud.mail.ru/public/8T3Q/9BJxCpvZT | public_file_verified |
| ok | 200 | text/html | 1 | https://cloud.mail.ru/public/TTr7/4LpPLVKqn | public_file_verified |
| ok | 200 | text/html | 1 | https://dano.hse.ru/demo | html_nonempty |
| ok | 200 | text/html | 1 | https://dano.hse.ru/library/past_tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://dano.hse.ru/library/task | html_nonempty |
| ok | 200 | text/html | 1 | https://disk.360.yandex.ru/d/bP7LfOrVlE3khg | html_nonempty |
| ok | 200 | text/html | 1 | https://disk.yandex.ru/d/mo0W3HNQAh3X3A | html_nonempty |
| ok | 200 | text/html | 1 | https://distolymp2.spbu.ru/olymp/index_learn.html | html_nonempty |
| ok | 200 | text/html | 1 | https://dovuz.innopolis.university/pre-olympiads/innopolis-open/ai | html_nonempty |
| ok | 200 | text/html | 1 | https://dovuz.innopolis.university/pre-olympiads/innopolis-open/cyberbez | html_nonempty |
| ok | 200 | text/html | 1 | https://dovuz.innopolis.university/pre-olympiads/innopolis-open/informatics | html_nonempty |
| ok | 200 | text/html | 1 | https://dovuz.innopolis.university/pre-olympiads/innopolis-open/math | html_nonempty |
| ok | 200 | text/html | 1 | https://dovuz.innopolis.university/pre-olympiads/innopolis-open/robo | html_nonempty |
| ok | 200 | text/html | 4 | https://dovuz.sfu.ru/abiturientu-sfu/olimpiady/belchonok/arkhiv/ | html_nonempty |
| ok | 200 | text/html | 6 | https://dovuz.urfu.ru/olymps/izumrud/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://dream-create.ru/shkola2.html | html_nonempty |
| ok | 200 | text/html | 1 | https://elo.linguanet.ru/#archive | html_nonempty |
| ok | 200 | text/html | 1 | https://fin-olimp.ru/o-proekte/materials/ | html_nonempty |
| ok | 200 | text/html | 1 | https://fingram.rea.ru/olimpiada | html_nonempty |
| ok | 200 | text/html | 1 | https://geoschool.web.ru/olympiad/_arhiv.html | html_nonempty |
| ok | 200 | text/html | 1 | https://inf-open.ru/archive/ | html_nonempty |
| ok | 200 | text/html | 6 | https://info.abiturient.tsu.ru/ru/content/answers-ORMO | html_nonempty |
| ok | 200 | text/html | 1 | https://innagrika.ru/olimpiada/ | html_nonempty |
| ok | 200 | text/html | 1 | https://innagrika.ru/olimpiada/zadanija-i-pobediteli-proshlyh-let/ | html_nonempty |
| ok | 200 | application/pdf | 1 | https://innagrika.ru/wp-content/uploads/2026/05/7.materialy_zadanij_i_kriterii_ocenki_profil_agrogenetika_2025-26.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://lk-dovuz.innopolis.university/public/files/Final_robo_contest.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://lk-dovuz.innopolis.university/public/files/contest-ru.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://lk-dovuz.innopolis.university/public/files/materials_robo_25.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://lk-dovuz.innopolis.university/public/files/reshenie_ru.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://lk-dovuz.innopolis.university/public/files/robo_contest_7-8.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://lk-dovuz.innopolis.university/public/files/robo_contest_9-11.pdf | download_nonempty |
| ok | 200 | text/html | 1 | https://malun.kpfu.ru/mendeleev | html_nonempty |
| ok | 200 | text/html | 8 | https://malun.kpfu.ru/mpoarh | html_nonempty |
| ok | 200 | text/html | 1 | https://maxwell.mipt.ru/ | html_nonempty |
| ok | 200 | text/html | 1 | https://mkoshp.ru/ | html_nonempty |
| ok | 200 | text/html | 1 | https://moebiustour.ru/archive | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/amxk | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/arab | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/astr | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/bioecon | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/biol | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/chem | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/ecol | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/econ | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/fingram | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/gen | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/geog | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/hist | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/ib | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/iikt-10-11 | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/iikt-6-9 | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/izo | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/law | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/ling | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/math | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/math-6-7 | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/obzh | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/phil | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/phys | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/predprof-engprak | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/predprof-infprak | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/predprof-sciprak | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/pt | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/robo-5-8 | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/robo-9-11 | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/soci | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/trud-kd | html_nonempty |
| ok | 200 | text/html | 1 | https://mos.olimpiada.ru/tasks/trud-tt | html_nonempty |
| ok | 200 | text/html | 3 | https://mospolytech.ru/postupayushchim/olimpiady/olimpiada-iskusstvo-grafiki/ | html_nonempty |
| ok | 200 | text/html | 1 | https://msal.ru/content/abiturientam/olimpiady-i-konkursy/kutafinskaya-olimpiada-shkolnikov-po-pravu/raboty-pobediteley/ | html_nonempty |
| ok | 200 | text/html | 1 | https://neerc.ifmo.ru/school/archive/2025-2026.html | html_nonempty |
| ok | 200 | text/html | 1 | https://neerc.ifmo.ru/school/russia-team/archive.html | html_nonempty |
| ok | 200 | application/pdf | 1 | https://nerc.itmo.ru/school/io/archive/20240324/problems-20240324-ioip.pdf | download_nonempty |
| ok | 200 | text/html | 21 | https://ntcontest.ru/books/ | html_nonempty |
| ok | 200 | text/html | 1 | https://ogn.spmi.ru/zadaniya-i-resheniya-po-profilyu-estestvennye-nauki | html_nonempty |
| ok | 200 | text/html | 1 | https://ogn.spmi.ru/zadaniya-i-resheniya-po-profilyu-informatika | html_nonempty |
| ok | 200 | text/html | 1 | https://oho.misis.ru/materialy/materialy-proshlyh-let/ | html_nonempty |
| ok | 200 | text/html | 1 | https://olimp-lk.rpa-mu.ru/?p=1326 | html_nonempty |
| ok | 200 | text/html | 2 | https://olimp.prouniver.ru/archive/ | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/121/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/206/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/225/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/241/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/315/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/316/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/317/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/318/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/319/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/4357/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5005/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5013/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5024/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5033/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5034/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5035/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5039/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5054/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5148/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5149/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5172/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5322/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5354/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5663/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5710/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5777/tasks/2023?class=10 | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5809/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5864/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5911/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/5912/tasks | html_nonempty |
| ok | 200 | text/html | 1 | https://olimpiada.ru/activity/6946/tasks | html_nonempty |
| ok | 200 | text/html | 2 | https://olimpiadakurchatov.ru/tasks | html_nonempty |
| ok | 200 | text/html | 2 | https://olymp-sibir.nstu.ru/ | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.academtalant.ru/chemspb | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.bmstu.ru/ru/biology-olymp | html_nonempty |
| ok | 200 | text/html | 7 | https://olymp.bmstu.ru/ru/variants | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-arthist | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-biology | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-business | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-chemistry | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-culture | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-design | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-devcode | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-eco | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-electronics | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-finance | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-history | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-inter | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-it | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-journ | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-lang | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-lang-orient | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-law | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-literature | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-math | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-phil | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-psy | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-rus | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-soc | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-sociology | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/materials-vostok | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-arthist | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-biology | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-business | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-chemistry | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-culture | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-design | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-devcode | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-eco | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-electronics | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-finance | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-history | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-inter | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-it | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-journ | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-lang | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-lang-orient | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-law | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-literature | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-math | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-phil | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-psy | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-rus | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-soc | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-sociology | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.hse.ru/mmo/tasks-vostok | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.mephi.ru/engineering/about/traning/task_of_previous_years | html_nonempty |
| ok | 200 | text/html | 2 | https://olymp.mephi.ru/junior/examples | html_nonempty |
| ok | 200 | text/html | 2 | https://olymp.mephi.ru/junior/training | html_nonempty |
| ok | 200 | text/html | 2 | https://olymp.mephi.ru/rosatom/about/traning/task_of_previous_years | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.mephi.ru/rosatom_it/training | html_nonempty |
| ok | 200 | text/html | 7 | https://olymp.mipt.ru/olympiad/samples | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.misis.ru/ | html_nonempty |
| ok | 200 | text/html | 27 | https://olymp.msu.ru/rus/page/main/29/page/zadaniya-olimpiady-proshlyh-let | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.psu.ru/disciplines/chem/zadania.html | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.psu.ru/disciplines/geography/%D0%BE%D0%BB%D0%B8%D0%BC%D0%BF%D0%B8%D0%B0%D0%B4%D1%8B-%D0%BF%D1%80%D0%BE%D1%88%D0%BB%D1%8B%D1%85-%D0%BB%D0%B5%D1%82/ | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.psu.ru/disciplines/geology/home.html | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.rghpu.ru/arkhiv-luchshikh-rabot | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.rghpu.ru/zaklyuchitelnyj-etap/zadaniya-zaklyuchitelnogo-etapa-2026 | html_nonempty |
| ok | 200 | text/html | 1 | https://olymp.rgup.ru/#materials | html_nonempty |
| ok | 200 | text/html | 4 | https://olymp.tsput.ru/materials/ | html_nonempty |
| ok | 200 | text/html | 1 | https://olymphysics.nsu.ru/ | html_nonempty |
| ok | 200 | application/zip | 1 | https://olympiad.gazprom.ru/assets/files/training/solving-tasks-2026/chemistry.zip | download_nonempty |
| ok | 200 | application/zip | 1 | https://olympiad.gazprom.ru/assets/files/training/solving-tasks-2026/computer-science.zip | download_nonempty |
| ok | 200 | application/zip | 1 | https://olympiad.gazprom.ru/assets/files/training/solving-tasks-2026/economics.zip | download_nonempty |
| ok | 200 | application/zip | 1 | https://olympiad.gazprom.ru/assets/files/training/solving-tasks-2026/engineering.zip | download_nonempty |
| ok | 200 | application/zip | 1 | https://olympiad.gazprom.ru/assets/files/training/solving-tasks-2026/mathematics.zip | download_nonempty |
| ok | 200 | application/zip | 1 | https://olympiad.gazprom.ru/assets/files/training/solving-tasks-2026/physics.zip | download_nonempty |
| ok | 200 | text/html | 21 | https://olympiada.spbu.ru/arkhiv.html | html_nonempty |
| ok | 200 | text/html | 21 | https://olympiada.spbu.ru/podgotovka.html | html_nonempty |
| ok | 200 | text/html | 1 | https://olympiads.mccme.ru/ommo/26/ | html_nonempty |
| ok | 200 | text/html | 1 | https://olympiads.ru/team/ | html_nonempty |
| ok | 200 | text/html | 1 | https://opk.pravolimp.ru/articles/69a59b7e53bb56162303c58b | html_nonempty |
| ok | 200 | text/html | 1 | https://opk.pravolimp.ru/pages/6361009f53bb56318d003c08 | html_nonempty |
| ok | 200 | application/pdf | 1 | https://opk.pravolimp.ru/system/files/6814a74053bb56171e01b8e3/original/%D0%97%D0%B0%D0%B4%D0%B0%D0%BD%D0%B8%D1%8F%20%D0%9E%D0%9F%D0%9A%202024-2025.pdf?1746184000 | download_nonempty |
| ok | 200 | text/html | 2 | https://pre-univer.csu.ru/olymp/regcom/lastyear/ | html_nonempty |
| ok | 200 | text/html | 3 | https://pro.firpo.ru/meropriyatiya/itogi/itogi2026/ | html_nonempty |
| ok | 200 | text/html | 1 | https://pro.voenmeh.ru/oto_tt | html_nonempty |
| ok | 200 | text/html | 4 | https://prodcontest.com/materials/ | html_nonempty |
| ok | 200 | text/html | 8 | https://pvg.mk.ru/archive/2024-2025/ | html_nonempty |
| ok | 200 | text/html | 8 | https://pvg.mk.ru/archive/archive/ | html_nonempty |
| ok | 200 | text/html | 1 | https://raai.sfedu.ru/Olimpiada/Olimpia.html | html_nonempty |
| ok | 200 | application/pdf | 1 | https://rgup.ru/img/OLIMPIADY%20RGUP/FEMIDA%209-11%202023/10%20%D0%BA%D0%BB%D0%B0%D1%81%D1%81%20%D0%B7%D0%B0%D0%B4%D0%B0%D0%BD%D0%B8%D1%8F.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://rgup.ru/img/OLIMPIADY%20RGUP/FEMIDA%209-11%202023/11%20%D0%BA%D0%BB%D0%B0%D1%81%D1%81.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://rgup.ru/img/OLIMPIADY%20RGUP/FEMIDA%209-11%202023/9%20%D0%BA%D0%BB%D0%B0%D1%81%D1%81%20%D0%B7%D0%B0%D0%B4%D0%B0%D0%BD%D0%B8%D1%8F.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://rosfinolymp.ru/file/16803/zadaniya-i-kriterii-ocenki-finalnogo-etapa-dlya-shkolnikov-pdf | download_nonempty |
| ok | 200 | text/html | 1 | https://sibiriada.org/olymp.html | html_nonempty |
| ok | 200 | text/html | 1 | https://t.me/s/kidskillsmoscow?before=1776 | html_nonempty |
| ok | 200 | application/pdf | 1 | https://tasks.olimpiada.ru/upload/files/tasks/5777/2023/5777-ans-biol-10-final-23-24.pdf | download_nonempty |
| ok | 200 | application/pdf | 1 | https://tasks.olimpiada.ru/upload/files/tasks/5777/2023/5777-tasks-biol-10-final-23-24.pdf | download_nonempty |
| ok | 200 | text/html | 1 | https://techno-cup.ru/archive | html_nonempty |
| ok | 200 | text/html | 1 | https://techno-cup.ru/training | html_nonempty |
| ok | 200 | text/html | 1 | https://turgor.ru/problems/ | html_nonempty |
| ok | 200 | text/html | 1 | https://umov.phys.msu.ru/#archive | html_nonempty |
| ok | 200 | text/html | 1 | https://v-olymp.ru/prev-materials?slug=cryptography | official_api_materials |
| ok | 200 | text/html | 1 | https://v-olymp.ru/prev-materials?slug=foreign_language | official_api_materials |
| ok | 200 | text/html | 1 | https://v-olymp.ru/prev-materials?slug=information_security | official_api_materials |
| ok | 200 | text/html | 1 | https://v-olymp.ru/prev-materials?slug=physics | official_api_materials |
| ok | 200 | text/html | 1 | https://v-olymp.ru/prev-materials?slug=russian_language | official_api_materials |
| ok | 200 | text/html | 1 | https://v-olymp.ru/prev-materials?slug=social_studies | official_api_materials |
| ok | 200 | text/html | 1 | https://vos.olimpiada.ru/archive/table/tasks/years/2025_2026/ | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/anglyaz | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/astronom | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/biolog | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/chemistry | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/china | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/ecology | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/economy | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/fizkultura | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/french | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/geograf | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/history | html_nonempty |
| ok | 200 | text/html | 4 | https://vserosolimp.edsoo.ru/informatic | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/iskusstvo | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/ispansk | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/italy | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/literatura | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/matematika | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/nemeckiy | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/obshestvo | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/osnovybezopasn | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/physics | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/pravo | html_nonempty |
| ok | 200 | text/html | 1 | https://vserosolimp.edsoo.ru/russkiy | html_nonempty |
| ok | 200 | text/html | 2 | https://vserosolimp.edsoo.ru/tehnologiya | html_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/2JRP59nHTM2fJzo/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/4EdXcb9HddRMFwQ/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/6fKtr8sNzpkL3mm/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 2 | https://vso.edsoo.ru/public.php/dav/files/8wmeSPpHbXMPZHd/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/GxFB9RjFx38eofi/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/JCeNRLiPpMeeMJL/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/K8HLidSLaoCnzYZ/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/Mdt8k635qCok4Ad/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/TAjqnPsp2FFdLt2/?accept=zip | download_nonempty |
| ok | 200 | application/zip | 1 | https://vso.edsoo.ru/public.php/dav/files/Tm63xLfEnR2bY5m/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/X4XwrkzPfRarcCZ/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/XHQ7f9T5wp5pks4/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/XbXMjL8dp7tmXbw/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/YL2b7HQ5XttqWwE/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/eDEgpePPoT3PqAb/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/k5xnzeY8q4miMH9/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/oJF7sGDsMXBRpe7/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/qDn8KF4GQA46zsa/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/qzTbcXSrFK4bFp4/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/r23zYxqD5pdkMMa/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/rPRCxj9eCMsCPbT/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/sQBydKoiwScyg96/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 1 | https://vso.edsoo.ru/public.php/dav/files/sfy9ytLranPBq3d/?accept=zip | download_nonempty |
| ok | 200 | application/pdf | 4 | https://vso.edsoo.ru/public.php/dav/files/ywgpTXZJfX4RWE2/?accept=zip | download_nonempty |
| ok | 200 | text/html | 1 | https://www.energy-hope.ru/olymp/tasks.html | html_nonempty |
| ok | 200 | text/html | 5 | https://www.fa.ru/for-applicants/olympiads/mission/examples/ | html_nonempty |
| ok | 200 | text/html | 5 | https://www.fa.ru/for-applicants/olympiads/mission/materials/ | html_nonempty |
| ok | 200 | text/html | 1 | https://www.formulo.org/ru/olymp/2025-math-ru/ | html_nonempty |
| ok | 200 | text/html | 1 | https://www.formulo.org/ru/olymp/2025-phys-ru/ | html_nonempty |
| ok | 200 | text/html | 1 | https://www.herzen.spb.ru/abiturients/olimpiady/olimp-rsosh/fl/ | html_nonempty |
| ok | 200 | text/html | 1 | https://www.herzen.spb.ru/abiturients/olimpiady/olimp-rsosh/geo/ | html_nonempty |
| ok | 200 | text/html | 1 | https://www.herzen.spb.ru/abiturients/olimpiady/olimp-rsosh/pedagogy/index.php | html_nonempty |
| ok | 200 | text/html | 3 | https://www.pguas.ru/tatlin | html_nonempty |
| ok | 200 | text/html | 7 | https://www.ranepa.ru/olymp/arkhiv-zadaniy/ | html_nonempty |
| ok | 200 | text/html | 5 | https://www.rsuh.ru/education/cdo/olimpiada-rggu-dlya-shkolnikov.php | html_nonempty |
| ok | 200 | application/pdf | 1 | https://www.tyuiu.ru/media/pdf/38361b4b-09d2-464a-bfa4-42cfd1b0b12b.pdf | download_nonempty |
| ok | 200 | text/html | 1 | https://xn--80aeffgfbql5dyaw0k.xn--p1ai/union-olymp | html_nonempty |
| ok | 200 | text/html | 8 | https://xn--k1acfgjg.xn--l1afu.xn--p1ai/archives/%D0%B7%D0%B0%D0%B4%D0%B0%D0%BD%D0%B8%D1%8F/ | html_nonempty |
| ok | 200 | text/html | 1 | https://yumsh.ru/cms/yumsh-olymp/archive | html_nonempty |
