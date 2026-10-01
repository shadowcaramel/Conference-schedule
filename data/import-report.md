# Import report

Converted `data/programme.xlsx` into `data/*.json`.
Contribution ids and session ids were copied. Clock times were not edited.
The sheet’s UTC offset was `+10:00` and was not stored; the build derives it from `Asia/Vladivostok`.

## Counts

- Tracks: 8
- Rooms: 8
- Sessions: 84
- Contributions: 236 (188 oral, 48 poster)
- People: 219 (4 created from an unmatched chair line)
- Organizations: 41
- Changes: 12
- Resources: 0

## Chair matches

Each row is one sitting. `matched` means the surname and initials found an author. `created` means no author had that surname and initials, so a person was added (given name and patronymic are the initials). `matched (chair record)` is a later sitting that uses a person created earlier in this import.

| Session | Chair (RU) | Chair (EN) | Result | Person | Stored name |
|---|---|---|---|---|---|
| B002 | Кепагорин М. Г. | M. G. Kepagorbain | created | PER-0099 | Кепагорин М. Г. |
| B003 | Кепагорин М. Г. | M. G. Kepagorbain | matched (chair record) | PER-0099 | Кепагорин М. Г. |
| B004 | Кепагорин М. Г. | M. G. Kepagorbain | matched (chair record) | PER-0099 | Кепагорин М. Г. |
| B006 | Кавибуский К. П. | K. P. Kavibubskiy | matched | PER-0088 | Кавибуский Кеий Полевлович |
| B007 | Кавибуский К. П. | K. P. Kavibubskiy | matched | PER-0088 | Кавибуский Кеий Полевлович |
| B008 | Кавибуский К. П. | K. P. Kavibubskiy | matched | PER-0088 | Кавибуский Кеий Полевлович |
| B010 | Десувикл Л. Б. | L. B. Desuviklb | matched | PER-0073 | Десувикл Лароей Бундович |
| B011 | Десувикл Л. Б. | L. B. Desuviklb | matched | PER-0073 | Десувикл Лароей Бундович |
| B012 | Десувикл Л. Б. | L. B. Desuviklb | matched | PER-0073 | Десувикл Лароей Бундович |
| B013 | Десувикл Л. Б. | L. B. Desuviklb | matched | PER-0073 | Десувикл Лароей Бундович |
| B014 | Десувикл Л. Б. | L. B. Desuviklb | matched | PER-0073 | Десувикл Лароей Бундович |
| B016 | Д. Д. Тенамсов | D. D. Tenamsov | matched | PER-0204 | Тенамсов Далоь Давортевич |
| B017 | Р. Л. Монапопоаский | R. L. Monappaskiy | matched | PER-0126 | Монапопоаский Рапб Лесавевич |
| B018 | П. Н. Рориб | P. N. Roribb | matched | PER-0177 | Рориб Подепой Налелагифович |
| B019 | М. М. Супалов | M. M. Supalov | matched | PER-0189 | Супалов Мивебусл Монлович |
| B021 | Бусова Д. Г. | D. G. Busova | matched | PER-0038 | Бусова Детева Гогидкевна |
| B022 | Бусова Д. Г. | D. G. Busova | matched | PER-0038 | Бусова Детева Гогидкевна |
| B023 | Бусова Д. Г. | D. G. Busova | matched | PER-0038 | Бусова Детева Гогидкевна |
| B025 | Кавибуский К. П. | K. P. Kavibubskiy | matched | PER-0088 | Кавибуский Кеий Полевлович |
| B026 | Кавибуский К. П. | K. P. Kavibubskiy | matched | PER-0088 | Кавибуский Кеий Полевлович |
| B027 | Кавибуский К. П. | K. P. Kavibubskiy | matched | PER-0088 | Кавибуский Кеий Полевлович |
| B029 | К. С. Неров | K. S. Nerov | matched | PER-0138 | Неров Косуь Сарадогурович |
| B030 | П. В. Гопавнова | P. V. Gopavnova | matched | PER-0058 | Гопавнова Пока Вигувевна |
| B031 | М. Л. Лагогпов | M. L. Lagogpov | matched | PER-0104 | Лагогпов Мибавиуй Лебаволанович |
| B032 | М. Н. Балов | M. N. Balov | matched | PER-0031 | Балов Мукф Наридревич |
| B034 | П. В. Гопавнова | P. V. Gopavnova | matched | PER-0058 | Гопавнова Пока Вигувевна |
| B035 | С. К. Тамирадеский | S. K. Tamiradebskiy | matched | PER-0194 | Тамирадеский Сасемигб Кесугович |
| B036 | К. Сакакдова | K. Sakakdbova | created | PER-0181 | Сакакдова К. |
| B037 | Л. Д. Вефасев | L. D. Vefasbaev | matched | PER-0044 | Вефасев Лолосурин Донлович |
| B039 | Тамирадеский С. К. | S. K. Tamiradebskiy | matched | PER-0194 | Тамирадеский Сасемигб Кесугович |
| B040 | Тамирадеский С. К. | S. K. Tamiradebskiy | matched | PER-0194 | Тамирадеский Сасемигб Кесугович |
| B041 | Тамирадеский С. К. | S. K. Tamiradebskiy | matched | PER-0194 | Тамирадеский Сасемигб Кесугович |
| B043 | Вефасев Л. Д. | L. D. Vefasbaev | matched | PER-0044 | Вефасев Лолосурин Донлович |
| B044 | Вефасев Л. Д. | L. D. Vefasbaev | matched | PER-0044 | Вефасев Лолосурин Донлович |
| B045 | Вефасев Л. Д. | L. D. Vefasbaev | matched | PER-0044 | Вефасев Лолосурин Донлович |
| B047 | Б. Н. Гувлин | B. N. Guvlin | matched | PER-0062 | Гувлин Бупотай Неповзович |
| B048 | П. Т. Сутадаиский | P. T. Sutadaibskiy | matched | PER-0190 | Сутадаиский Пезирой Табагсевич |
| B049 | Л. Р. Бунип | L. R. Bunip | created | PER-0035 | Бунип Л. Р. |
| B050 | Ф. Л. Латандов | F. L. Latandbov | matched | PER-0109 | Латандов Фозитабув Леригевич |
| B053 | Ракефренко Д. | D. Rakefrenko | matched | PER-0165 | Ракефренко Допакевл |
| B054 | Ракефренко Д. | D. Rakefrenko | matched | PER-0165 | Ракефренко Допакевл |
| B055 | Ракефренко Д. | D. Rakefrenko | matched | PER-0165 | Ракефренко Допакевл |
| B057 | Фафовев Т. Р. | T. R. Fafovbev | matched | PER-0211 | Фафовев Текаай Риделпович |
| B058 | Фафовев Т. Р. | T. R. Fafovbev | matched | PER-0211 | Фафовев Текаай Риделпович |
| B059 | Фафовев Т. Р. | T. R. Fafovbev | matched | PER-0211 | Фафовев Текаай Риделпович |
| B063 | Мувилонов М. М. | M. M. Muvilonbaov | matched | PER-0128 | Мувилонов Муриь Мупалафевич |
| B064 | Мувилонов М. М. | M. M. Muvilonbaov | matched | PER-0128 | Мувилонов Муриь Мупалафевич |
| B065 | Мувилонов М. М. | M. M. Muvilonbaov | matched | PER-0128 | Мувилонов Муриь Мупалафевич |
| B067 | Дакафов Д. Л. | D. L. Dakafbov | matched | PER-0069 | Дакафов Дотегуй Лофолович |
| B068 | Дакафов Д. Л. | D. L. Dakafbov | matched | PER-0069 | Дакафов Дотегуй Лофолович |
| B069 | Дакафов Д. Л. | D. L. Dakafbov | matched | PER-0069 | Дакафов Дотегуй Лофолович |
| B071 | Н. С. Ланрова | N. S. Lanrbova | matched | PER-0107 | Ланрова Нибга Салемевна |
| B072 | В. Ф. Докзенко | V. F. Dokzenko | created | PER-0080 | Докзенко В. Ф. |
| B073 | Р. Б. Санебпев | R. B. Sanebpbev | matched | PER-0182 | Санебпев Ридомуй Букомнович |
| B074 | Б. Р. Тавпев | B. R. Tavpbev | matched | PER-0192 | Тавпев Буниий Рипемипефович |
| B076 | Р. Б. Санебпев | R. B. Sanebpbev | matched | PER-0182 | Санебпев Ридомуй Букомнович |
| B077 | Б. Р. Тавпев | B. R. Tavpbev | matched | PER-0192 | Тавпев Буниий Рипемипефович |
| B078 | П. Надпева | P. Nadpeva | matched | PER-0133 | Надпева Песапегна |
| B079 | Бунип Л. Р. | L. R. Bunip | matched (chair record) | PER-0035 | Бунип Л. Р. |
| B080 | Бунип Л. Р. | L. R. Bunip | matched (chair record) | PER-0035 | Бунип Л. Р. |
| B081 | Бунип Л. Р. | L. R. Bunip | matched (chair record) | PER-0035 | Бунип Л. Р. |
| B084 | П. Надпева | P. Nadpeva | matched | PER-0133 | Надпева Песапегна |

