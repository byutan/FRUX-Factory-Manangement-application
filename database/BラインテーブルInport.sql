USE frux;
SET GLOBAL local_infile = 1;

LOAD DATA LOCAL INFILE 'C:/Users/fruxt/Osechi-Production-Management-App/B_Line2025.csv'
INTO TABLE `bライン生産データ`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

truncate table `bライン生産データ`;
select * from `bライン生産データ`;

describe `bライン生産データ`;

alter table `bライン生産データ` modify column `生産数` int default 0;