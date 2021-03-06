-- psql mystrade < users.sql

delete from game_gameplayer;
delete from game_commodityinhand;
delete from game_ruleinhand;
delete from game_message;
delete from game_game_rules;
delete from game_game;
delete from profile_mystradeuser_user_permissions;
delete from profile_mystradeuser;

insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (1, 'manur', '', '', 'manur@manur.org', 'pbkdf2_sha256$10000$AvsUPNfG92lH$Uv9zi+lyAJcAqRnoASDBSmA8edSn3rlLvWaQT4xOmX8=', true, true, true, '2012-11-14 13:14:29.701148-08', '2012-11-14 13:14:10.261669-08', false, '', '');
insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (2, 'test1', '', '', 'test1@manur.org', 'pbkdf2_sha256$10000$ugaqIMpJCLqL$ICD7AbFkd1xruEUzRCfc7Wn5OykpQt3EbVXkFmf4bJA=', false, true, false, '2012-11-14 13:14:43.486688-08', '2012-11-14 13:14:43.486698-08', false, '', '');
insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (3, 'test2', '', '', 'test2@manur.org', 'pbkdf2_sha256$10000$cKGwnJ2Fw2DN$w73RWXIIEG4rpEaYsM7E/aHblltOxEGxW6iSwr0Fu84=', false, true, false, '2012-11-14 13:14:54-08', '2012-11-14 13:14:54-08', false, '', '');
insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (4, 'test3', '', '', 'test3@manur.org', 'pbkdf2_sha256$10000$Qe110chEVgXx$/h9v3IdKxiD2AgKcKHFKJXv6hQ3lG9xV4CKqK9K5e0Y=', false, true, false, '2012-11-14 13:16:06.79498-08', '2012-11-14 13:16:06.79499-08', false, '', '');
insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (5, 'test4', '', '', 'test4@manur.org', 'pbkdf2_sha256$10000$gfuMQraRYBX6$K7XS9VXSfzyypuS9cONAstm1t0f/5cFonHpXki/um7A=', false, true, false, '2012-11-14 13:16:15.139205-08', '2012-11-14 13:16:15.139216-08', false, '', '');
insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (6, 'test5', '', '', 'test5@manur.org', 'pbkdf2_sha256$10000$pkmAlZ316n1L$K5QRf1+cOUcmb22RO/d15mprtTUhjaCTt2V7i80+9Yc=', false, true, false, '2012-11-14 13:16:25.94064-08', '2012-11-14 13:16:25.940651-08', false, '', '');
insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (7, 'test6', '', '', 'test6@manur.org', 'pbkdf2_sha256$10000$lldGUIwveKF9$woG1SSqxUUe78ATix5m4OWxuDlRUe/3qVIV5Y06s5hQ=', false, true, false, '2012-11-14 13:16:35.504444-08', '2012-11-14 13:16:35.504485-08', false, '', '');
insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (8, 'test7', '', '', 'test7@manur.org', 'pbkdf2_sha256$10000$PyYHiS2oxbmA$dLdbqVEe9Hk6CNkof36pyvg2ByZ+Rg8Oe7gYnh7BcH8=', false, true, false, '2012-11-14 13:16:42.608752-08', '2012-11-14 13:16:42.608791-08', false, '', '');
insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (9, 'test8', '', '', 'test8@manur.org', 'pbkdf2_sha256$10000$l3RIL0Sdy17H$ivtardZX6ZL0AYOawLKRoJ1WOARl3Cyjus5xG6Mf2eA=', false, true, false, '2012-11-14 13:16:51.240367-08', '2012-11-14 13:16:51.240378-08', false, '', '');
insert into profile_mystradeuser (id, username, first_name, last_name, email, password, is_staff, is_active, is_superuser, last_login, date_joined, send_notifications, bio, contact) values (10, 'test9', '', '', 'test9@manur.org', 'pbkdf2_sha256$10000$lQjGRQ0IdsJk$iFkyorMeAoGo5LihMgp6v89po55IjK+faczx1mLb9KM=', false, true, false, '2012-11-14 13:16:59.278742-08', '2012-11-14 13:16:59.278752-08', false, '', '');

select setval('profile_mystradeuser_id_seq', 11);

-- TODO add add_game permission to manur