## People created for chairs

- `PER-0035` Бунип Л. Р. — Бунип Л. Р. / L. R. Bunip; Л. Р. Бунип / L. R. Bunip
- `PER-0080` Докзенко В. Ф. — В. Ф. Докзенко / V. F. Dokzenko
- `PER-0099` Кепагорин М. Г. — Кепагорин М. Г. / M. G. Kepagorbain
- `PER-0181` Сакакдова К. — К. Сакакдова / K. Sakakdbova

## People with more than one contribution

- `PER-0008` Lepnov Nabulopos: POST-02, POST-03, POST-04
- `PER-0032` Бафт Мудобн Ведадович: P-J1, P-18
- `PER-0038` Бусова Детева Гогидкевна: P-25, S2-20
- `PER-0049` Гиктенко Канипедег Неникпович: S4-23, POST-40
- `PER-0057` Гомфева Гунаи Кавловна: S3-24, S3-25, S3-26
- `PER-0063` Гуготалфев Гутевесв Гувобфевич: S6-02, S6-03, POST-17
- `PER-0070` Дакофоская Пева Легунигировна: S3-27, POST-30
- `PER-0071` Даротелин Мопероей Лобугмевич: S7-06, S7-11
- `PER-0090` Канесенко Фонанирв Фонетмевич: P-09, POST-38, POST-39
- `PER-0107` Ланрова Нибга Салемевна: S1-01, S5-07
- `PER-0141` Нефолодов Пепаой Далогиланович: POST-31, POST-32, POST-33
- `PER-0144` Нисемов Сакас Лесепович: POST-05, POST-06
- `PER-0158` Погунлова Такефонва Сенивигровна: S7-04, POST-29
- `PER-0190` Сутадаиский Пезирой Табагсевич: P-26, S2-21
- `PER-0204` Тенамсов Далоь Давортевич: S1-08, S2-08
- `PER-0216` Фородов Сугизий Миногсевич: P-22, POST-12

