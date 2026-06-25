
USE frux;
SET GLOBAL local_infile = 1;

LOAD DATA LOCAL INFILE 'C:/Users/fruxt/Osechi-Production-Management-App/A_Line2025.csv'
INTO TABLE `aライン生産データ`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

truncate table `aライン生産データ`;
select * from `aライン生産データ`;

describe `aライン生産データ`;

alter table `aライン生産データ` modify column `生産数` int default 0;