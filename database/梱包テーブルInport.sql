
USE frux;
SET GLOBAL local_infile = 1;

LOAD DATA LOCAL INFILE 'C:/Users/fruxt/Osechi-Production-Management-App/konpou2025.csv'
INTO TABLE `梱包ライン生産データ`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

truncate table `梱包ライン生産データ`;
select * from `梱包ライン生産データ`;
describe `梱包ライン生産データ`;

alter table `梱包ライン生産データ` modify column `梱包数` int default 0

INSERT INTO `梱包ライン生産データ`('梱包ID','ライン名','クール','商品名','合計数','カウント単位','梱包数','残数','作成時刻','更新時刻')
VALUES(67,'G','第3クール','誉2_ヤオコー_店渡_',1800,80,0,1800,'0000-00-00 00:00:00','0000-00-00 00:00:00');