## Organizations

- `ORG-001` Department of Physics, Lirenthal University (Ostia, Valemarcha)
- `ORG-002` Institute of Coastal Mechanics (Calderon, Montavia)
- `ORG-003` KNR Valemarchi
- `ORG-004` Miral Sci. Lab., Polverton LtD (Ostwick, Valeria)
- `ORG-005` Mireldan Univ., Ostia
- `ORG-006` БАР ОТ
- `ORG-007` БАР ОТ ЗЕОН
- `ORG-008` БАР ОТ-СЕЛМ
- `ORG-009` БАР ОТ-СЕЛМ, МорПУ
- `ORG-010` БАРХАН
- `ORG-011` БАРХАф
- `ORG-012` БЮР Прибреж
- `ORG-013` ВИР
- `ORG-014` ВИР БУК
- `ORG-015` Гамматек / Gammatech — https://gammatech.pro/ gammatech.png
- `ORG-016` Диджитайзер / Digitizer — https://edigitizer.ru/ digitizer.svg
- `ORG-017` КВУ
- `ORG-018` КРН (Берег
- `ORG-019` КРН (Берег)
- `ORG-020` ЛАРЕН
- `ORG-021` ЛАРЕН КВУ
- `ORG-022` ЛАРН
- `ORG-023` ЛИСТ, КВУ
- `ORG-024` ЛКДЦ им. К.М. Орша
- `ORG-025` ЛУГ
- `ORG-026` ЛУГ, ЛАРН
- `ORG-027` МЕЛНИИ СЕВ
- `ORG-028` Научное оборудование / Scientific Equipment — https://spegroup.ru/ spegroup.svg
- `ORG-029` НОЛ Приволж
- `ORG-030` ОРВУ (Севера)
- `ORG-031` ОТ ЗЕОН
- `ORG-032` ОТ-СЕЛМ
- `ORG-033` ПЛИОН
- `ORG-034` РИВН
- `ORG-035` РифГУ
- `ORG-036` Северный политехнический университет прибрежного края (Северград, Валмерия)
- `ORG-037` СЕЛМ
- `ORG-038` ТЕЗО
- `ORG-039` ТЕЗО, ЛИСТ
- `ORG-040` ШАЛМ
- `ORG-041` ЯРЬ(Берег)
