USE frux;
SET GLOBAL local_infile = 1;

LOAD DATA LOCAL INFILE 'C:/Users/fruxt/Osechi-Production-Management-App/D_Line2025.csv'
INTO TABLE `dライン生産データ`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

truncate table `dライン生産データ`;
select * from `dライン生産データ`;

describe `dライン生産データ`;

alter table `dライン生産データ` modify column `生産数` int default 0;