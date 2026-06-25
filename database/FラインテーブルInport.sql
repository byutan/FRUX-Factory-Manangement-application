USE frux;
SET GLOBAL local_infile = 1;

LOAD DATA LOCAL INFILE 'C:/Users/fruxt/Osechi-Production-Management-App/F_Line2025.csv'
INTO TABLE `fライン生産データ`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

truncate table `fライン生産データ`;
select * from `fライン生産データ`;

describe `fライン生産データ`;

alter table `fライン生産データ` modify column `生産数` int default 0;