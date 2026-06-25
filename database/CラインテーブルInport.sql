USE frux;
SET GLOBAL local_infile = 1;

LOAD DATA LOCAL INFILE 'C:/Users/fruxt/Osechi-Production-Management-App/C_Line2025.csv'
INTO TABLE `cライン生産データ`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

truncate table `cライン生産データ`;
select * from `cライン生産データ`;

describe `cライン生産データ`;

alter table `cライン生産データ` modify column `生産数` int default 0;