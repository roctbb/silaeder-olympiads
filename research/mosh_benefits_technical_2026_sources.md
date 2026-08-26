# Льготы для 32 профилей Московской олимпиады школьников: приём-2026

Дата проверки: **26 августа 2026 года**. Целевой каталог: **2026/27**.

## Граница данных

Это проверенный ориентир по правилам **приёма-2026**, а **не прогноз на приём-2027**. Результаты сезона 2026/27 будут использоваться при поступлении позже, поэтому перед применением льготы пользователь обязан открыть актуальные правила выбранного вуза.

Проверены МФТИ, НИЯУ МИФИ, МГТУ им. Н. Э. Баумана, ИТМО и СПбГУ. Связь добавлена только там, где официальный документ вуза прямо называет «Московскую олимпиаду школьников» и соответствующий профиль. Уровень олимпиады из перечня не использовался как основание для БВИ или 100 баллов.

Статус `unresolved` означает «в проверенных документах нельзя безопасно назначить право по заданному правилу исследования», а не доказательство отсутствия любого права.

## Результат

- проверено профилей: **32**;
- профилей хотя бы с одной подтверждённой связью: **17**;
- подтверждённых пар `slug + вуз`: **40**;
- типы: **16 `bvi`**, **4 `hundred_points`**, **20 `other`**;
- дубликатов `slug + вуз`: **0**;
- максимум одна benefit-запись на `slug + вуз`;
- если строка или совокупность официальных приложений даёт и БВИ, и 100 баллов в разных условиях, используется единая запись `other`.

## Официальные источники

### МФТИ

