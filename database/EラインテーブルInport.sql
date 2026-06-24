USE frux;
SET GLOBAL local_infile = 1;

LOAD DATA LOCAL INFILE 'C:/Users/fruxt/Osechi-Production-Management-App/E_Line2025.csv'
INTO TABLE `eライン生産データ`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

truncate table `eライン生産データ`;
select * from `eライン生産データ`;

describe `eライン生産データ`;

alter table `eライン生産データ` modify column `生産数` int default 0;