- [Порядок предоставления особых прав победителям и призёрам олимпиад школьников в МФТИ в 2026 году](https://pk.mipt.ru/bachelor/2026_olympiads/) — официальная страница и матрица. Строка 37 прямо перечисляет десять профилей МОШ. Для МОШ результат должен быть получен за 11 класс и не ранее 2022 года; предмет и минимальный балл зависят от права и конкурсной группы.
- Смешанные строки «100 баллов + адресное БВИ» записаны как `other`; чистое адресное БВИ по робототехнике, финансовой грамотности и экономике — как `bvi`.

### НИЯУ МИФИ

- [Официальная страница льгот приёма-2026](https://admission.mephi.ru/admission/baccalaureate-and-specialty/specials/winners).
- [Официальная PDF-матрица для московской площадки](https://admission.mephi.ru/content/public/uploads/documents/2026/main_doc/19._osobye_prava_moskva_2026_last_1.pdf) — строка 37 прямо перечисляет профили МОШ, коды направлений БВИ и отдельную колонку 100 баллов.
- БВИ ограничено ровно указанными кодами направлений; лингвистика и филология дают 100 баллов по русскому языку на всех направлениях; финансовая грамотность сохранена как `other`, поскольку одна строка содержит и БВИ, и 100 баллов.

### МГТУ им. Н. Э. Баумана

- [Раздел официальных документов](https://bmstu.ru/documents).
- [Приложение 5: общий порядок предоставления особых прав](https://api.mirror.bmstu.ru/file/122219/download).
- [Приложение 5.1: матрица БВИ по НПС](https://api.mirror.bmstu.ru/file/124777/download).
- [Приложение 5.3: право на 100 баллов](https://api.mirror.bmstu.ru/file/122150/download).
- Общие условия: результат в 10 или 11 классе, подтверждающий ЕГЭ не ниже 75. БВИ зависит от конкретного НПС и отдельной колонки победителя/призёра; 100 баллов проверено по строке 37 приложения 5.3. Если подтверждены оба механизма, используется одна запись `other`.

### Университет ИТМО

- [Раздел нормативных документов ИТМО](https://abit.itmo.ru/page/80).
- [Официальное приложение о дипломах РСОШ, дающих БВИ в 2026 году](https://abit.itmo.ru/file_storage/file/pages/82/rsosh_bvi_2025.pdf). Техническое имя файла содержит `2025`, но заголовок документа прямо относится к поступлению в 2026 году.
- Прямо подтверждены МОШ по информатике и математике для 01.03.02 и по изобразительному искусству для 54.03.01. Для изобразительного искусства поле подтверждающего предмета в строке пустое, поэтому порог не придуман.

### СПбГУ

- [Официальная матрица приёма-2026](https://abiturient.spbu.ru/medialibrary/ru/2026/bac/bac_spec_olymp_2_2026.pdf).
- В документе нет строки с названием «Московская олимпиада школьников»: условия заданы по профилю и уровню. Поскольку исследование запрещает выводить право из уровня перечня, все 32 связи СПбГУ оставлены `generic_matrix_only`.

Все перечисленные URL повторно открыты с HTTP 200 (с допустимыми официальными редиректами МГТУ и ИТМО) 26 августа 2026 года.

## Все 32 проверенных slug

| № | Slug | Профиль каталога | Подтверждено | Unresolved |
|---:|---|---|---|---|
| 1 | `mosh-2026-27-arab` | Арабский язык | — | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 2 | `registry-2026-27-035-01` | Астрономия | МФТИ — `other`<br>НИЯУ МИФИ — `bvi`<br>МГТУ — `other` | ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 3 | `mosh-2026-27-biol` | Биология | — | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 4 | `mosh-2026-27-bioecon` | Биоэкономика | — | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 5 | `registry-2026-27-035-02` | Вероятность и статистика | НИЯУ МИФИ — `bvi`<br>МГТУ — `other` | МФТИ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 6 | `registry-2026-27-035-03` | Генетика | МФТИ — `other`<br>МГТУ — `other` | НИЯУ МИФИ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 7 | `registry-2026-27-035-04` | География | — | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 8 | `registry-2026-27-035-05` | Изобразительное искусство | ИТМО — `bvi` | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 9 | `mosh-2026-27-iikt-10-11` | Информатика (10–11 классы) | МФТИ — `other`<br>НИЯУ МИФИ — `bvi`<br>МГТУ — `other`<br>ИТМО — `bvi` | СПбГУ — `generic_matrix_only` |
| 10 | `mosh-2026-27-iikt-6-9` | Информатика (6–9 классы) | — | МФТИ — `age_track_not_safely_mapped`<br>НИЯУ МИФИ — `age_track_not_safely_mapped`<br>МГТУ — `age_track_not_safely_mapped`<br>ИТМО — `age_track_not_safely_mapped`<br>СПбГУ — `generic_matrix_only` |
| 11 | `mosh-2026-27-ib` | Информационная безопасность | — | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 12 | `registry-2026-27-035-07` | История | НИЯУ МИФИ — `bvi`<br>МГТУ — `other` | МФТИ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 13 | `registry-2026-27-035-08` | История искусств | — | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 14 | `mosh-2026-27-obzh` | Комплексная безопасность | — | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 15 | `registry-2026-27-035-09` | Лингвистика | НИЯУ МИФИ — `hundred_points`<br>МГТУ — `hundred_points` | МФТИ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 16 | `mosh-2026-27-math-6-7` | Математический праздник | — | МФТИ — `age_track_not_safely_mapped`<br>НИЯУ МИФИ — `age_track_not_safely_mapped`<br>МГТУ — `age_track_not_safely_mapped`<br>ИТМО — `age_track_not_safely_mapped`<br>СПбГУ — `generic_matrix_only` |
| 17 | `mosh-2026-27-math` | Московская математическая олимпиада | МФТИ — `other`<br>НИЯУ МИФИ — `bvi`<br>МГТУ — `other`<br>ИТМО — `bvi` | СПбГУ — `generic_matrix_only` |
| 18 | `registry-2026-27-035-11` | Обществознание | НИЯУ МИФИ — `bvi`<br>МГТУ — `other` | МФТИ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 19 | `registry-2026-27-035-12` | Право | МГТУ — `other` | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 20 | `mosh-2026-27-predprof-engprak` | Предпрофессиональная олимпиада: Инженерия | — | МФТИ — `umbrella_profile_ambiguous`<br>НИЯУ МИФИ — `umbrella_profile_ambiguous`<br>МГТУ — `umbrella_profile_ambiguous`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 21 | `mosh-2026-27-predprof-infprak` | Предпрофессиональная олимпиада: Информационные технологии | — | МФТИ — `umbrella_profile_ambiguous`<br>НИЯУ МИФИ — `umbrella_profile_ambiguous`<br>МГТУ — `umbrella_profile_ambiguous`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 22 | `mosh-2026-27-predprof-sciprak` | Предпрофессиональная олимпиада: Исследования | — | МФТИ — `umbrella_profile_ambiguous`<br>НИЯУ МИФИ — `umbrella_profile_ambiguous`<br>МГТУ — `umbrella_profile_ambiguous`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 23 | `mosh-2026-27-robo-5-8` | Робототехника (5–8 классы) | — | МФТИ — `age_track_not_safely_mapped`<br>НИЯУ МИФИ — `age_track_not_safely_mapped`<br>МГТУ — `age_track_not_safely_mapped`<br>ИТМО — `age_track_not_safely_mapped`<br>СПбГУ — `generic_matrix_only` |
| 24 | `mosh-2026-27-robo-9-11` | Робототехника (9–11 классы) | МФТИ — `bvi`<br>НИЯУ МИФИ — `bvi`<br>МГТУ — `other` | ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 25 | `mosh-2026-27-trud-kd` | Труд (технология): Культура дома, дизайн и технологии | — | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 26 | `mosh-2026-27-trud-tt` | Труд (технология): Техника, технологии и техническое творчество | — | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 27 | `registry-2026-27-035-15` | Физика | МФТИ — `other`<br>НИЯУ МИФИ — `bvi`<br>МГТУ — `other` | ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 28 | `mosh-2026-27-phil` | Филология | НИЯУ МИФИ — `hundred_points` | МФТИ — `not_explicitly_confirmed`<br>МГТУ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 29 | `registry-2026-27-035-16` | Финансовая грамотность | МФТИ — `bvi`<br>НИЯУ МИФИ — `other`<br>МГТУ — `hundred_points` | ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 30 | `registry-2026-27-035-17` | Химия | МФТИ — `other`<br>НИЯУ МИФИ — `bvi`<br>МГТУ — `other` | ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 31 | `registry-2026-27-035-18` | Экология | МГТУ — `other` | МФТИ — `not_explicitly_confirmed`<br>НИЯУ МИФИ — `not_explicitly_confirmed`<br>ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |
| 32 | `registry-2026-27-035-19` | Экономика | МФТИ — `bvi`<br>НИЯУ МИФИ — `bvi`<br>МГТУ — `other` | ИТМО — `not_explicitly_confirmed`<br>СПбГУ — `generic_matrix_only` |

## Ключевые unresolved-случаи

- `mosh-2026-27-predprof-engprak`, `mosh-2026-27-predprof-infprak` и `mosh-2026-27-predprof-sciprak`: МФТИ, НИЯУ МИФИ и МГТУ публикуют одну зонтичную строку «предпрофессиональная», но официальные документы вузов не распределяют её между тремя отдельными карточками сервиса. Льгота не была угадана.
- `mosh-2026-27-iikt-6-9`, `mosh-2026-27-math-6-7` и `mosh-2026-27-robo-5-8`: возрастная карточка не получила право старшей карточки автоматически; документы вузов либо требуют диплом 10/11 класса, либо не позволяют безопасно сопоставить возрастной трек.
- СПбГУ: все 32 профиля оставлены unresolved из-за отсутствия прямой строки с названием МОШ.
- Профили без прямой строки в матрице конкретного вуза имеют `not_explicitly_confirmed`; это осознанно консервативнее переноса льготы по уровню перечня.

## Машиночитаемый пакет

Подробные условия, предметы подтверждения, пороги, коды направлений, source locator и unresolved-причины находятся в `research/mosh_benefits_technical_2026.json`. Каждое описание льготы содержит явное предупреждение «Не прогноз на приём-2027».
